from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.routes import Coordinate
from app.schemas.place import NearbyPlaceResponse


class TravelRouteWaypoint(BaseModel):
    """여행 코스의 단일 경유지 정보"""

    waypoint_name: str = Field(..., description="경유지 이름")
    waypoint_index: int = Field(..., description="경유지 순서 (0부터 시작)")
    coordinates: Optional[Coordinate] = Field(
        None, description="경유지 좌표 (위치 찾기 실패 시 None)"
    )
    nearby_places: List[NearbyPlaceResponse] = Field(
        default_factory=list, description="경유지 주변 추천 장소 목록"
    )
    error: Optional[str] = Field(
        None, description="좌표 검색 실패 등 에러 메시지 (없으면 None)"
    )


class TravelRouteResponse(BaseModel):
    """여행 코스 생성 결과"""

    total_days: int = Field(..., description="총 여행 일수")
    waypoints_count: int = Field(..., description="경유지 개수")
    route: List[TravelRouteWaypoint] = Field(..., description="경유지별 추천 결과")
