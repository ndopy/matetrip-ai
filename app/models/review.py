from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import TEXT, ForeignKey, TIMESTAMP, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pgvector.sqlalchemy import Vector

if TYPE_CHECKING:
    from app.models.place import Place


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
    source_url: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)

    # 🆕 소프트 삭제 필드
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), nullable=False
    )
    # Relationship
    place: Mapped["Place"] = relationship("Place", back_populates="reviews")
