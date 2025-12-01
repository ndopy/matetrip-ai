"""
일반 장소 추천 도구 전용 후처리 노드
recommend_nearby_places, recommend_popular_places_in_region 등의 결과를 처리합니다.
"""

from app.agent.state import AgentState
from app.common.logger import logger
from app.utils.agent_message_utils import get_last_tool_message
from app.utils.place_extractor import extract_simple_places_from_result
from app.utils.tool_content_parser import parse_tool_content


def handle_place_recommendation_node(state: AgentState) -> AgentState:
    """일반 장소 추천 도구 결과를 처리하여 상태를 업데이트합니다."""
    logger.info("[handle_place_recommendation_node] Starting")

    # 마지막 ToolMessage 가져오기
    last_tool_message = get_last_tool_message(state.get("messages", []))
    if not last_tool_message:
        logger.warning("[handle_place_recommendation_node] No tool message found")
        return {}

    tool_name = getattr(last_tool_message, "name", "")
    raw_content = getattr(last_tool_message, "content", None)

    # 공통 파싱 유틸리티 사용
    content = parse_tool_content(raw_content)
    if content is None:
        return {}

    # 장소 추출
    places = extract_simple_places_from_result(content, tool_name)

    logger.info(
        f"[handle_place_recommendation_node] Extracted {len(places)} places from {tool_name}"
    )

    # 새로 추천한 장소 ID 추출
    new_place_ids = [p.id for p in places if hasattr(p, "id") and p.id]

    # 기존 excluded_place_ids에 추가 (중복 제거)
    current_excluded = state.get("excluded_place_ids", [])
    updated_excluded = list(set(current_excluded + new_place_ids))

    logger.info(
        f"[handle_place_recommendation_node] Added {len(new_place_ids)} IDs to exclusion list "
        f"(total: {len(updated_excluded)})"
    )

    return {
        "last_recommended_places": places,
        "excluded_place_ids": updated_excluded,
    }
