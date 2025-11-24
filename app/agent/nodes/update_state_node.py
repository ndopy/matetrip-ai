"""
도구 실행 후 상태 업데이트 노드
장소 추천 도구 결과를 last_recommended_places에 저장합니다.
"""

import json
from langchain_core.messages import ToolMessage

from app.agent.utils.agent_utils import get_last_tool_message
from app.agent.state import AgentState
from app.agent.utils.place_extractor import extract_places_from_result
from app.common.logger import logger


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

    tool_name = getattr(last_tool_message, "name", "")
    logger.info(f"[update_state_node] Processing tool: {tool_name}")

    try:
        content = last_tool_message.content

        # 문자열인 경우 JSON 파싱
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                logger.warning(
                    "[update_state_node] Failed to parse tool result as JSON"
                )
                return {}

        # replace_single_place의 경우 특별 처리
        if tool_name == "replace_single_place":
            if isinstance(content, dict):
                return _handle_replace_single_place(state, content)
            else:
                logger.warning("[update_state_node] Invalid content type for replace_single_place")
                return {}

        # 장소 추출 (ToolResult 표준 형식 처리)
        places = extract_places_from_result(content, tool_name)

        if places:
            logger.info(
                f"[update_state_node] Updated last_recommended_places with {len(places)} places"
            )
            return {"last_recommended_places": places}
        else:
            logger.info("[update_state_node] No places extracted from tool result")
            return {}

    except Exception as e:
        logger.error(f"[update_state_node] Error processing tool result: {e}")
        return {}


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
            logger.warning("[update_state_node] No new places in replace_single_place result")
            return {}

        # SimplePlace로 변환
        from app.schemas.place import SimplePlace

        new_places = []
        for place in new_places_data:
            if isinstance(place, dict) and "id" in place and "title" in place:
                new_places.append(SimplePlace(id=place["id"], title=place["title"]))

        if not new_places:
            logger.warning("[update_state_node] Failed to convert new places")
            return {}

        # 기존 last_recommended_places 가져오기
        last_recommended_places = state.get("last_recommended_places", [])

        # 제외된 장소 제거
        updated_places = [
            place
            for place in last_recommended_places
            if place.id != replaced_place_id
        ]

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
