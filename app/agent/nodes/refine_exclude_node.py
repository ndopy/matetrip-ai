"""
장소 제외 처리 노드
사용자가 특정 장소를 제외하고 다시 추천받고 싶을 때 처리하는 노드입니다.
"""

from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agent.utils.agent_utils import get_last_human_message
from app.agent.graph import AgentState
from app.common.logger import logger
from app.core.llm import global_llm
from app.schemas.place import SimplePlace


class ExclusionAnalysis(BaseModel):
    """제외할 장소 분석 결과"""

    excluded_place_ids: List[str] = Field(
        default=[],
        description="제외할 장소 ID 목록 (예: ['place1_id', 'place2_id'])",
    )
    excluded_indices: List[int] = Field(
        default=[],
        description="제외할 장소의 인덱스 (1-based, 예: [1, 3] means 첫 번째와 세 번째)",
    )
    excluded_keywords: List[str] = Field(
        default=[],
        description="제외할 키워드 목록 (예: ['카페', '호텔'])",
    )
    needs_new_recommendation: bool = Field(
        default=True, description="새로운 추천이 필요한지 여부"
    )


# 제외 분석 프롬프트
exclusion_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an assistant that analyzes user's exclusion requests.\n\n"
                "Given the user's message and the list of previously recommended places, "
                "identify which places the user wants to exclude.\n\n"
                "User might specify places by:\n"
                "1. Index/position: '첫 번째 빼고', '1번 제외', '세 번째랑 다섯 번째 빼줘'\n"
                "2. Keywords/category: '카페는 말고', '호텔 제외', '맛집만'\n"
                "3. Place name/title: '~~ 빼고', 'xxx는 제외'\n\n"
                "**IMPORTANT**:\n"
                "- When user says '카페는 말고' or '호텔 제외', add those to excluded_keywords\n"
                "- When user says '첫 번째 빼고', add 1 to excluded_indices\n"
                "- Extract ALL exclusion patterns from the user message\n\n"
                "Examples:\n"
                "- '첫 번째 빼고' → excluded_indices: [1]\n"
                "- '1번이랑 3번 제외' → excluded_indices: [1, 3]\n"
                "- '카페는 말고 맛집만' → excluded_keywords: ['카페']\n"
                "- '호텔 빼고' → excluded_keywords: ['호텔']\n"
            ),
        ),
        (
            "user",
            "User message: {user_message}\n\n"
            "Previously recommended places:\n{places_list}\n\n"
            "Analyze what the user wants to exclude.",
        ),
    ]
)

# 체인 생성
exclusion_chain = exclusion_prompt | global_llm.with_structured_output(
    ExclusionAnalysis
)


