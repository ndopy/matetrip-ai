"""
도구 실행 후 상태 업데이트 노드
장소 추천 도구 결과를 last_recommended_places에 저장합니다.
"""

import json
from langchain_core.messages import ToolMessage

from agent.utils.agent_utils import get_last_tool_message
from app.agent.graph import AgentState
from app.agent.utils.place_extractor import (
    is_place_recommendation_tool,
    extract_places_from_result,
)
from app.common.logger import logger


def update_state_node(state: AgentState) -> AgentState:
    """
    도구 실행 결과를 분석하여 상태를 업데이트하는 노드

    장소 추천 도구의 결과인 경우 last_recommended_places 업데이트
    """
    logger.info("[update_state_node] Checking tool results for state update")

    messages = state.get("messages", [])

    # 마지막 ToolMessage 찾기
    last_tool_message = get_last_tool_message(messages)

    if not last_tool_message.content:
        logger.info("[update_state_node] No ToolMessage found")
        return {}

    # 도구 이름 확인
    tool_name = getattr(last_tool_message, "name", "")
    logger.info(f"[update_state_node] Tool name: {tool_name}")

    # 장소 추천 도구가 아니면 스킵
    if not is_place_recommendation_tool(tool_name):
        logger.info(
            f"[update_state_node] {tool_name} is not a place recommendation tool"
        )
        return {}

    # 도구 결과 파싱
    try:
        content = last_tool_message.content

        # 문자열인 경우 JSON 파싱 시도
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                logger.warning(
                    "[update_state_node] Failed to parse tool result as JSON"
                )
                return {}

        # 장소 추출
        places = extract_places_from_result(content, tool_name)

        if places:
            logger.info(
                f"[update_state_node] Updated last_recommended_places with {len(places)} places"
            )
            return {"last_recommended_places": places}
        else:
            logger.info("[update_state_node] No places found in tool result")
            return {}

    except Exception as e:
        logger.error(f"[update_state_node] Error processing tool result: {e}")
        return {}
