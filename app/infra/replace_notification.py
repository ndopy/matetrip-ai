"""
장소 교체 결과를 Backend에 브로드캐스트하는 알림 유틸

- LangGraph 후처리 노드(handle_replace_places_node)에서 호출
- 비동기 httpx 호출을 별도 스레드에서 실행해 에이전트 흐름을 막지 않음
- Backend가 DB 업데이트 + Redis 캐시 동기화 + Socket 브로드캐스트 수행
"""

import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor
from typing import List

from app.agent.state import AgentState
from app.common.logger import logger
from app.schemas.backend_notification import ReplaceScheduleNotification
from app.utils.backend_notifier import get_nestjs_server_url

# 백그라운드 작업용 스레드 풀
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="replace_notifier")


def _run_async_notification(
    workspace_id: str, notification: ReplaceScheduleNotification
) -> None:
    """ThreadPoolExecutor에서 asyncio 호출을 실행."""
    asyncio.run(notify_backend_places_replaced(workspace_id, notification))


async def notify_backend_places_replaced(
    workspace_id: str, notification: ReplaceScheduleNotification
) -> None:
    """
    Backend에 장소 교체 정보를 전달하여 DB 업데이트 및 Socket 브로드캐스트

    Backend 처리 흐름:
    1. replacements의 old_place_id로 기존 POI 조회 (day, sequence 획득)
    2. 기존 POI 삭제
    3. 새 POI 생성 (기존 POI의 day, sequence 재사용)
    4. Redis 캐시 동기화 (workspace의 전체 POI 리스트 갱신)
    5. Socket.IO 브로드캐스트 (모든 클라이언트에게 갱신된 POI 리스트 전송)

    Args:
        workspace_id: 워크스페이스 ID (session_id와 동일)
        notification: 장소 교체 알림 DTO
    """
    nestjs_server_url = get_nestjs_server_url()
    if not nestjs_server_url:
        logger.warning("[replace_notifier] NESTJS_SERVER_URL not set, skipping")
        return

    payload = notification.model_dump()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{nestjs_server_url}/workspace/{workspace_id}/ai/replace-schedule",
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"[replace_notifier] Successfully replaced {len(notification.replacements)} places "
                f"for workspace {workspace_id}: {result}"
            )
    except httpx.HTTPError as e:
        logger.error(
            f"[replace_notifier] Failed to notify backend for workspace {workspace_id}: {e}",
            exc_info=True,
        )
        # 에러가 발생해도 AI 응답은 계속 진행 (사용자에게는 응답 제공)


def schedule_replace_notification(
    state: AgentState, replaced_place_ids: List[str], new_places: List[dict]
) -> None:
    """
    replace_places Tool 결과를 받아 Backend 알림을 예약.
    Backend 처리 흐름:
    1. replacements의 old_place_id로 기존 POI를 DB 조회 (day, sequence 정보 획득)
    2. 기존 POI 삭제
    3. 새 POI 생성 (기존 POI의 day, sequence 재사용)
    4. Redis 캐시 동기화 (workspace의 전체 POI 리스트 갱신)
    5. Socket.IO 브로드캐스트 (연결된 모든 클라이언트에게 갱신된 POI 리스트 전송)

    Args:
        state: Agent 상태 (session_id 추출용)
        replaced_place_ids: 교체된 기존 POI ID 목록
        new_places: 새로 추천된 장소 목록 (NearbyPlaceResponse dict)
    """
    workspace_id = state.get("session_id")
    if not workspace_id or not replaced_place_ids or not new_places:
        logger.warning("[replace_notifier] Invalid input")
        return

    # DTO 생성
    notification: ReplaceScheduleNotification = ReplaceScheduleNotification.create(
        replaced_place_ids=replaced_place_ids,
        new_places=new_places,
        source="ai_replace",
    )

    try:
        _executor.submit(_run_async_notification, workspace_id, notification)
        logger.info(
            f"[replace_notifier] Backend notification scheduled for workspace {workspace_id}"
        )
    except Exception as e:
        logger.error(f"[replace_notifier] Error scheduling notification: {e}")
