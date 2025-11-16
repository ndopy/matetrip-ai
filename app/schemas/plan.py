from pydantic import BaseModel, Field
from typing import List, Any

# --- 1. NestJS로부터 받을 데이터 (Input DTO) ---
class PlanGenerationRequest(BaseModel):
    """
    NestJS가 AI에게 계획 생성을 요청할 때 보낼 DTO
    """
    places: List[Any] = Field(description="장소 DTO 객체들의 리스트")
    total_date: int = Field(description="여행 총 일수")

# --- 2. AI가 반환할 데이터 (Output DTOs) ---
class DailyPlanIDs(BaseModel):
    """
    하루치 계획에 포함될 장소 ID들의 리스트
    """
    placeIDs: List[str] = Field(
        description="선별된 장소 ID들의 리스트. 예: ['poi_123', 'poi_124']"
    )

class PlanResponseIDs(BaseModel):
    """
    AI가 반환할 최종 ID 순서 객체
    """
    daily_plans: List[DailyPlanIDs]