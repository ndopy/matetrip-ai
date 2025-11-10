"""
카카오 Local API를 사용하여 서울 지역의 장소 데이터를 수집하는 배치 스크립트

실행 방법:
    python scripts/collect_places.py

또는 uv 사용:
    uv run python scripts/collect_places.py
"""

import sys
import os
import asyncio
import logging
from typing import List

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.place import Place
from app.service.kakao_local_service import KakaoLocalService
from app.service.place_service import PlaceService
from app.data.seoul_districts import SEOUL_DISTRICTS, CATEGORY_CODES

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PlaceCollector:
    """장소 데이터 수집기"""

    def __init__(self, db: Session):
        self.db = db
        self.kakao_service = KakaoLocalService()
        self.place_service = PlaceService()
        self.collected_count = 0
        self.skipped_count = 0
        self.error_count = 0

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
        서울 전역의 장소를 수집하고 처리합니다.

        Args:
            categories: 수집할 카테고리 리스트 (예: ['food', 'tourism'])
            process_reviews: 리뷰 자동 처리 여부
        """
        logger.info("=" * 80)
        logger.info("장소 데이터 수집 시작")
        logger.info(f"대상 카테고리: {categories}")
        logger.info(f"대상 지역: 서울 {len(SEOUL_DISTRICTS)}개 구")
        logger.info("=" * 80)

        for district in SEOUL_DISTRICTS:
            logger.info(f"\n[{district['name']}] 데이터 수집 시작...")
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

        kakao_places = self.kakao_service.search_places_by_category(
            category_code=category_code,
            x=district["longitude"],
            y=district["latitude"],
            radius=5000,
            max_pages=3,
        )

        logger.info(f"    검색 결과: {len(kakao_places)}개")

        for kakao_place in kakao_places:
            await self._handle_place(kakao_place, process_reviews)

    async def _handle_place(self, kakao_place: dict, process_reviews: bool):
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
        logger.info(
            f"    ✓ 저장: {place_data['title']} ({place_data['address']})"
        )

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
            logger.info("    ✓ 리뷰 처리 완료")
        except Exception as e:
            self.error_count += 1
            logger.error(f"    ✗ 리뷰 처리 실패: {e}")


async def main():
    """메인 실행 함수"""
    db = SessionLocal()

    try:
        collector = PlaceCollector(db)

        # 관광명소와 음식점 수집 (리뷰 자동 처리)
        await collector.collect_and_process(
            categories=["tourism", "food"], process_reviews=True
        )

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
