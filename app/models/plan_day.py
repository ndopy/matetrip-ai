from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, date
from sqlalchemy import INTEGER, DATE, TIMESTAMP, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base


class PlanDay(Base):
    """여행 계획 일차별 모델"""

    __tablename__ = "plan_day"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    day_no: Mapped[int] = mapped_column(
        INTEGER,
        nullable=False,
        info={"check": "day_no >= 1"},
    )

    plan_date: Mapped[Optional[date]] = mapped_column(DATE, nullable=True)

    __table_args__ = (CheckConstraint("day_no >= 1", name="check_day_no_positive"),)
