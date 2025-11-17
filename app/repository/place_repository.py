from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from sqlalchemy import func, text
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

    def find_nearby_places(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Place]:
        """
        주어진 좌표 주변의 장소를 검색합니다.

        Args:
            latitude: 위도
            longitude: 경도
            radius_km: 검색 반경 (km 단위, 기본값: 5km)
            category: 카테고리 필터 (예: '음식', '숙박', '레포츠' 등)
            limit: 최대 결과 개수 (기본값: 10)

        Returns:
            거리순으로 정렬된 장소 리스트
        """
        # Haversine 공식을 사용한 거리 계산 (km 단위)
        distance_formula = func.acos(
            func.cos(func.radians(latitude))
            * func.cos(func.radians(Place.latitude))
            * func.cos(func.radians(Place.longitude) - func.radians(longitude))
            + func.sin(func.radians(latitude)) * func.sin(func.radians(Place.latitude))
        ) * 6371  # 지구 반지름 (km)

        query = (
            self._db.query(Place, distance_formula.label("distance"))
            .filter(distance_formula <= radius_km)
        )

        # 카테고리 필터링
        if category:
            query = query.filter(Place.category == category)

        # 거리순 정렬 및 제한
        results = query.order_by(text("distance")).limit(limit).all()

        # Place 객체만 추출하여 반환
        return [place for place, distance in results]
