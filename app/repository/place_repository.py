from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.place import Place


class PlaceRepository:
    """장소 관련 DB 작업을 담당하는 레포지토리."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @property
    def session(self) -> Session:
        return self._db

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    def refresh(self, place: Place) -> None:
        self._db.refresh(place)

    def find_by_id(self, place_id: UUID | int) -> Optional[Place]:
        return self._db.query(Place).filter(Place.id == place_id).first()
