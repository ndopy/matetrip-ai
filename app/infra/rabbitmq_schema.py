from pydantic import BaseModel, ConfigDict, Field


class ProfileEmbeddingReqMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., alias="userId", min_length=36)


class BehaviorEventData(BaseModel):
    """행동 이벤트 상세 데이터"""

    model_config = ConfigDict(populate_by_name=True)

    place_id: str | None = Field(None, alias="placeId")
    place_name: str | None = Field(None, alias="placeName")
    category: str | None = None
    workspace_id: str | None = Field(None, alias="workspaceId")
    plan_day_id: str | None = Field(None, alias="planDayId")


class BehaviorEmbeddingReqMessage(BaseModel):
    """RabbitMQ로 받는 행동 이벤트 메시지"""

    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., alias="userId", min_length=1)
    event_type: str = Field(..., alias="eventType")
    timestamp: str
    event_data: BehaviorEventData = Field(..., alias="eventData")
    weight: float
    workspace_id: str | None = Field(None, alias="workspaceId")
    place_id: str | None = Field(None, alias="placeId")
