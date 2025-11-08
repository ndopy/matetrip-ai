from openai import BaseModel


class ReviewCreateRequest(BaseModel):
    place_id: str
    content: str
    source_url: str

    # id: Mapped[UUID] = mapped_column(
    #     PG_UUID(as_uuid=True),
    #     primary_key=True,
    #     default=uuid4,
    #     index=True,
    # )

    # place_id: Mapped[UUID] = mapped_column(
    #     PG_UUID(as_uuid=True),
    #     ForeignKey("places.id", ondelete="CASCADE"),
    #     nullable=False,
    # )

    # content: Mapped[str] = mapped_column(TEXT, nullable=False)
    # source_url: Mapped[str] = mapped_column(TEXT, nullable=False)
    # embedding: Mapped[Optional[Vector]] = mapped_column(Vector(768), nullable=True)  # type: ignore
    # created_at: Mapped[float] = mapped_column()


class ReviewCreateResponse(BaseModel):
    content: str
