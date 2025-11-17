from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint
from geoalchemy2 import Geography

from app.models.place import Place
from app.models.user_behavior import UserBehaviorEvent
from app.schemas.place import PopularPlaceResponse
from app.enums.place import RegionGroupType


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

    def find_popular_places_by_region(
        self,
        region: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[PopularPlaceResponse]:
        """
        특정 지역에서 사용자 행동 기록을 기반으로 인기 장소를 검색합니다.

        Args:
            region: 지역명 (예: '서울특별시', '대전광역시', '제주도' 등)
            category: 카테고리 필터 (예: '음식', '숙박', '레포츠' 등)
            limit: 최대 결과 개수 (기본값: 10)

        Returns:
            인기도 순으로 정렬된 장소 DTO 리스트
            각 DTO는 장소 정보 + popularity_score를 포함
        """
        # 인기도 점수 계산: POI_MARK, POI_SCHEDULE 이벤트 개수
        popularity_score = func.count(func.distinct(UserBehaviorEvent.id)).label(
            "popularity_score"
        )
        # TODO: Net Count로 변경하기

        # 기본 쿼리: Place LEFT JOIN UserBehaviorEvent
        stmt = select(
            Place.id,
            Place.title,
            Place.address,
            Place.category,
            Place.tags,
            Place.summary,
            Place.image_url,
            Place.longitude,
            Place.latitude,
            Place.region,
            popularity_score,
        ).outerjoin(
            UserBehaviorEvent,
            (Place.id == UserBehaviorEvent.place_id)
            & (UserBehaviorEvent.event_type.in_(["POI_MARK", "POI_SCHEDULE"])),
        )

        # 지역 필터링 로직:
        # - region이 RegionGroupType enum 값이면 region 컬럼으로 검색
        # - 아니면 sido 컬럼으로 검색 (예: '서울특별시', '대전광역시')
        valid_region_values = {r.value for r in RegionGroupType}
        if region in valid_region_values:
            # enum 값이면 region 컬럼 검색
            stmt = stmt.where(Place.region == region)
        else:
            # sido 값이면 sido 컬럼만 검색
            stmt = stmt.where(Place.sido == region)

        # 카테고리 필터링 (선택적)
        if category:
            stmt = stmt.where(Place.category == category)

        # 그룹화 및 정렬
        stmt = (
            stmt.group_by(
                Place.id,
                Place.title,
                Place.address,
                Place.category,
                Place.tags,
                Place.summary,
                Place.image_url,
                Place.longitude,
                Place.latitude,
                Place.region,
            )
            .order_by(popularity_score.desc(), Place.created_at.desc())
            .limit(limit)
        )

        # 쿼리 실행
        result = self._db.execute(stmt)
        rows = result.fetchall()

        # Row -> DTO 변환
        return [
            PopularPlaceResponse(
                id=str(row[0]),
                title=row[1],
                address=row[2],
                category=row[3],
                tags=row[4],
                summary=row[5],
                image_url=row[6],
                longitude=row[7],
                latitude=row[8],
                region=row[9],
                popularity_score=row[10],
            )
            for row in rows
        ]
