"""
여행 루트 생성 결과를 Backend에 브로드캐스트하는 알림 유틸

- LangGraph 후처리 노드에서 호출
- 비동기 httpx 호출을 별도 스레드에서 실행해 에이전트 흐름을 막지 않음
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.agent.state import AgentState
from app.common.logger import logger
from app.schemas.tool_response import TravelRouteData
from app.utils.backend_notifier import notify_backend_route_created

# 백그라운드 작업용 스레드 풀
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="route_notifier")


def _run_async_notification(workspace_id: str, route_data: TravelRouteData) -> None:
    """ThreadPoolExecutor에서 asyncio 호출을 실행."""
    asyncio.run(notify_backend_route_created(workspace_id, route_data))


def schedule_route_notification(state: AgentState, content: Any) -> None:
    """
    create_travel_route Tool 결과를 받아 Backend 알림을 예약한다.
    실패나 누락된 필드는 로그만 남기고 에이전트 흐름을 막지 않는다.
    """
    try:
        payload = json.loads(content) if isinstance(content, str) else content

        if not isinstance(payload, dict) or not payload.get("success", False):
            logger.warning(
                f"[route_notifier] Tool failed or invalid payload: {getattr(payload, 'error', None)}"
            )
            return

        data = payload.get("data")
        if not data:
            logger.warning("[route_notifier] No data in tool result")
            return

        workspace_id = state.get("session_id")
        if not workspace_id:
            logger.error("[route_notifier] No session_id in state")
            return

        _executor.submit(_run_async_notification, workspace_id, TravelRouteData(**data))
        logger.info(
            f"[route_notifier] Backend notification scheduled for workspace {workspace_id}"
        )
    except Exception as e:
        logger.error(f"[route_notifier] Error scheduling notification: {e}")
