from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PlaceBase(BaseModel):
    title: str = Field(..., description="장소 이름")
    address: str = Field(..., description="장소 주소")
    place_url: str = Field(..., description="장소 URL")
    longitude: float = Field(..., description="경도")
    latitude: float = Field(..., description="위도")


# 장소 생성용 스키마
class PlaceCreate(PlaceBase):
    pass


class PlaceListCreateRequest(BaseModel):
    places: list[PlaceCreate] = Field(..., description="장소 리스트")


class PlaceResponse(BaseModel):
    # id: UUID = Field(..., description="장소 ID")
    title: str = Field(..., description="장소 이름")
    address: str = Field(..., description="장소 주소")
    place_url: Optional[str] = Field(default="", description="장소 URL")
    categories: list[str] = Field(default=[], description="장소 분류")
    tags: Optional[list[str]] = Field(default=[], description="장소 태그")
    summary: Optional[str] = Field(default="", description="리뷰 요약")

    model_config = {
        "from_attributes": True,  # SQLAlchemy 객체에서 바로 변환 허용
    }

    # title: Mapped[str] = mapped_column(TEXT, nullable=False)
    # address: Mapped[str] = mapped_column(TEXT, nullable=False)
    # categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    # tags: Mapped[Optional[list[str]]] = mapped_column(
    #     JSONB, nullable=True
    # )  # 장소 태그 (예: ["맛집", "분위기좋음", "데이트"])
    # summary: Mapped[Optional[str]] = mapped_column(
    #     TEXT, nullable=True
    # )  # 리뷰 요약 (3-4줄)


class PlaceRecommendation(BaseModel):
    id: UUID
    title: str
    address: str
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    image_url: Optional[str] = None
    longitude: float
    latitude: float
    similarity: float = Field(..., description="0~1 사이 유사도 (1에 가까울수록 유사)")
