"""
장소 제외 처리 노드
사용자가 특정 장소를 제외하고 다시 추천받고 싶을 때 처리하는 노드입니다.
"""

from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agent.utils.agent_utils import get_last_human_message
from app.agent.utils.place_normalizer import to_simple_places
from app.agent.state import AgentState
from app.common.logger import logger
from app.core.llm import global_llm
from app.schemas.place import SimplePlace


def to_string_from_places(places: List[SimplePlace]) -> str:
    """번호를 매긴 장소 목록 문자열 생성"""
    return "\n".join(
        f"{idx}. {place.title} (ID: {place.id})"
        for idx, place in enumerate(places, start=1)
    )


def _build_replacement_message(excluded_place: SimplePlace) -> HumanMessage:
    """replace_single_place 호출용 프롬프트를 생성"""
    excluded_place_id = excluded_place.id
    excluded_title = excluded_place.title

    latitude = getattr(excluded_place, "latitude", None)
    longitude = getattr(excluded_place, "longitude", None)
    coord_text = (
        f"좌표: latitude={latitude}, longitude={longitude}\n"
        if latitude is not None and longitude is not None
        else ""
    )

    replacement_prompt = (
        f"사용자가 '{excluded_title}'를 제외하고 싶어합니다. "
        f"replace_single_place 도구를 사용하여 대체 장소 1개를 추천해주세요.\n"
        f"제외할 장소 ID: {excluded_place_id}\n"
        f"{coord_text}"
        f"기존 추천 장소들은 excluded_place_ids 파라미터로 자동 전달됩니다."
    )

    return HumanMessage(content=replacement_prompt)


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


async def refine_exclude_node(state: AgentState) -> AgentState:
    """
    사용자가 특정 장소를 제외하고 싶을 때 처리하는 노드

    처리 과정:
    1. 사용자 메시지에서 제외할 장소 파악 (인덱스, 키워드, 이름 등)
    2. 제외할 장소 ID와 해당 장소의 좌표를 파악
    3. 기존 추천된 모든 장소를 excluded_place_ids에 추가
    4. replace_single_place를 프롬프트에 포함시켜 agent로 라우팅
    """
    logger.info("[refine_exclude_node] Starting exclusion processing")

    last_recommended_places: List[SimplePlace] = to_simple_places(
        state.get("last_recommended_places", [])
    )
    # 이전 추천이 없으면 바로 에이전트로 넘김
    if not last_recommended_places:
        logger.warning("[refine_exclude_node] No previous recommendations found")
        response_message = AIMessage(
            content="죄송해요, 이전 추천 기록이 없어서 제외 처리를 할 수 없어요. 먼저 장소를 추천받아주세요."
        )
        return {"messages": [response_message]}

    # 장소 리스트를 문자열로 변환 (분석용)
    places_list: str = to_string_from_places(last_recommended_places)

    # 마지막 사용자 메시지 추출
    user_message: HumanMessage = get_last_human_message(state.get("messages", []))
    logger.info(f"[refine_exclude_node] User message: {user_message}")

    # 제외 분석 실행
    try:
        raw_analysis = await exclusion_chain.ainvoke(
            {"user_message": user_message.content, "places_list": places_list}
        )
        analysis: ExclusionAnalysis = ExclusionAnalysis.model_validate(raw_analysis)

    except Exception as e:
        logger.error(f"[refine_exclude_node] Error during exclusion: {e}")
        return {
            "messages": [
                AIMessage(content="제외 처리 중 오류가 발생했어요. 다시 시도해주세요.")
            ]
        }

    return _build_replacement_response(last_recommended_places, analysis)


def _build_replacement_response(
    last_recommended_places: List[SimplePlace], analysis: ExclusionAnalysis
) -> AgentState:
    """분석 결과를 기반으로 교체 요청 메시지 및 상태 반환"""
    logger.info(f"[refine_exclude_node] Exclusion analysis: {analysis}")

    # 제외할 장소 ID 파악
    excluded_ids = _get_excluded_place_ids(last_recommended_places, analysis)

    if not excluded_ids:
        logger.warning("[refine_exclude_node] No places to exclude identified")
        return {
            "intent": "REFINEMENT",  # Agent로 라우팅하여 일반 대화로 처리
        }

    logger.info(f"[refine_exclude_node] Excluded place IDs: {excluded_ids}")

    # 제외할 장소 정보 찾기 (첫 번째 제외 장소만 처리)
    excluded_place_id = excluded_ids[0]
    excluded_place = next(
        (p for p in last_recommended_places if p.id == excluded_place_id), None
    )

    if not excluded_place:
        return {
            "intent": "REFINEMENT",
        }

    # 기존 추천 전체를 excluded_place_ids에 추가 (중복 방지)
    all_existing_ids = [place.id for place in last_recommended_places]

    logger.info(f"[refine_exclude_node] Replacing place: {excluded_place.title}")

    # Agent로 다시 라우팅하도록 intent 변경
    # excluded_place_ids를 state에 설정하여 도구가 이미 본 장소를 제외하도록 함
    prompt: HumanMessage = _build_replacement_message(excluded_place)
    return {
        "messages": [prompt],  # Agent로 라우팅하도록 프롬프트를 메시지로 추가
        "excluded_place_ids": all_existing_ids,
        "intent": "REFINEMENT",  # Agent로 라우팅
    }


def _get_excluded_place_ids(
    places: List[SimplePlace], analysis: ExclusionAnalysis
) -> List[str]:
    """
    분석 결과를 기반으로 제외할 장소 ID 리스트 추출

    Args:
        places: 원본 장소 리스트
        analysis: 제외 분석 결과

    Returns:
        제외할 장소 ID 리스트
    """
    excluded_ids: list[str] = []
    existing_ids = {place.id for place in places}
    seen: set[str] = set()

    # 1) 명시적 ID 우선
    for pid in analysis.excluded_place_ids:
        if pid and pid in existing_ids and pid not in seen:
            excluded_ids.append(pid)
            seen.add(pid)

    # 2) 인덱스 기반 (1-based)
    for idx in analysis.excluded_indices:
        if 1 <= idx <= len(places):
            pid = places[idx - 1].id
            if pid and pid in existing_ids and pid not in seen:
                excluded_ids.append(pid)
                seen.add(pid)

    # 3) 키워드 기반 (title 매칭 순서대로)
    if analysis.excluded_keywords:
        for place in places:
            for keyword in analysis.excluded_keywords:
                if keyword.lower() in place.title.lower():
                    pid = place.id
                    if pid and pid in existing_ids and pid not in seen:
                        excluded_ids.append(pid)
                        seen.add(pid)
                    break

    return excluded_ids
