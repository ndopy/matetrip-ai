from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
