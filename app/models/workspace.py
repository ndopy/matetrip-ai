from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import TEXT, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base


class Workspace(Base):
    """워크스페이스 모델 - 게시글당 하나의 워크스페이스"""

    __tablename__ = "workspace"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("post.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # post_id는 unique (1:1 관계)
    )

    workspace_name: Mapped[str] = mapped_column(TEXT, nullable=False)

    memo: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
