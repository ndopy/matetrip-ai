"""
replace_places 도구 전용 후처리 노드
도구가 반환한 새 장소 정보를 받아서 상태를 업데이트하고 Backend에 알림을 전송합니다.
"""

from dataclasses import dataclass

from app.agent.state import AgentState
from app.common.logger import logger
from app.schemas.place import SimplePlace
from app.utils.agent_message_utils import get_last_tool_message
from app.utils.place_normalizer import to_simple_places
from app.utils.tool_content_parser import parse_tool_content
from app.infra.replace_notification import schedule_replace_notification


@dataclass
class ReplacePayload:
    replaced_place_ids: list[str]
    new_places_data: list[dict]


def _extract_replace_payload(content: dict) -> ReplacePayload | None:
    if not content.get("success", False):
        logger.warning(
            f"[handle_replace_places_node] Tool failed: {content.get('error')}"
        )
        return None

    data = content.get("data", {}) or {}
    replaced_place_ids = data.get("replaced_place_ids", []) or []
    new_places_data = data.get("places", []) or []

    if not replaced_place_ids:
        logger.warning("[handle_replace_places_node] No replaced_place_ids")
        return None

    if not new_places_data:
        logger.warning("[handle_replace_places_node] No new places")
        return None

    return ReplacePayload(replaced_place_ids, new_places_data)


def _drop_places_by_ids(
    places: list[SimplePlace], place_ids: list[str]
) -> list[SimplePlace]:
    place_ids_set = set(place_ids)
    return [p for p in places if getattr(p, "id", None) not in place_ids_set]


def handle_replace_places_node(state: AgentState) -> AgentState:
    """replace_places 도구 결과를 처리하여 상태를 업데이트합니다."""
    logger.info("[handle_replace_places_node] Starting")

    last_tool_message = get_last_tool_message(state.get("messages", []))
    if not last_tool_message:
        logger.warning("[handle_replace_places_node] No tool message found")
        return {}

    raw_content = getattr(last_tool_message, "content", None)
    content = parse_tool_content(raw_content)
    if content is None:
        return {}

    payload = _extract_replace_payload(content)
    if payload is None:
        return {}

    new_places = to_simple_places(payload.new_places_data)
    if not new_places:
        return {}

    # 기존 last_recommended_places 가져오기
    last_recommended_places = to_simple_places(state.get("last_recommended_places", []))

    # 교체 대상 제거
    updated_places: list[SimplePlace] = _drop_places_by_ids(
        last_recommended_places, payload.replaced_place_ids
    )

    # 새 장소 추가
    updated_places.extend(new_places)

    # 새로 추천한 장소 ID 추출
    new_place_ids = [p.id for p in new_places if hasattr(p, "id") and p.id]

    # 기존 excluded_place_ids에 추가 (중복 제거)
    current_excluded = state.get("excluded_place_ids", [])
    updated_excluded = list(set(current_excluded + new_place_ids))

    # Backend 알림 처리 (DB 업데이트 + Redis 캐시 동기화 + Socket 브로드캐스트)
    schedule_replace_notification(
        state, payload.replaced_place_ids, payload.new_places_data
    )

    return {
        "last_recommended_places": updated_places,
        "excluded_place_ids": updated_excluded,
    }
