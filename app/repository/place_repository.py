from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint
from geoalchemy2 import Geography

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
        주어진 좌표 주변의 장소를 검색합니다. (PostGIS 사용)

        Args:
            latitude: 위도
            longitude: 경도
            radius_km: 검색 반경 (km 단위, 기본값: 5km)
            category: 카테고리 필터 (예: '음식', '숙박', '레포츠' 등)
            limit: 최대 결과 개수 (기본값: 10)

        Returns:
            거리순으로 정렬된 장소 리스트
        """
        # PostGIS geography로 검색 위치 생성
        print("[Place Repository : find_nearby_places 함수]")
        search_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326).cast(
            Geography
        )

        # ST_DWithin으로 반경 내 장소 필터링 (GiST 인덱스 사용)
        # radius_km * 1000 = 미터 단위로 변환
        query = self._db.query(
            Place, ST_Distance(Place.location, search_point).label("distance")
        ).filter(ST_DWithin(Place.location, search_point, radius_km * 1000))

        # 카테고리 필터링
        if category:
            query = query.filter(Place.category == category)

        # 거리순 정렬 및 제한
        results = query.order_by("distance").limit(limit).all()

        # Place 객체만 추출하여 반환
        return [place for place, _ in results]
