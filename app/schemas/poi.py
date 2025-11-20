"""
POI (Point of Interest) 관련 스키마
NestJS의 DateGroupedScheduledPoisResDto 구조에 맞춰 작성됨
"""

from typing import Optional
from pydantic import BaseModel, Field


class PlanDayScheduleSummaryDto(BaseModel):
    """일정의 날짜 요약 정보"""

    dayNo: int = Field(..., description="일차 번호 (1부터 시작)")
    planDate: str = Field(..., description="일정 날짜 (ISO 8601 형식)")

    class Config:
        from_attributes = True


class PoiResDto(BaseModel):
    """POI 상세 정보"""

    id: str = Field(..., description="POI 고유 ID")
    workspaceId: str = Field(..., description="워크스페이스 ID")
    createdBy: str = Field(..., description="생성자 ID")
    placeName: str = Field(..., description="장소 이름")
    address: str = Field(..., description="주소")
    longitude: float = Field(..., description="경도")
    latitude: float = Field(..., description="위도")
    planDayId: Optional[str] = Field(None, description="계획 일자 ID")
    placeId: str = Field(..., description="장소 ID")
    status: str = Field(..., description="POI 상태")
    sequence: int = Field(..., description="순서")

    class Config:
        from_attributes = True


class PlanDayScheduledPoisGroupDto(BaseModel):
    """날짜별로 그룹화된 POI 목록"""

    planDay: PlanDayScheduleSummaryDto = Field(..., description="일정 날짜 정보")
    pois: list[PoiResDto] = Field(default_factory=list, description="해당 날짜의 POI 목록")

    class Config:
        from_attributes = True


class DateGroupedScheduledPoisResDto(BaseModel):
    """날짜별로 그룹화된 전체 일정 응답 DTO"""

    planDayScheduledPoisGroup: list[PlanDayScheduledPoisGroupDto] = Field(
        default_factory=list, description="날짜별 POI 그룹 목록"
    )

    class Config:
        from_attributes = True
