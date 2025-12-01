"""POI 분석 요청/응답 DTO"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.place import NearbyPlaceResponse


class AnalyzePoiRequest(BaseModel):
    """POI 분석 요청 DTO (3개 이상 파라미터 캡슐화)"""

    workspace_id: str = Field(..., description="워크스페이스 ID")
    day_no: Optional[int] = Field(None, description="특정 일차 (None이면 전체)")

    @classmethod
    def create(
        cls, *, workspace_id: str, day_no: Optional[int] = None
    ) -> "AnalyzePoiRequest":
        """요청 DTO 생성 팩토리 메서드"""
        return cls(workspace_id=workspace_id, day_no=day_no)


class CategoryBalanceInput(BaseModel):
    """카테고리 균형 분석 입력 DTO"""

    category_count: Dict[str, int] = Field(..., description="카테고리별 개수")
    day_idx: int = Field(..., description="일차 인덱스 (0부터 시작)")
    total_days: int = Field(..., description="전체 일수")
    day_label: str = Field(..., description="일차 라벨 (예: '1일차')")

    @classmethod
    def create(
        cls,
        *,
        category_count: Dict[str, int],
        day_idx: int,
        total_days: int,
        day_label: str,
    ) -> "CategoryBalanceInput":
        """입력 DTO 생성 팩토리 메서드"""
        return cls(
            category_count=category_count,
            day_idx=day_idx,
            total_days=total_days,
            day_label=day_label,
        )


class CategoryBalanceResult(BaseModel):
    """카테고리 균형 분석 결과 DTO"""

    missing_categories: List[str] = Field(
        default_factory=list, description="부족 카테고리"
    )
    reason: str = Field(..., description="분석 사유")


class DayPoi(BaseModel):
    """수집된 POI 요약"""

    id: str = Field(..., description="POI ID")
    place_name: str = Field(..., description="장소 이름")
    category: str = Field(..., description="카테고리")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")


class DayPoiCollection(BaseModel):
    """일차별 POI 수집 결과 DTO"""

    pois: List[DayPoi] = Field(default_factory=list, description="POI 목록")
    category_count: Dict[str, int] = Field(
        default_factory=dict, description="카테고리별 개수"
    )


class DayAnalysis(BaseModel):
    """일차별 분석 결과"""

    reason: str = Field(..., description="분석 사유")
    missing_categories: List[str] = Field(
        default_factory=list, description="부족 카테고리"
    )
    category_distribution: Dict[str, int] = Field(
        default_factory=dict, description="카테고리 분포"
    )
    current_poi_count: int = Field(..., description="현재 POI 개수")


class DayRecommendation(BaseModel):
    """일차별 추천 결과"""

    day_no: int = Field(..., description="일차 번호")
    plan_date: str = Field(..., description="일정 날짜")
    analysis: DayAnalysis = Field(..., description="분석 결과")
    recommendations: List[NearbyPlaceResponse] = Field(
        default_factory=list, description="추천 장소"
    )


class PoiAnalysisResponse(BaseModel):
    """POI 분석 응답"""

    total_days: int = Field(..., description="전체 일수")
    daily_reports: List[DayRecommendation] = Field(..., description="일차별 리포트")
