"""
도구 실행 후 상태 업데이트 노드
장소 추천 도구 결과를 last_recommended_places에 저장합니다.
"""

import json
from app.agent.utils.agent_utils import get_last_tool_message
from app.agent.state import AgentState
from app.agent.utils.place_extractor import extract_places_from_result
from app.common.logger import logger
from app.schemas.place import SimplePlace


def update_state_node(state: AgentState) -> AgentState:
    """
    도구 실행 결과를 분석하여 상태를 업데이트하는 노드

    모든 장소 추천 도구가 ToolResult 형식으로 반환하므로
    처리 로직이 단순화되었습니다.

    replace_single_place의 경우:
    - 기존 last_recommended_places에서 제외된 장소를 제거하고
    - 새로운 장소를 추가합니다
    """
    logger.info("[update_state_node] Starting state update")
    messages = state.get("messages", [])

    # 마지막 ToolMessage 찾기
    last_tool_message = get_last_tool_message(messages)
    if not last_tool_message or not last_tool_message.content:
        logger.info("[update_state_node] No ToolMessage found")
        return {}

    content = last_tool_message.content
    tool_name = getattr(last_tool_message, "name", "")
    logger.info(f"[update_state_node] Processing tool: {tool_name}")

    # replace_single_place의 경우 특별 처리
    if tool_name == "replace_single_place":
        return (
            _handle_replace_single_place(state, content)
            if isinstance(content, dict)
            else {}
        )

    try:

        # 문자열인 경우 JSON 파싱
        if isinstance(content, str):
            content = json.loads(content)

        # 장소 추출 (dict형식으로 표준 형식 처리)
        places = extract_places_from_result(content, tool_name)
        if places:
            return {"last_recommended_places": places}

        logger.info("[update_state_node] No places extracted from tool result")
        return {}

    except Exception as e:
        logger.error(f"[update_state_node] Error processing tool result: {e}")
        return {}


def _ensure_simple_places(places_data) -> list[SimplePlace]:
    """dict/Model 혼합 입력을 SimplePlace 리스트로 정규화"""
    normalized = []
    for place in places_data or []:
        if isinstance(place, SimplePlace):
            normalized.append(place)
        elif isinstance(place, dict) and "id" in place and "title" in place:
            normalized.append(SimplePlace(id=place["id"], title=place["title"]))
    return normalized


def _drop_place_by_id(places: list[SimplePlace], place_id: str) -> list[SimplePlace]:
    """주어진 ID를 제외한 새 리스트 반환"""
    return [p for p in places if getattr(p, "id", None) != place_id]


def _handle_replace_single_place(state: AgentState, content: dict) -> AgentState:
    """
    replace_single_place 도구 결과 처리

    기존 last_recommended_places에서 제외된 장소를 제거하고
    새로운 장소를 추가합니다.

    Args:
        state: 현재 AgentState
        content: replace_single_place 도구 실행 결과

    Returns:
        업데이트된 상태
    """
    try:
        # 성공 여부 확인
        if not content.get("success", False):
            logger.warning(
                f"[update_state_node] replace_single_place failed: {content.get('error')}"
            )
            return {}

        data = content.get("data", {})
        if not data:
            logger.warning("[update_state_node] No data in replace_single_place result")
            return {}

        # 제외된 장소 ID
        replaced_place_id = data.get("replaced_place_id")
        if not replaced_place_id:
            logger.warning("[update_state_node] No replaced_place_id in result")
            return {}

        # 새로운 장소들
        new_places_data = data.get("places", [])
        if not new_places_data:
            logger.warning(
                "[update_state_node] No new places in replace_single_place result"
            )
            return {}

        new_places = _ensure_simple_places(new_places_data)

        if not new_places:
            logger.warning("[update_state_node] Failed to convert new places")
            return {}

        # 기존 last_recommended_places 가져오기
        last_recommended_places = _ensure_simple_places(
            state.get("last_recommended_places", [])
        )

        # 제외된 장소 제거
        updated_places = _drop_place_by_id(last_recommended_places, replaced_place_id)

        # 새로운 장소 추가
        updated_places.extend(new_places)

        logger.info(
            f"[update_state_node] Replaced place {replaced_place_id} with {len(new_places)} new places. "
            f"Total: {len(updated_places)} places"
        )

        return {"last_recommended_places": updated_places}

    except Exception as e:
        logger.error(f"[update_state_node] Error handling replace_single_place: {e}")
        return {}
