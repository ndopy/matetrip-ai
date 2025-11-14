from pydantic import BaseModel, ConfigDict, Field


class ProfileEmbeddingReqMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., alias="userId", min_length=35)


class BehaviorEmbeddingReqMessage(BaseModel):
    # populate_by_name=True : 필드의 "python 변수 이름"으로도 값을 넣을 수 있게 해주는 옵션.(별칭도 가능)
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., alias="userId", min_length=1)
    title: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    latitude: float = Field(..., ge=-90.0, le=90.0)
