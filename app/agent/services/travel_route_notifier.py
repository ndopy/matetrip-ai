import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.agent.state import AgentState
from app.common.logger import logger
from app.schemas.tool_response import TravelRouteData
from app.utils.backend_notifier import notify_backend_route_created

# 백그라운드 작업용 스레드 풀
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="backend_notifier")


def _run_async_notification(workspace_id: str, route_data: TravelRouteData) -> None:
    """별도 스레드에서 비동기 알림 함수를 실행합니다."""
    asyncio.run(notify_backend_route_created(workspace_id, route_data))


def handle_travel_route_notification(state: AgentState, content: Any) -> None:
    """
    create_travel_route 도구 실행 결과를 Backend에 전달하여
    POI를 일괄 생성하고 모든 클라이언트에게 브로드캐스트합니다.

    Args:
        state: 현재 AgentState (session_id 포함)
        content: create_travel_route 도구 실행 결과 (ToolResult 형식)
    """
    try:
        # content가 문자열이면 JSON 파싱
        if isinstance(content, str):
            content = json.loads(content)

        # 성공 여부 확인
        if not content.get("success", False):
            logger.warning(f"[travel_route] Tool execution failed: {content.get('error')}")
            return

        # data 추출
        data = content.get("data")
        if not data:
            logger.warning("[travel_route] No data in tool result")
            return

        # TravelRouteData로 변환
        route_data = TravelRouteData(**data)

        # session_id 가져오기 (workspace_id와 동일)
        workspace_id = state.get("session_id")
        if not workspace_id:
            logger.error("[travel_route] No session_id in state")
            return

        # Backend에 비동기 알림 (백그라운드 스레드에서 실행)
        _executor.submit(_run_async_notification, workspace_id, route_data)

        logger.info(
            f"[travel_route] Backend notification scheduled for workspace {workspace_id}"
        )
    except Exception as e:
        logger.error(f"[travel_route] Error handling route notification: {e}", exc_info=True)
