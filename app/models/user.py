from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import ConfigDict
from sqlalchemy import TEXT, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base


class User(Base):
    """사용자 모델"""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    email: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)

    hashed_password: Mapped[str] = mapped_column(TEXT, nullable=False)

    model_config = ConfigDict(from_attributes=True)
