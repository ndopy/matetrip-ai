from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from datetime import datetime


class ProfileEmbeddingReqMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., alias="userId", min_length=36)


class BehaviorEmbeddingReqMessage(BaseModel):
    """RabbitMQ로 받는 행동 이벤트 메시지 (간소화됨)"""

    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., alias="userId", min_length=36)
    place_id: str = Field(..., alias="placeId", description="places 테이블의 ID")
    event_type: str = Field(..., alias="eventType")
    created_at: datetime = Field(
        ...,
        alias="createdAt",
        validation_alias=AliasChoices("created_at", "timestamp", "createdAt"),
    )
    weight: float
    planday_id: str | None = Field(None, alias="plandayId")
    workspace_id: str | None = Field(None, alias="workspaceId")
