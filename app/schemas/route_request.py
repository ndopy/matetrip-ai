"""여행 루트 생성 요청 DTO"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CreateRouteRequest(BaseModel):
    """여행 루트 생성 요청 DTO (3개 이상 파라미터 캡슐화)"""

    waypoints: List[str] = Field(..., description="경유지 리스트")
    days: int = Field(1, description="여행 일수")
    nearby_places_per_waypoint: int = Field(2, description="경유지당 추천 장소 개수")
    radius_km: float = Field(4.0, description="검색 반경 (km)")
    category: Optional[str] = Field(None, description="카테고리 필터")
    excluded_place_ids: List[str] = Field(
        default_factory=list, description="제외할 장소 ID 리스트"
    )

    @classmethod
    def create(
        cls,
        *,
        waypoints: List[str],
        days: int = 1,
        nearby_places_per_waypoint: int = 2,
        radius_km: float = 4.0,
        category: Optional[str] = None,
        excluded_place_ids: List[str] = [],
    ) -> "CreateRouteRequest":
        """요청 DTO 생성 팩토리 메서드"""
        return cls(
            waypoints=waypoints,
            days=days,
            nearby_places_per_waypoint=nearby_places_per_waypoint,
            radius_km=radius_km,
            category=category,
            excluded_place_ids=excluded_place_ids,
        )


class RouteBuildConfig(BaseModel):
    """여행 루트 생성 시 필요한 파라미터 묶음 (계산된 값 포함)"""

    waypoints: List[str] = Field(..., description="경유지 리스트")
    waypoints_per_day: List[int] = Field(..., description="일차별 경유지 개수")
    category: Optional[str] = Field(None, description="카테고리 필터")
    radius_km: float = Field(..., description="검색 반경 (km)")
    nearby_places_per_waypoint: int = Field(..., description="경유지당 추천 장소 개수")
    excluded_place_ids: List[str] = Field(
        default_factory=list, description="제외할 장소 ID 리스트"
    )

    @classmethod
    def from_request(
        cls, request: CreateRouteRequest, waypoints_per_day: List[int]
    ) -> "RouteBuildConfig":
        """CreateRouteRequest + 분배 결과를 캡슐화"""
        return cls(
            waypoints=request.waypoints,
            waypoints_per_day=waypoints_per_day,
            category=request.category,
            radius_km=request.radius_km,
            nearby_places_per_waypoint=request.nearby_places_per_waypoint,
            excluded_place_ids=request.excluded_place_ids,
        )


class WaypointAssignment(BaseModel):
    """일차/순서가 할당된 경유지 정보"""

    index: int = Field(..., description="원본 경유지 인덱스 (0부터)")
    name: str = Field(..., description="경유지 명")
    day: int = Field(..., description="일차 번호 (1부터)")
    sequence_in_day: int = Field(..., description="해당 일차 내 순서 (0부터)")
