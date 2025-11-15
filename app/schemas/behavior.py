from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SaveBehaviorEventDto(BaseModel):
    """행동 이벤트 저장 DTO"""

    user_id: str = Field(..., description="사용자 ID")
    event_type: str = Field(..., description="이벤트 타입 (POI_MARK, POI_SCHEDULE, etc.)")
    event_data: Dict[str, Any] = Field(..., description="이벤트 상세 데이터")
    weight: float = Field(..., description="행동 가중치")
    workspace_id: Optional[str] = Field(None, description="워크스페이스 ID")
    place_id: Optional[str] = Field(None, description="장소 ID")

    model_config = {"from_attributes": True}