def refine_exclude_node(state: AgentState) -> AgentState:
    """
    사용자가 특정 장소를 제외하고 싶을 때 처리하는 노드

    처리 과정:
    1. 사용자 메시지에서 제외할 장소 파악 (인덱스, 키워드, 이름 등)
    2. last_recommended_places에서 해당 장소들을 필터링
    3. 남은 장소들을 사용자에게 응답
    """
    logger.info("[refine_exclude_node] Starting exclusion processing")

    last_recommended_places = state.get("last_recommended_places", [])
    # 이전 추천이 없으면 바로 에이전트로 넘김
    if not last_recommended_places:
        logger.warning("[refine_exclude_node] No previous recommendations found")
        response_message = AIMessage(
            content="죄송해요, 이전 추천 기록이 없어서 제외 처리를 할 수 없어요. 먼저 장소를 추천받아주세요."
        )
        return {"messages": [response_message]}

    messages = state.get("messages", [])
    # 마지막 사용자 메시지 추출
    user_message = get_last_human_message(messages)
    user_message_text = (
        user_message.content if isinstance(user_message, HumanMessage) else ""
    )

    logger.info(f"[refine_exclude_node] User message: {user_message}")
    logger.info(
        f"[refine_exclude_node] Last recommended places count: {len(last_recommended_places)}"
    )

    # 장소 리스트를 문자열로 변환 (분석용)
    places_list = "\n".join(
        [
            f"{i+1}. {place['title']} (ID: {place['id']})"
            for i, place in enumerate(last_recommended_places)
        ]
    )

    # 제외 분석 실행
    try:
        raw_analysis = exclusion_chain.invoke(
            {"user_message": user_message_text, "places_list": places_list}
        )
        analysis: ExclusionAnalysis = ExclusionAnalysis.model_validate(raw_analysis)

        logger.info(f"[refine_exclude_node] Exclusion analysis: {analysis}")

        # 제외할 장소 필터링
        filtered_places = _filter_places(last_recommended_places, analysis)

        logger.info(
            f"[refine_exclude_node] Filtered places count: {len(filtered_places)}"
        )

        # 필터링된 결과로 응답 생성
        if not filtered_places:
            response_content = (
                "모든 장소가 제외되어 추천할 장소가 없어요. 다른 조건으로 검색해주세요."
            )
        else:
            # 남은 장소들을 자연스럽게 소개
            response_content = _build_filtered_response(filtered_places, analysis)

        response_message = AIMessage(content=response_content)

        # 상태 업데이트: 필터링된 장소를 새로운 last_recommended_places로 설정
        return {
            "messages": [response_message],
            "last_recommended_places": filtered_places,
        }

    except Exception as e:
        logger.error(f"[refine_exclude_node] Error during exclusion: {e}")
        error_message = AIMessage(
            content="제외 처리 중 오류가 발생했어요. 다시 시도해주세요."
        )
        return {"messages": [error_message]}


def _filter_places(
    places: List[SimplePlace], analysis: ExclusionAnalysis
) -> List[SimplePlace]:
    """
    분석 결과를 기반으로 장소 필터링

    Args:
        places: 원본 장소 리스트
        analysis: 제외 분석 결과

    Returns:
        필터링된 장소 리스트
    """
    filtered = []

    for i, place in enumerate(places):
        should_exclude = False

        # 1. 인덱스로 제외 (1-based)
        if (i + 1) in analysis.excluded_indices:
            should_exclude = True
            logger.info(f"Excluding place by index {i+1}: {place['title']}")

        # 2. ID로 제외
        if place["id"] in analysis.excluded_place_ids:
            should_exclude = True
            logger.info(f"Excluding place by ID: {place['title']}")

        # 3. 키워드로 제외 (title에 키워드가 포함되어 있으면 제외)
        for keyword in analysis.excluded_keywords:
            if keyword.lower() in place["title"].lower():
                should_exclude = True
                logger.info(f"Excluding place by keyword '{keyword}': {place['title']}")
                break

        if not should_exclude:
            filtered.append(place)

    return filtered


def _build_filtered_response(
    filtered_places: List[SimplePlace], analysis: ExclusionAnalysis
) -> str:
    """
    필터링된 장소 목록으로 응답 생성

    Args:
        filtered_places: 필터링된 장소 리스트
        analysis: 제외 분석 결과

    Returns:
        응답 메시지
    """
    # 제외 조건 설명
    exclusion_desc = []
    if analysis.excluded_indices:
        indices_str = ", ".join([f"{idx}번째" for idx in analysis.excluded_indices])
        exclusion_desc.append(indices_str)
    if analysis.excluded_keywords:
        keywords_str = ", ".join([f"'{kw}'" for kw in analysis.excluded_keywords])
        exclusion_desc.append(keywords_str)

    if exclusion_desc:
        response = f"{' 및 '.join(exclusion_desc)} 장소를 제외하고 {len(filtered_places)}곳을 추천드려요.\n\n"
    else:
        response = f"필터링된 결과 {len(filtered_places)}곳을 추천드려요.\n\n"

    # 장소 목록은 프론트엔드에서 표시하므로 간단히 안내만
    response += "아래 장소들을 확인해보세요!"

    return response
