from pydantic import BaseModel, Field


class ProfileEmbeddingReqMessage(BaseModel):
    user_id: str = Field(..., min_length=35)


class BehaviorEmbeddingReqMessage(BaseModel):
    user_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    latitude: float = Field(..., ge=-90.0, le=90.0)
