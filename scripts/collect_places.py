"""
카카오 Local API를 사용하여 전국 장소 데이터를 수집하는 배치 스크립트

실행 방법:
    python scripts/collect_places.py

또는 uv 사용:
    uv run python scripts/collect_places.py

네이버 API 제한 고려:
    - 네이버 블로그 검색 API: 하루 25,000건 제한
    - 안전하게 하루 20,000건으로 제한 설정
"""

import sys
import os
import asyncio
import logging
from typing import List, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.place import Place
from app.service.kakao_local_service import KakaoLocalService
from app.service.place_service import PlaceService
from app.data.korea_regions import ALL_REGIONS, CATEGORY_CODES, REGIONS_BY_AREA

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PlaceCollector:
    """장소 데이터 수집기"""

    def __init__(
        self,
        db: Session,
        max_naver_api_calls: int = 20000,
        region_filter: Optional[str] = None,
    ):
        self.db = db
        self.kakao_service = KakaoLocalService()
        self.place_service = PlaceService()
        self.collected_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.naver_api_call_count = 0
        self.max_naver_api_calls = max_naver_api_calls
        self.region_filter = region_filter
        self.api_limit_reached = False

    def place_exists(self, title: str, address: str) -> bool:
        """장소가 이미 DB에 존재하는지 확인"""
        existing = (
            self.db.query(Place)
            .filter(Place.title == title, Place.address == address)
            .first()
        )
        return existing is not None

    async def collect_and_process(
        self, categories: List[str], process_reviews: bool = True
    ):
        """
        전국 장소를 수집하고 처리합니다.

        Args:
            categories: 수집할 카테고리 리스트 (예: ['food', 'tourism'])
            process_reviews: 리뷰 자동 처리 여부
        """
        # 지역 필터링
        if self.region_filter:
            regions = REGIONS_BY_AREA.get(self.region_filter, [])
            region_name = self.region_filter
        else:
            regions = ALL_REGIONS
            region_name = "전국"

        logger.info("=" * 80)
        logger.info("장소 데이터 수집 시작")
        logger.info(f"대상 지역: {region_name} ({len(regions)}개 시/군/구)")
        logger.info(f"대상 카테고리: {categories}")
        logger.info(f"리뷰 처리: {'ON' if process_reviews else 'OFF'}")
        if process_reviews:
            logger.info(f"네이버 API 제한: {self.max_naver_api_calls}건")
        logger.info("=" * 80)

        for district in regions:
            # API 제한 도달 시 중단
            if self.api_limit_reached:
                logger.warning("\n네이버 API 호출 제한에 도달하여 수집을 중단합니다.")
                break

            logger.info(
                f"\n[{district.get('region', '')} {district['name']}] 데이터 수집 시작..."
            )
            await self._collect_for_district(
                district=district,
                categories=categories,
                process_reviews=process_reviews,
            )

        # 최종 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("데이터 수집 완료!")
        logger.info(f"- 새로 수집: {self.collected_count}개")
        logger.info(f"- 중복 건너뜀: {self.skipped_count}개")
        logger.info(f"- 오류: {self.error_count}개")
        if process_reviews:
            logger.info(f"- 네이버 API 호출 수: {self.naver_api_call_count}건")
        logger.info("=" * 80)

    async def _collect_for_district(
        self, district: dict, categories: List[str], process_reviews: bool
    ):
        for category in categories:
            await self._collect_for_category(
                district=district,
                category=category,
                process_reviews=process_reviews,
            )

    async def _collect_for_category(
        self, district: dict, category: str, process_reviews: bool
    ):
        category_code = CATEGORY_CODES.get(category)
        if not category_code:
            logger.warning(f"알 수 없는 카테고리: {category}")
            return

        logger.info(f"  - 카테고리: {category} ({category_code}) 검색 중...")

        # 그리드 검색: 한 지역을 4개 영역으로 나눠서 검색 (더 많은 장소 수집)
        # 중심점 기준으로 동/서/남/북 0.05도씩 이동 (약 5km)
        grid_offsets = [
            (0, 0),         # 중심
            (0.05, 0),      # 동쪽
            (-0.05, 0),     # 서쪽
            (0, 0.05),      # 북쪽
            (0, -0.05),     # 남쪽
            (0.05, 0.05),   # 북동
            (0.05, -0.05),  # 남동
            (-0.05, 0.05),  # 북서
            (-0.05, -0.05), # 남서
        ]

        all_places = {}  # kakao_place_id를 key로 중복 제거

        for offset_x, offset_y in grid_offsets:
            kakao_places = self.kakao_service.search_places_by_category(
                category_code=category_code,
                x=district["longitude"] + offset_x,
                y=district["latitude"] + offset_y,
                radius=20000,  # 최대 반경 20km
                max_pages=15,  # 더 많은 페이지 검색 (15페이지 = 225개)
            )

            # 중복 제거하며 수집
            for place in kakao_places:
                place_id = place.get("id")
                if place_id and place_id not in all_places:
                    all_places[place_id] = place

        logger.info(f"    검색 결과: {len(all_places)}개 (중복 제거됨)")

        for kakao_place in all_places.values():
            await self._handle_place(kakao_place, process_reviews)

    async def _handle_place(self, kakao_place: dict, process_reviews: bool):
        # API 제한 도달 확인
        if process_reviews and self.naver_api_call_count >= self.max_naver_api_calls:
            self.api_limit_reached = True
            return

        place_data = self.kakao_service.convert_to_place_data(kakao_place)

        if self.place_exists(place_data["title"], place_data["address"]):
            self.skipped_count += 1
            return

        try:
            new_place = self._create_place(place_data)
        except Exception as e:
            self.error_count += 1
            self.db.rollback()
            logger.error(f"    ✗ 저장 실패: {e}")
            return

        self.collected_count += 1
        logger.info(f"    ✓ 저장: {place_data['title']} ({place_data['address']})")

        if process_reviews:
            await self._process_reviews(new_place)

    def _create_place(self, place_data: dict) -> Place:
        new_place = Place(
            title=place_data["title"],
            address=place_data["address"],
            categories=place_data["categories"],
            longitude=place_data["longitude"],
            latitude=place_data["latitude"],
        )

        self.db.add(new_place)
        self.db.commit()
        self.db.refresh(new_place)
        return new_place

    async def _process_reviews(self, place: Place):
        logger.info("    → 리뷰 처리 시작...")
        try:
            await self.place_service.process_place_reviews(self.db, place)
            self.db.commit()

            # 네이버 API 호출 수 추적
            # - search_place_image: 1회
            # - search_review_urls: 1회 (실제로는 재시도 가능)
            # 안전하게 장소당 5회로 추정
            self.naver_api_call_count += 5

            logger.info(
                f"    ✓ 리뷰 처리 완료 (API 호출 누적: {self.naver_api_call_count}건)"
            )
        except Exception as e:
            self.error_count += 1
            self.db.rollback()
            logger.error(f"    ✗ 리뷰 처리 실패: {e}")


async def main():
    """메인 실행 함수"""
    db = SessionLocal()

    try:
        # 전국 장소 수집 (모든 주요 카테고리)
        # 리뷰는 포함하지 않음 (1단계: 장소만 수집)
        collector = PlaceCollector(db)

        # 더 많은 카테고리를 포함하여 수집
        await collector.collect_and_process(
            categories=["tourism", "food", "cafe", "accommodation", "culture"],
            process_reviews=False,
        )

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
