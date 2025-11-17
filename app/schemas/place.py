from typing import List, Optional, TYPE_CHECKING
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.enums.place import RegionGroupType

if TYPE_CHECKING:
    from app.models.place import Place


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


class NearbyPlaceRequest(BaseModel):
    """주변 장소 검색 요청 DTO"""

    latitude: float = Field(..., description="기준 위도")
    longitude: float = Field(..., description="기준 경도")
    radius_km: float = Field(5.0, description="검색 반경 (km 단위)")
    category: Optional[str] = Field(
        None,
        description="카테고리 필터 (음식, 숙박, 레포츠, 자연, 인문(문화/예술/역사), 추천코스)",
    )
    limit: int = Field(10, description="최대 결과 개수")

    @classmethod
    def from_coordinates(
        cls,
        *,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> "NearbyPlaceRequest":
        return cls(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            category=category,
            limit=limit,
        )


class NearbyPlaceResponse(BaseModel):
    """주변 장소 검색 응답 DTO"""

    id: str = Field(..., description="장소 ID")
    title: str = Field(..., description="장소명")
    address: str = Field(..., description="주소")
    category: Optional[str] = Field(None, description="카테고리")
    tags: Optional[List[str]] = Field(None, description="태그")
    summary: Optional[str] = Field(None, description="리뷰 요약")
    image_url: Optional[str] = Field(None, description="이미지 URL")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")

    model_config = {
        "from_attributes": True,
    }

    @classmethod
    def from_entity(cls, place: "Place") -> "NearbyPlaceResponse":
        return cls(
            id=str(place.id),
            title=place.title,
            address=place.address,
            category=place.category,
            tags=place.tags,
            summary=place.summary,
            image_url=place.image_url,
            latitude=place.latitude,
            longitude=place.longitude,
        )


class PopularPlaceRequest(BaseModel):
    """인기 장소 검색 요청 DTO"""

    region: str = Field(..., description="지역명 (예: 서울, 부산, 대전, 제주도 등)")
    category: Optional[str] = Field(
        None,
        description="카테고리 필터 (음식, 숙박, 레포츠, 자연, 인문(문화/예술/역사), 추천코스)",
    )
    limit: int = Field(10, description="최대 결과 개수")

    @classmethod
    def create(
        cls,
        *,
        region: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> "PopularPlaceRequest":
        return cls(
            region=region.strip(),
            category=category,
            limit=limit,
        )


class PopularPlaceResponse(BaseModel):
    """인기 장소 검색 응답 DTO"""

    id: str = Field(..., description="장소 ID")
    title: str = Field(..., description="장소명")
    address: str = Field(..., description="주소")
    category: Optional[str] = Field(None, description="카테고리")
    tags: Optional[List[str]] = Field(None, description="태그")
    summary: Optional[str] = Field(None, description="리뷰 요약")
    image_url: Optional[str] = Field(None, description="이미지 URL")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")
    region: Optional[str] = Field(None, description="지역")
    popularity_score: int = Field(
        0, description="인기도 점수 (마크/일정 추가 횟수)"
    )

    model_config = {
        "from_attributes": True,
    }
