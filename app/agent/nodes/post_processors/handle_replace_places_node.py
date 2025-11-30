"""
replace_places 도구 전용 후처리 노드
도구가 반환한 새 장소 정보를 받아서 상태를 업데이트합니다.
"""

from app.agent.state import AgentState
from app.common.logger import logger
from app.schemas.place import SimplePlace
from app.utils.agent_message_utils import get_last_tool_message
from app.utils.place_normalizer import to_simple_places


def _drop_places_by_ids(
    places: list[SimplePlace], place_ids: list[str]
) -> list[SimplePlace]:
    """주어진 ID들을 제외한 새 리스트 반환"""
    place_ids_set = set(place_ids)
    return [p for p in places if getattr(p, "id", None) not in place_ids_set]


def handle_replace_places_node(state: AgentState) -> AgentState:
    """replace_places 도구 결과를 처리하여 상태를 업데이트합니다."""
    logger.info("[handle_replace_places_node] Starting")

    # 마지막 ToolMessage 가져오기
    last_tool_message = get_last_tool_message(state.get("messages", []))
    if not last_tool_message:
        logger.warning("[handle_replace_places_node] No tool message found")
        return {}

    content = getattr(last_tool_message, "content", None)
    if not isinstance(content, dict):
        logger.warning("[handle_replace_places_node] Invalid content type")
        return {}

    # 성공 여부 확인
    if not content.get("success", False):
        logger.warning(f"[handle_replace_places_node] Tool failed: {content.get('error')}")
        return {}

    data = content.get("data", {})
    if not data:
        logger.warning("[handle_replace_places_node] No data in result")
        return {}

    # 교체 대상 ID 리스트
    replaced_place_ids = data.get("replaced_place_ids", [])
    if not replaced_place_ids:
        logger.warning("[handle_replace_places_node] No replaced_place_ids")
        return {}

    # 새로운 장소들
    new_places_data = data.get("places", [])
    if not new_places_data:
        logger.warning("[handle_replace_places_node] No new places")
        return {}

    new_places = to_simple_places(new_places_data)
    if not new_places:
        logger.warning("[handle_replace_places_node] Failed to convert new places")
        return {}

    # 기존 last_recommended_places 가져오기
    last_recommended_places = to_simple_places(
        state.get("last_recommended_places", [])
    )

    # 교체 대상 제거
    updated_places = _drop_places_by_ids(last_recommended_places, replaced_place_ids)

    # 새 장소 추가
    updated_places.extend(new_places)

    # 새로 추천한 장소 ID 추출
    new_place_ids = [p.id for p in new_places if hasattr(p, "id") and p.id]

    # 기존 excluded_place_ids에 추가 (중복 제거)
    current_excluded = state.get("excluded_place_ids", [])
    updated_excluded = list(set(current_excluded + new_place_ids))

    logger.info(
        f"[handle_replace_places_node] Replaced {len(replaced_place_ids)} places "
        f"with {len(new_places)} new places. Added {len(new_place_ids)} IDs to exclusion list "
        f"(total: {len(updated_excluded)})"
    )

    return {
        "last_recommended_places": updated_places,
        "excluded_place_ids": updated_excluded,
    }
