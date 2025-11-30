"""POI 분석 요청/응답 DTO"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


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


class DayAnalysis(BaseModel):
    """일차별 분석 결과"""

    reason: str = Field(..., description="분석 사유")
    missing_categories: List[str] = Field(default_factory=list, description="부족 카테고리")
    category_distribution: Dict[str, int] = Field(
        default_factory=dict, description="카테고리 분포"
    )
    current_poi_count: int = Field(..., description="현재 POI 개수")


class DayRecommendation(BaseModel):
    """일차별 추천 결과"""

    day_no: int = Field(..., description="일차 번호")
    plan_date: str = Field(..., description="일정 날짜")
    analysis: DayAnalysis = Field(..., description="분석 결과")
    recommendations: List[dict] = Field(default_factory=list, description="추천 장소")


class PoiAnalysisResponse(BaseModel):
    """POI 분석 응답"""

    total_days: int = Field(..., description="전체 일수")
    daily_reports: List[DayRecommendation] = Field(..., description="일차별 리포트")
