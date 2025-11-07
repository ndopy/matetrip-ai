from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import JSON, TEXT, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

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

    title: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    tags: Mapped[Optional[list[str]]] = mapped_column(
        JSON, nullable=True
    )  # 장소 태그 (예: ["맛집", "분위기좋음", "데이트"])
    summary: Mapped[Optional[str]] = mapped_column(
        TEXT, nullable=True
    )  # 리뷰 요약 (3-4줄)

    # reviews: Mapped[list["Review"]] = relationship("Review", back_populates="place")
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
