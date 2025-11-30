"""여행 루트 생성 서비스 (순수 비즈니스 로직)"""

from typing import List, Optional, Tuple

from app.common.logger import logger
from app.service.place_service import PlaceService
from app.utils.geocoding import fetch_coordinates_from_address
from app.schemas.route_request import CreateRouteRequest
from app.schemas.route_tool import TravelRouteResponse, TravelRouteWaypoint
from app.schemas.routes import Coordinate
from app.schemas.place import NearbyPlaceResponse


class RouteService:
    """여행 루트 생성 서비스"""

    def __init__(self, place_service: PlaceService):
        self.place_service = place_service

    def create_travel_route(
        self, request: CreateRouteRequest
    ) -> TravelRouteResponse:
        """여행 루트 생성"""
        # 경유지를 일자별로 분배
        waypoints_per_day = self._distribute_waypoints(
            len(request.waypoints), request.days
        )

        # 경유지별 추천 생성
        route_data = self._build_waypoints(
            waypoints=request.waypoints,
            waypoints_per_day=waypoints_per_day,
            category=request.category,
            radius_km=request.radius_km,
            nearby_places_per_waypoint=request.nearby_places_per_waypoint,
            excluded_place_ids=request.excluded_place_ids or [],
        )

        return TravelRouteResponse(
            total_days=request.days,
            waypoints_count=len(request.waypoints),
            route=route_data,
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

    def _build_waypoints(
        self,
        waypoints: List[str],
        waypoints_per_day: List[int],
        category: Optional[str],
        radius_km: float,
        nearby_places_per_waypoint: int,
        excluded_place_ids: List[str],
    ) -> List[TravelRouteWaypoint]:
        """경유지별 추천 생성"""
        route: List[TravelRouteWaypoint] = []
        waypoint_iter = enumerate(waypoints)

        for day_num, count_in_day in enumerate(waypoints_per_day, start=1):
            for seq_in_day in range(count_in_day):
                waypoint_idx, waypoint = next(waypoint_iter)
                route.append(
                    self._build_single_waypoint(
                        waypoint=waypoint,
                        waypoint_index=waypoint_idx,
                        day=day_num,
                        sequence_in_day=seq_in_day,
                        category=category,
                        radius_km=radius_km,
                        nearby_places_per_waypoint=nearby_places_per_waypoint,
                        excluded_place_ids=excluded_place_ids,
                    )
                )

        return route

    def _build_single_waypoint(
        self,
        waypoint: str,
        waypoint_index: int,
        day: int,
        sequence_in_day: int,
        category: Optional[str],
        radius_km: float,
        nearby_places_per_waypoint: int,
        excluded_place_ids: List[str],
    ) -> TravelRouteWaypoint:
        """경유지 한 개에 대한 정보 및 주변 추천 생성"""
        logger.info(f"경유지 {waypoint_index + 1} ({day}일차, 순서 {sequence_in_day}): {waypoint}")

        try:
            latitude, longitude = fetch_coordinates_from_address(waypoint)
        except ValueError as e:
            logger.warning(f"경유지 '{waypoint}' 좌표를 찾을 수 없습니다: {e}")
            return TravelRouteWaypoint(
                waypoint_name=waypoint,
                waypoint_index=waypoint_index,
                day=day,
                sequence_in_day=sequence_in_day,
                coordinates=None,
                nearby_places=[],
                error=f"'{waypoint}' 위치를 찾을 수 없습니다.",
            )

        # 주변 장소 조회
        nearby_places_entities = self.place_service.find_nearby_places(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            category=category,
            limit=nearby_places_per_waypoint,
            excluded_place_ids=excluded_place_ids,
        )

        logger.info(f"경유지 '{waypoint}' 주변 {len(nearby_places_entities)}개 장소 추천")

        nearby_places = [
            NearbyPlaceResponse.from_entity(place) for place in nearby_places_entities
        ]

        return TravelRouteWaypoint(
            waypoint_name=waypoint,
            waypoint_index=waypoint_index,
            day=day,
            sequence_in_day=sequence_in_day,
            coordinates=Coordinate(latitude=latitude, longitude=longitude),
            nearby_places=nearby_places,
            error=None,
        )
