from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import JSON, TEXT, Float, String, Integer, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from pgvector.sqlalchemy import VECTOR as VectorColumn

if TYPE_CHECKING:
    from pgvector import Vector as VECTOR
else:
    from pgvector.sqlalchemy import VECTOR

from app.models.base import Base


"""
Mapped[T] : 타입힌트 친화적 문법 (타입힌트 + ORM 매핑)
ampped_column(실제 DB 컬럼 정의)
"""


class Place(Base):

    __tablename__ = "places"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    address: Mapped[str] = mapped_column(TEXT, nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSONB, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(
        JSONB, nullable=True
    )  # 장소 태그 (예: ["맛집", "분위기좋음", "데이트"])
    summary: Mapped[Optional[str]] = mapped_column(
        TEXT, nullable=True
    )  # 리뷰 요약 (3-4줄)
    image_url: Mapped[Optional[str]] = mapped_column(
        TEXT, nullable=True
    )  # 장소 대표 이미지 URL

    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)

    # 장소 대표 임베딩 (리뷰 기반 평균 벡터)
    embedding: Mapped[Optional["VECTOR"]] = mapped_column(
        VectorColumn(1024), nullable=True
    )

    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=True
    )
