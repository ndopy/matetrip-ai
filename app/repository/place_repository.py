from __future__ import annotations

import math
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

    def find_by_ids(self, place_ids: List[UUID]) -> List[Place]:
        if not place_ids:
            return []
        return self._db.query(Place).filter(Place.id.in_(place_ids)).all()

    def get_top_closest_places(
        self,
        latitude: float,
        longitude: float,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Place]:
        """
        주어진 좌표와 가장 가까운 장소들을 거리 순으로 반환합니다.

        Args:
            latitude: 기준 위도
            longitude: 기준 경도
            category: 필터링할 카테고리
            limit: 최대 결과 개수

        Returns:
            거리순 정렬된 장소 리스트

        """
        search_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326).cast(
            Geography
        )
        query = self._db.query(
            Place, ST_Distance(Place.location, search_point).label("distance")
        )
        if category:
            query = query.filter(Place.category == category)

        results = query.order_by("distance").limit(limit).all()
        return [place for place, _ in results]

    def find_places_within_radius(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        limit: int = 10,
        excluded_place_ids: List[str] = [],
    ) -> List[Place]:
        """
        주어진 좌표 주변의 장소를 검색합니다. (PostGIS 사용)
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

        # 제외할 장소 ID 필터링
        excluded_ids = list(excluded_place_ids)
        if excluded_ids:
            query = query.filter(~Place.id.in_(excluded_ids))
            # logger.debug(f"Excluding {len(excluded_ids)} places from radius search")
            print(f"[Place Repository : Excluding {len(excluded_ids)} places]")

        # 거리순 정렬 및 제한
        results = query.order_by("distance").limit(limit).all()

        print(f"[Place nearby 결과 = {len(results)}]")
        # Place 객체만 추출하여 반환
        return [place for place, _ in results]

    # @staticmethod
    # def _haversine_distance(
    #     lat1: float, lon1: float, lat2: float, lon2: float
    # ) -> float:
    #     """
    #     두 좌표 간의 거리를 Haversine 공식으로 계산합니다.

    #     Args:
    #         lat1, lon1: 첫 번째 지점의 위도, 경도
    #         lat2, lon2: 두 번째 지점의 위도, 경도

    #     Returns:
    #         거리 (미터 단위)
    #     """
    #     R = 6371000  # 지구 반경 (미터)

    #     # 라디안으로 변환
    #     lat1_rad = math.radians(lat1)
    #     lat2_rad = math.radians(lat2)
    #     delta_lat = math.radians(lat2 - lat1)
    #     delta_lon = math.radians(lon2 - lon1)

    #     # Haversine 공식
    #     a = (
    #         math.sin(delta_lat / 2) ** 2
    #         + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    #     )
    #     c = 2 * math.asin(math.sqrt(a))

    #     return R * c

    # # 테스트용 메서드(production 환경에서 안쓰는 메서드)
    # def find_nearby_places_haversine(
    #     self,
    #     latitude: float,
    #     longitude: float,
    #     radius_km: float = 5.0,
    #     category: Optional[str] = None,
    #     limit: int = 10,
    # ) -> List[Place]:
    #     """
    #     주어진 좌표 주변의 장소를 검색합니다. (Haversine 공식 사용 - 공간 인덱스 미사용)

    #     성능 비교를 위한 메서드로, 모든 장소를 Python에서 필터링합니다.
    #     공간 인덱스를 사용하지 않으므로 대용량 데이터에서는 느릴 수 있습니다.

    #     Args:
    #         latitude: 위도
    #         longitude: 경도
    #         radius_km: 검색 반경 (km 단위, 기본값: 5km)
    #         category: 카테고리 필터 (예: '음식', '숙박', '레포츠' 등)
    #         limit: 최대 결과 개수 (기본값: 10)

    #     Returns:
    #         거리순으로 정렬된 장소 리스트
    #     """
    #     print(
    #         "[Place Repository : find_nearby_places_haversine 함수 (공간 인덱스 미사용)]"
    #     )

    #     # 카테고리 필터만 DB에서 적용
    #     query = self._db.query(Place)
    #     if category:
    #         query = query.filter(Place.category == category)

    #     # 모든 장소를 가져옴 (공간 인덱스 미사용)
    #     all_places = query.all()

    #     # Python에서 거리 계산 및 필터링
    #     places_with_distance = []
    #     radius_m = radius_km * 1000  # km를 미터로 변환

    #     for place in all_places:
    #         if place.latitude is None or place.longitude is None:
    #             continue

    #         distance = self._haversine_distance(
    #             latitude, longitude, place.latitude, place.longitude
    #         )

    #         # 반경 내에 있는 장소만 추가
    #         if distance <= radius_m:
    #             places_with_distance.append((place, distance))

    #     # 거리순 정렬 및 제한
    #     places_with_distance.sort(key=lambda x: x[1])

    #     # Place 객체만 추출하여 반환
    #     return [place for place, _ in places_with_distance[:limit]]

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
