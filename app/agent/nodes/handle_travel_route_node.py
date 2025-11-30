"""
create_travel_route 도구 전용 후처리 노드
여행 루트 생성 후 Backend에 알림을 보냅니다.
"""

from app.agent.state import AgentState
from app.agent.services.travel_route_notifier import handle_travel_route_notification
from app.common.logger import logger
from app.utils.agent_message_utils import get_last_tool_message


def handle_travel_route_node(state: AgentState) -> AgentState:
    """create_travel_route 도구 결과를 처리하고 Backend에 알림을 전송합니다."""
    logger.info("[handle_travel_route_node] Starting")

    # 마지막 ToolMessage 가져오기
    last_tool_message = get_last_tool_message(state.get("messages", []))
    if not last_tool_message:
        logger.warning("[handle_travel_route_node] No tool message found")
        return {}

    content = getattr(last_tool_message, "content", None)
    if not content:
        logger.warning("[handle_travel_route_node] No content")
        return {}

    # Backend 알림 처리
    handle_travel_route_notification(state, content)

    logger.info("[handle_travel_route_node] Notification sent")

    # 상태 변경 없음
    return {}
