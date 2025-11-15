from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

from schemas.rabbitmq_schema import BehaviorEmbeddingReqMessage


class SaveBehaviorEventDto(BaseModel):
    """행동 이벤트 저장 DTO (간소화됨)"""

    user_id: str = Field(..., description="사용자 ID")
    place_id: str = Field(..., description="장소 ID (places 테이블)")
    event_type: str = Field(
        ..., description="이벤트 타입 (POI_MARK, POI_SCHEDULE, etc.)"
    )
    weight: float = Field(..., description="행동 가중치")
    workspace_id: Optional[str] = Field(None, description="워크스페이스 ID")
    planday_id: Optional[str] = Field(None, description="플랜 데이 ID")

    model_config = {"from_attributes": True}

    @classmethod
    def from_message(
        cls, message: BehaviorEmbeddingReqMessage
    ) -> "SaveBehaviorEventDto":
        return cls(
            user_id=message.user_id,
            place_id=message.place_id,
            event_type=message.event_type,
            weight=message.weight,
            workspace_id=message.workspace_id,
            planday_id=message.planday_id,
        )
