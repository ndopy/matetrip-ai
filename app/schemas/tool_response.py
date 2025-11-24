"""
표준 도구 응답 스키마
모든 도구가 일관된 형식으로 결과를 반환하도록 정의합니다.
"""

from typing import List, Optional, TypeVar, Generic, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    """
    모든 도구의 표준 응답 포맷

    Example:
        성공 케이스:
        ToolResult(
            success=True,
            data=PlaceRecommendationData(places=[...], count=5),
            message="부산에서 인기 있는 장소 5곳을 찾았습니다."
        )

        실패 케이스:
        ToolResult(
            success=False,
            error="API 오류가 발생했습니다."
        )
    """

    success: bool = Field(description="도구 실행 성공 여부")
    data: Optional[T] = Field(default=None, description="성공 시 반환되는 데이터")
    error: Optional[str] = Field(default=None, description="실패 시 에러 메시지")
    message: Optional[str] = Field(
        default=None, description="사용자에게 표시할 메시지 (선택)"
    )


class PlaceRecommendationData(BaseModel):
    """
    장소 추천 결과 데이터
    recommend_popular_places_in_region, recommend_nearby_places, replace_single_place용
    """

    places: List[dict] = Field(description="추천된 장소 목록 (dict 형태)")
    count: int = Field(description="추천된 장소 개수")
    replaced_place_id: Optional[str] = Field(default=None, description="대체된 장소 ID (replace_single_place에서만 사용)")


class TravelRouteData(BaseModel):
    """
    여행 코스 생성 결과 데이터
    create_travel_route용

    places 필드는 route의 모든 nearby_places를 평탄화하여
    SimplePlace(id, title) 형태로 저장합니다.
    """

    total_days: int = Field(description="총 여행 일수")
    waypoints_count: int = Field(description="경유지 개수")
    route: List[dict] = Field(description="경유지별 상세 정보")
    places: List[dict] = Field(default_factory=list, description="전체 장소 목록 (id, title만)")

    def model_post_init(self, __context: Any) -> None:
        """
        모델 초기화 후 places 필드를 자동으로 계산
        route에서 모든 nearby_places를 평탄화하여 SimplePlace 형태로 저장
        """
        # route에서 모든 nearby_places 추출하여 SimplePlace 형태로 변환
        all_places = []
        for waypoint in self.route:
            if isinstance(waypoint, dict):
                nearby_places = waypoint.get("nearby_places", [])
                for place in nearby_places:
                    if isinstance(place, dict) and "id" in place and "title" in place:
                        # SimplePlace 형태로 변환 (id, title만)
                        all_places.append({
                            "id": place["id"],
                            "title": place["title"]
                        })

        # places 필드에 저장
        self.places = all_places
