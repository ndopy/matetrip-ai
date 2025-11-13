from pyexpat import model
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Coordinate(BaseModel):
    """WGS84 좌표."""

    longitude: float = Field(..., description="경도")
    latitude: float = Field(..., description="위도")


class RouteSummary(BaseModel):
    """두 지점 간의 경로 요약 정보."""

    duration: float = Field(..., description="소요시간(초)")
    distance: float = Field(..., description="거리(미터)")
    origin: Coordinate = Field(..., description="출발 좌표")
    destination: Coordinate = Field(..., description="도착 좌표")


class POICoordinate(BaseModel):
    """최적화 대상 POI 좌표 정보."""

    id: str = Field(..., description="POI 고유 ID")
    longitude: float = Field(..., description="경도")
    latitude: float = Field(..., description="위도")


class RouteOptimizeResponse(BaseModel):
    """경로 최적화 결과."""

    ids: List[str] = Field(..., description="최적화된 POI ID 순서")
    routes: List[RouteSummary] = Field(
        ..., description="최적 경로를 구성하는 구간 요약 (순서대로)"
    )
    total_duration: float = Field(..., description="총 소요시간(초)")
    total_distance: float = Field(..., description="총 거리(미터)")


class OptimizeRouteRequest(BaseModel):
    """경로 최적화 요청"""

    poi_list: List[POICoordinate] = Field(..., description="최적화할 POI 리스트")
    start_index: Optional[int] = Field(None, description="시작 지점 인덱스 (고정)")
    end_index: Optional[int] = Field(None, description="종료 지점 인덱스 (고정)")

    @field_validator("poi_list")
    def validate_poi_list(cls, poi_list: List[POICoordinate]):
        if len(poi_list) == 0:
            raise ValueError("POI 리스트가 비어있습니다.")
        return poi_list


class OptimizeAndBroadcastRequest(BaseModel):
    """경로 최적화 + NestJS 브로드캐스트 요청"""

    workspace_id: str = Field(..., description="워크스페이스 ID")
    plan_day_id: str = Field(..., description="일정 day ID")
    poi_list: List[POICoordinate] = Field(..., description="최적화할 POI 리스트")
    start_index: Optional[int] = Field(None, description="시작 지점 인덱스 (고정)")
    end_index: Optional[int] = Field(None, description="종료 지점 인덱스 (고정)")
