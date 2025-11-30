"""
recommend_places_by_all_users 도구 전용 후처리 노드
워크스페이스 기반 추천 결과를 처리합니다.
"""

import json
from app.agent.state import AgentState
from app.common.logger import logger
from app.utils.agent_message_utils import get_last_tool_message
from app.utils.place_extractor import extract_simple_places_from_result


def handle_workspace_recommendation_node(state: AgentState) -> AgentState:
    """워크스페이스 추천 도구 결과를 처리하여 상태를 업데이트합니다."""
    logger.info("[handle_workspace_recommendation_node] Starting")

    # 마지막 ToolMessage 가져오기
    last_tool_message = get_last_tool_message(state.get("messages", []))
    if not last_tool_message:
        logger.warning("[handle_workspace_recommendation_node] No tool message found")
        return {}

    content = getattr(last_tool_message, "content", None)
    tool_name = getattr(last_tool_message, "name", "")

    if not content:
        logger.warning("[handle_workspace_recommendation_node] No content")
        return {}

    try:
        # 문자열인 경우 JSON 파싱
        if isinstance(content, str):
            content = json.loads(content)
    except Exception as e:
        logger.error(f"[handle_workspace_recommendation_node] JSON parse error: {e}")
        return {}

    # 장소 추출 (다른 place 도구들과 동일한 유틸 사용)
    places = extract_simple_places_from_result(content, tool_name)

    logger.info(
        f"[handle_workspace_recommendation_node] Extracted {len(places)} places from {tool_name}"
    )

    # 새로 추천한 장소 ID 추출
    new_place_ids = [p.id for p in places if hasattr(p, "id") and p.id]

    # 기존 excluded_place_ids에 추가 (중복 제거)
    current_excluded = state.get("excluded_place_ids", [])
    updated_excluded = list(set(current_excluded + new_place_ids))

    logger.info(
        f"[handle_workspace_recommendation_node] Added {len(new_place_ids)} IDs to exclusion list "
        f"(total: {len(updated_excluded)})"
    )

    return {
        "last_recommended_places": places,
        "excluded_place_ids": updated_excluded,
    }
