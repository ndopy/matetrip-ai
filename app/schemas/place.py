from uuid import UUID
from pydantic import BaseModel, Field


class PlaseBase(BaseModel):
    title: str = Field(..., description="장소 이름")
    address: str = Field(..., description="장소 주소")
    place_url: str = Field(..., description="장소 URL")
    logitude: float = Field(..., description="경도")
    latitude: float = Field(..., description="위도")


# 장소 생성용 스키마
class PlaceCreate(PlaseBase):
    pass


class PlaceListCreateRequest(BaseModel):
    places: list[PlaceCreate] = Field(..., description="장소 리스트")


class PlaceResponse:
    id: UUID
