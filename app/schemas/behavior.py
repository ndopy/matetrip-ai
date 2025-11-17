from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from app.enums.user_behavior import BehaviorEventType
from app.schemas.rabbitmq_schema import BehaviorEmbeddingReqMessage


class SaveBehaviorEventDto(BaseModel):
    """행동 이벤트 저장 DTO (간소화됨)"""

    user_id: str = Field(..., description="사용자 ID")
    place_id: str = Field(..., description="장소 ID (places 테이블)")
    workspace_id: Optional[str] = Field(None, description="워크스페이스 ID")
    planday_id: Optional[str] = Field(None, description="플랜 데이 ID")
    # todo: Enum으로 전부 바뀌면 str말고 enum으로
    event_type: str = Field(
        ..., description="이벤트 타입 (POI_MARK, POI_SCHEDULE, etc.)"
    )
    weight: float = Field(..., description="행동 가중치")
    created_at: datetime = Field(..., description="이벤트 발생 시간")

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
            created_at=message.created_at,
        )


class WeightedPlaceEmbeddingDto(BaseModel):
    """행동 임베딩 계산에 사용되는 장소별 벡터 DTO"""

    place_id: UUID
    weight: float
    created_at: datetime
    event_type: BehaviorEventType
    place_embedding: List[float]
    place_name: str
    category: Optional[str] = None

    model_config = {"from_attributes": True}


class UserEventResDto(BaseModel):
    """이벤트 상세 DTO"""

    event_id: UUID
    event_type: BehaviorEventType
    created_at: datetime
    workspace_id: Optional[UUID] = None
    place_id: UUID

    model_config = {"from_attributes": True}
