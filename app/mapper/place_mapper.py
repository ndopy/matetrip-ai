from app.models.place import Place
from app.schemas.place import PlaceCreate, PlaceResponse


class PlaceMapper:

    @staticmethod
    def to_entity(dto: PlaceCreate) -> Place:
        return Place(
            title=dto.title,
            address=dto.address,
            longitude=dto.longitude,
            latitude=dto.latitude,
        )

    @staticmethod
    def to_response(entity: Place) -> PlaceResponse:
        return PlaceResponse.model_validate(entity)

    # title: Mapped[str] = mapped_column(TEXT, nullable=False)
    # address: Mapped[str] = mapped_column(TEXT, nullable=False)
    # categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    # tags: Mapped[Optional[list[str]]] = mapped_column(
    #     JSONB, nullable=True
    # )  # 장소 태그 (예: ["맛집", "분위기좋음", "데이트"])
    # summary: Mapped[Optional[str]] = mapped_column(
    #     TEXT, nullable=True
    # )  # 리뷰 요약 (3-4줄)

    # title: str = Field(..., description="장소 이름")
    # address: str = Field(..., description="장소 주소")
    # place_url: Optional[str] = Field(default="", description="장소 URL")
    # categories: list[str] = Field(default=[], description="장소 분류")
    # tags: Optional[list[str]] = Field(default=[], description="장소 태그")
    # summary: Optional[str] = Field(default="", description="리뷰 요약")
