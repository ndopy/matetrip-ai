from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from pgvector import Vector
from sqlalchemy import TEXT, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pgvector.sqlalchemy import Vector


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
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), nullable=False
    )
