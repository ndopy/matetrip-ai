from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import ConfigDict
from sqlalchemy import TEXT, Float, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, ENUM
from pgvector.sqlalchemy import VECTOR as VectorColumn
from geoalchemy2 import Geography

from app.enums import RegionGroupType

if TYPE_CHECKING:
    from pgvector import Vector as VECTOR
    from app.models.review import PlaceReview
else:
    from pgvector.sqlalchemy import VECTOR

from app.models.base import Base


"""
Mapped[T] : 타입힌트 친화적 문법 (타입힌트 + ORM 매핑)
mapped_column(실제 DB 컬럼 정의)
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
    category: Mapped[str] = mapped_column(TEXT, nullable=True)
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

    # 지역 그룹 (광역 단위)
    region: Mapped[Optional[str]] = mapped_column(
        ENUM(
            *[region.value for region in RegionGroupType],
            name="region_group_type",
            create_type=False,
        ),
        nullable=True,
    )

    # 시/도 (행정구역 단위: 서울특별시, 부산광역시, 대전광역시, 경기도 등)
    sido: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True, index=True)

    # 장소 대표 임베딩 (리뷰 기반 평균 벡터)
    embedding: Mapped[Optional["VECTOR"]] = mapped_column(
        VectorColumn(1024), nullable=True
    )

    # PostGIS 지리 정보 (공간 쿼리 최적화용)
    location: Mapped[Optional[Geography]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    reviews: Mapped[list["PlaceReview"]] = relationship(
        "PlaceReview",
        back_populates="place",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    model_config = ConfigDict(from_attributes=True)
