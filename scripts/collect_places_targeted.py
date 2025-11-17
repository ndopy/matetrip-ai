# collect_places_targeted.py

"""
지역별, 카테고리별 타겟팅된 장소 데이터 수집 스크립트

목표: 총 2,500개의 인기 장소 수집
- 제주도: 700개 (자연 400, 인문 150, 레포츠 100, 추천코스 50)
- 부산: 600개 (자연 200, 숙박 150, 레포츠 200, 인문 50)
- 서울: 500개 (레포츠 250, 자연 150, 숙박 100)
- 경상도: 400개 (숙박 150, 레포츠 150, 자연 100)
- 인천: 300개 (레포츠 150, 숙박 100, 자연 50)

실행 방법:
    uv run python scripts/collect_places_targeted.py
"""

import sys
import os
import asyncio
import logging
import re
from typing import List, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.place import Place
from app.service.crawling.tour_api_service import TourAPIService
from app.service.place_service import PlaceService
from app.service.crawling.naver_search_service import NaverSearchService
from app.enums import RegionGroupType

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TargetedPlaceCollector:
    """타겟팅된 장소 데이터 수집기"""

    def __init__(
        self,
        db: Session,
        region_filter: str,
        min_quality_score: int = 60,
    ):
        self.db = db
        self.tour_service = TourAPIService()
        self.naver_service = NaverSearchService()
        self.place_service = PlaceService(db)
        self.collected_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.region_filter = region_filter
        self.min_quality_score = min_quality_score

    @staticmethod
    def get_region_from_address(address: str) -> Optional[str]:
        """주소에서 region_group을 추출합니다."""
        sido_raw = address.split()[0] if address else ""
        # "서울시" -> "서울", "경기도" -> "경기" 등으로 정규화
        sido_normalized = re.sub(
            r"(특별시|광역시|특별자치시|특별자치도|도|시)$", "", sido_raw
        )

        region_mapping = {
            "서울": RegionGroupType.SEOUL.value,
            "경기": RegionGroupType.GYEONGGI.value,
            "인천": RegionGroupType.INCHEON.value,
            "강원": RegionGroupType.GANGWON.value,
            "부산": RegionGroupType.BUSAN.value,
            "경남": RegionGroupType.GYEONGSANG.value,
            "경북": RegionGroupType.GYEONGSANG.value,
            "대구": RegionGroupType.GYEONGSANG.value,
            "울산": RegionGroupType.GYEONGSANG.value,
            "전남": RegionGroupType.JEOLLA.value,
            "전북": RegionGroupType.JEOLLA.value,
            "세종": RegionGroupType.CHUNGCHEONG.value,
            "충남": RegionGroupType.CHUNGCHEONG.value,
            "충북": RegionGroupType.CHUNGCHEONG.value,
            "대전": RegionGroupType.CHUNGCHEONG.value,
            "제주": RegionGroupType.JEJU.value,
        }

        return region_mapping.get(sido_normalized)

    def place_exists(self, title: str, address: str) -> bool:
        """장소가 이미 DB에 존재하는지 확인 (title + address 기준)"""
        existing = (
            self.db.query(Place)
            .filter(Place.title == title, Place.address == address)
            .first()
        )
        return existing is not None

    async def collect_category(self, category: str, max_items: int) -> int:
        """특정 카테고리의 데이터 수집"""
        area_code = TourAPIService.AREA_CODES.get(self.region_filter)
        content_type_id = TourAPIService.CONTENT_TYPES.get(category)

        if not area_code or not content_type_id:
            logger.warning(
                f"알 수 없는 지역 또는 카테고리: {self.region_filter}, {category}"
            )
            return 0

        logger.info(
            f"\n[{self.region_filter}] {category} 카테고리 수집 시작 (목표: {max_items}개)"
        )

        # Tour API에서 인기순으로 수집
        tour_items = self.tour_service.search_all_pages(
            area_code=area_code,
            content_type_id=content_type_id,
            max_pages=100,
            # arrange="B",  # 조회수순 (인기도순)
            # max_items=max_items * 3,  # 중복/필터링을 고려하여 3배 가져오기
            # min_quality_score=self.min_quality_score,
        )

        logger.info(
            f"  검색 결과: {len(tour_items)}개 (품질 점수 {self.min_quality_score}점 이상)"
        )

        collected_in_category = 0
        for tour_item in tour_items:
            if collected_in_category >= max_items:
                break

            if await self._handle_place(tour_item):
                collected_in_category += 1

        logger.info(f"  ✓ {category} 수집 완료: {collected_in_category}개")
        return collected_in_category

    async def _handle_place(self, tour_item: dict) -> bool:
        """개별 장소 처리 (성공 시 True 반환)"""
        # Tour API 데이터를 Place 형식으로 변환
        place_data = self.tour_service.convert_to_place_data(tour_item)

        # 필수 필드 검증
        if not place_data["title"] or not place_data["address"]:
            return False

        # 숙박시설 필터링 (저품질 숙소 제외)
        excluded_accommodation_keywords = [
            "모텔",
            "호스텔",
            "수련원",
            "게스트하우스",
            "민박",
            "여관",
            "여인숙",
        ]
        title_lower = place_data["title"].lower()
        for keyword in excluded_accommodation_keywords:
            if keyword in title_lower:
                self.skipped_count += 1
                return False

        # 좌표 검증
        if place_data["longitude"] == 0.0 or place_data["latitude"] == 0.0:
            return False

        # 중복 확인
        if self.place_exists(place_data["title"], place_data["address"]):
            self.skipped_count += 1
            return False

        try:
            self._create_place(place_data)
            self.collected_count += 1
            logger.info(f"    ✓ 저장: {place_data['title']}")
            return True
        except Exception as e:
            self.error_count += 1
            self.db.rollback()
            logger.error(f"    ✗ 저장 실패: {e}")
            return False

    def _create_place(self, place_data: dict) -> Place:
        """Place 객체 생성 및 DB 저장"""
        category_value = None
        if place_data.get("categories") and len(place_data["categories"]) > 0:
            category_value = place_data["categories"][0]

        region_value = self.get_region_from_address(place_data["address"])

        new_place = Place(
            title=place_data["title"],
            address=place_data["address"],
            category=category_value,
            region=region_value,
            longitude=place_data["longitude"],
            latitude=place_data["latitude"],
            image_url=place_data.get("image_url"),
        )

        self.db.add(new_place)
        self.db.commit()
        self.db.refresh(new_place)
        return new_place


