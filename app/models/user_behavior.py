from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import TEXT, TIMESTAMP, Numeric, Integer, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from pgvector.sqlalchemy import VECTOR as VectorColumn

if TYPE_CHECKING:
    from pgvector import Vector as VECTOR
else:
    from pgvector.sqlalchemy import VECTOR

from app.models.base import Base


class UserBehaviorEvent(Base):
    """사용자 행동 이벤트 원본 데이터"""

    __tablename__ = "user_behavior_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        TEXT, nullable=False, index=True
    )  # POI_MARK, POI_SCHEDULE, POI_UNMARK, POI_UNSCHEDULE

    event_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # 행동별 상세 데이터

    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # 행동 가중치

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    workspace_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    place_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class UserBehaviorEmbedding(Base):
    """사용자별 집계된 행동 임베딩"""

    __tablename__ = "user_behavior_embeddings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    behavior_embedding: Mapped[Optional["VECTOR"]] = mapped_column(
        VectorColumn(1024), nullable=True
    )  # 행동 기반 임베딩 벡터 (장소 임베딩 가중평균)

    aggregated_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # 집계된 통계 데이터 (카테고리별 점수 등)

    last_updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    total_events_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
