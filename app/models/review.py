from typing import Optional, Text
from uuid import UUID, uuid4
from pgvector import Vector
from sqlalchemy import TEXT, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from torch import embedding
from app.models.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class PlaceReview(Base):
    __tablename__ = "place_review"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    source_url: Mapped[str] = mapped_column(TEXT, nullable=False)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(768), nullable=True)  # type: ignore
    created_at: Mapped[float] = mapped_column()
