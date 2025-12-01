"""여행 루트 생성 서비스 (순수 비즈니스 로직)"""

from typing import List

from app.common.logger import logger
from app.service.place_service import PlaceService
from app.utils.geocoding import fetch_coordinates_from_address
from app.schemas.route_request import (
    CreateRouteRequest,
    RouteBuildConfig,
    WaypointAssignment,
)
from app.schemas.route_tool import TravelRouteResponse, TravelRouteWaypoint
from app.schemas.routes import Coordinate
from app.schemas.place import NearbyPlaceResponse


class RouteService:
    """여행 루트 생성 서비스"""

    def __init__(self, place_service: PlaceService):
        self.place_service = place_service

    def create_travel_route(self, request: CreateRouteRequest) -> TravelRouteResponse:
        """여행 루트 생성"""
        # 경유지를 일자별로 분배
        waypoints_per_day = self._distribute_waypoints(
            len(request.waypoints), request.days
        )

        # 경유지별 경로들을 추천하는 것(요청 + 계산값을 config로 캡슐화)
        config = RouteBuildConfig.from_request(request, waypoints_per_day)
        waypoint_plan = self._build_waypoint_routes(config)

        return TravelRouteResponse(
            total_days=request.days,
            waypoints_count=len(request.waypoints),
            route=waypoint_plan,
        )

    def _distribute_waypoints(self, total_waypoints: int, days: int) -> List[int]:
        """경유지를 일자별로 균등 분배"""
        base_count = total_waypoints // days
        remainder = total_waypoints % days

        result = []
        for day_idx in range(days):
            count = base_count + (1 if day_idx < remainder else 0)
            result.append(count)

        return result

    def _build_waypoint_routes(
        self, config: RouteBuildConfig
    ) -> List[TravelRouteWaypoint]:
        """경유지별 추천 생성"""
        route: List[TravelRouteWaypoint] = []
        assignments = self._assign_waypoints(config)

        for assignment in assignments:
            route.append(self._build_single_waypoint(assignment, config))

        return route

    def _assign_waypoints(self, config: RouteBuildConfig) -> List[WaypointAssignment]:
        """경유지 리스트에 일차/순서를 부여"""
        assignments: List[WaypointAssignment] = []
        idx = 0
        for day_num, count_in_day in enumerate(config.waypoints_per_day, start=1):
            for seq_in_day in range(count_in_day):
                if idx >= len(config.waypoints):
                    break
                assignments.append(
                    WaypointAssignment(
                        index=idx,
                        name=config.waypoints[idx],
                        day=day_num,
                        sequence_in_day=seq_in_day,
                    )
                )
                idx += 1
        return assignments

    def _build_single_waypoint(
        self, waypoint_task: WaypointAssignment, config: RouteBuildConfig
    ) -> TravelRouteWaypoint:
        """경유지 한 개에 대한 정보 및 주변 추천 생성"""
        logger.info(
            f"경유지 {waypoint_task.index + 1} ({waypoint_task.day}일차, 순서 {waypoint_task.sequence_in_day}): {waypoint_task.name}"
        )

        try:
            latitude, longitude = fetch_coordinates_from_address(waypoint_task.name)
        except ValueError as e:
            logger.warning(
                f"경유지 '{waypoint_task.name}' 좌표를 찾을 수 없습니다: {e}"
            )
            return TravelRouteWaypoint(
                waypoint_name=waypoint_task.name,
                waypoint_index=waypoint_task.index,
                day=waypoint_task.day,
                sequence_in_day=waypoint_task.sequence_in_day,
                coordinates=None,
                nearby_places=[],
                error=f"'{waypoint_task.name}' 위치를 찾을 수 없습니다.",
            )

        # 주변 장소 조회
        nearby_places_entities = self.place_service.find_nearby_places(
            latitude=latitude,
            longitude=longitude,
            radius_km=config.radius_km,
            category=config.category,
            limit=config.nearby_places_per_waypoint,
            excluded_place_ids=config.excluded_place_ids,
        )

        logger.info(
            f"경유지 '{waypoint_task.name}' 주변 {len(nearby_places_entities)}개 장소 추천"
        )

        return TravelRouteWaypoint(
            waypoint_name=waypoint_task.name,
            waypoint_index=waypoint_task.index,
            day=waypoint_task.day,
            sequence_in_day=waypoint_task.sequence_in_day,
            coordinates=Coordinate(latitude=latitude, longitude=longitude),
            nearby_places=[
                NearbyPlaceResponse.from_entity(place)
                for place in nearby_places_entities
            ],
            error=None,
        )
