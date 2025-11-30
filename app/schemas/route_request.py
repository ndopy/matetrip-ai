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
    excluded_place_ids: Optional[List[str]] = Field(
        None, description="제외할 장소 ID 리스트"
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
        excluded_place_ids: Optional[List[str]] = None,
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
