"""
Backend API 호출을 위한 유틸리티 모듈
"""

import logging
import os
import httpx

from app.schemas.tool_response import TravelRouteData

logger = logging.getLogger(__name__)

nestjs_server_url = os.getenv("NESTJS_SERVER_URL")
# api_key = os.getenv("AI_SERVER_API_KEY")

# if not api_key:
#     logger.warning(
#         "AI_SERVER_API_KEY not set. Skipping backend notification for route creation."
#     )
# 일단 배포 환경에서 env맞추기 귀찮으니 나중에 ㄱ


async def notify_backend_route_created(
    workspace_id: str, route_data: TravelRouteData
) -> None:
    """
    Backend에 생성된 여행 코스를 전달하여 POI로 저장하고 모든 클라이언트에게 브로드캐스트합니다.

    Args:
        workspace_id: 워크스페이스 ID (session_id와 동일)
        route_data: AI가 생성한 여행 코스 데이터 (TravelRouteData)
    """

    # route_data.route에서 경유지(waypoints)와 장소(places)를 분리하여 추출
    waypoints = []
    places = []

    for waypoint_data in route_data.route:
        waypoint_day = getattr(waypoint_data, "day", None)
        waypoint_sequence = getattr(waypoint_data, "sequence_in_day", None)

        if waypoint_day is None or waypoint_sequence is None:
            logger.warning(
                f"Waypoint {getattr(waypoint_data, 'waypoint_name', 'unknown')} missing day or sequence info"
            )
            continue

        # 경유지 자체를 waypoints 배열에 추가
        waypoint_coords = getattr(waypoint_data, "coordinates", None)
        if waypoint_coords:
            waypoints.append(
                {
                    "waypointName": getattr(waypoint_data, "waypoint_name", ""),
                    "latitude": getattr(waypoint_coords, "latitude", None),
                    "longitude": getattr(waypoint_coords, "longitude", None),
                    "address": "",
                    "day": waypoint_day,
                    "sequence": waypoint_sequence * 10,  # 경유지는 sequence * 10
                }
            )

        # 해당 경유지 주변 장소들을 places 배열에 추가
        nearby_places = getattr(waypoint_data, "nearby_places", [])
        for idx, place in enumerate(nearby_places):
            if not getattr(place, "id", None) or not getattr(place, "title", None):
                continue
            places.append(
                {
                    "placeId": str(getattr(place, "id")),
                    "placeName": str(getattr(place, "title")),
                    "latitude": getattr(place, "latitude", None),
                    "longitude": getattr(place, "longitude", None),
                    "address": getattr(place, "address", "") or "",
                    "day": waypoint_day,
                    "sequence": waypoint_sequence * 10
                    + idx
                    + 1,  # 경유지 * 10 + nearby 순서
                }
            )

    if len(waypoints) == 0 and len(places) == 0:
        logger.info("No waypoints or places to send to backend")
        return

    payload = {"waypoints": waypoints, "places": places, "source": "ai_route"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{nestjs_server_url}/workspace/{workspace_id}/ai/schedule-batch",
                json=payload,
                # headers={"x-ai-api-key": api_key},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"Successfully notified backend for workspace {workspace_id}: "
                f"{result.get('count', 0)} POIs created"
            )
    except httpx.HTTPError as e:
        logger.error(
            f"Failed to notify backend for workspace {workspace_id}: {e}",
            exc_info=True,
        )
        # 에러가 발생해도 AI 응답은 계속 진행 (사용자에게는 응답 제공)