async def collect_region(db: Session, region: str, collection_plan: dict):
    """특정 지역의 데이터 수집"""
    logger.info("\n" + "=" * 80)
    logger.info(f"{region} 데이터 수집 시작 (총 {collection_plan['total']}개 목표)")
    logger.info("=" * 80)

    collector = TargetedPlaceCollector(
        db=db,
        region_filter=region,
        min_quality_score=60,
    )

    total_collected = 0
    for category, max_items in collection_plan["categories"].items():
        collected = await collector.collect_category(category, max_items)
        total_collected += collected

    logger.info("\n" + "-" * 80)
    logger.info(f"{region} 수집 완료:")
    logger.info(f"  - 목표: {collection_plan['total']}개")
    logger.info(f"  - 수집: {total_collected}개")
    logger.info(f"  - 중복 건너뜀: {collector.skipped_count}개")
    logger.info(f"  - 오류: {collector.error_count}개")
    logger.info("-" * 80)

    return total_collected


async def main():
    """메인 실행 함수"""
    db = SessionLocal()

    try:
        # 수집 계획 정의
        collection_plans = {
            "제주": {
                "total": 700,
                "categories": {
                    "tourism": 400,  # 자연 (관광지)
                    "culture": 150,  # 인문(문화시설)
                    "leisure": 100,  # 레포츠
                    "course": 50,  # 추천코스
                },
            },
            "부산": {
                "total": 600,
                "categories": {
                    "tourism": 200,  # 자연
                    "accommodation": 150,  # 숙박
                    "leisure": 200,  # 레포츠
                    "culture": 50,  # 인문
                },
            },
            "서울": {
                "total": 500,
                "categories": {
                    "leisure": 250,  # 레포츠
                    "tourism": 150,  # 자연
                    "accommodation": 100,  # 숙박
                },
            },
            "경남": {  # 경상도 (경남)
                "total": 200,
                "categories": {
                    "accommodation": 75,  # 숙박
                    "leisure": 75,  # 레포츠
                    "tourism": 50,  # 자연
                },
            },
            "경북": {  # 경상도 (경북)
                "total": 200,
                "categories": {
                    "accommodation": 75,  # 숙박
                    "leisure": 75,  # 레포츠
                    "tourism": 50,  # 자연
                },
            },
            "인천": {
                "total": 300,
                "categories": {
                    "leisure": 150,  # 레포츠
                    "accommodation": 100,  # 숙박
                    "tourism": 50,  # 자연
                },
            },
        }

        # 전체 수집 시작
        logger.info("\n" + "=" * 80)
        logger.info("타겟팅된 장소 데이터 수집 시작")
        logger.info("총 목표: 2,500개 (인기순)")
        logger.info("=" * 80)

        grand_total = 0

        # 각 지역별로 순차 수집
        for region, plan in collection_plans.items():
            total = await collect_region(db, region, plan)
            grand_total += total

        # 최종 결과
        logger.info("\n" + "=" * 80)
        logger.info("전체 수집 완료!")
        logger.info(f"총 수집: {grand_total}개")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
