# collect_places_tour.py

"""
Tour API를 사용하여 전국 유명 관광지 데이터를 수집하는 배치 스크립트

Tour API는 한국관광공사에서 제공하는 공식 관광정보로,
검증된 유명 관광지만 포함되어 있어 여행 추천에 적합합니다.

실행 방법:
    python scripts/collect_places_tour.py

또는 uv 사용:
    uv run python scripts/collect_places_tour.py
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
from app.service.tour_api_service import TourAPIService
from app.service.place_service import PlaceService
from app.service.naver_search_service import NaverSearchService
from app.enums import RegionGroupType

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TourPlaceCollector:
    """Tour API 기반 장소 데이터 수집기"""

    def __init__(
        self,
        db: Session,
        max_naver_api_calls: int = 20000,
        region_filter: Optional[str] = None,
        process_reviews: bool = False,
    ):
        self.db = db
        self.tour_service = TourAPIService()
        self.naver_service = NaverSearchService()
        self.place_service = PlaceService()
        self.collected_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.naver_api_call_count = 0
        self.max_naver_api_calls = max_naver_api_calls
        self.region_filter = region_filter
        self.process_reviews = process_reviews
        self.api_limit_reached = False

    @staticmethod
    def get_region_from_address(address: str) -> Optional[str]:
        """
        주소에서 region_group을 추출합니다.

        예시:
            - "서울특별시 강남구 ..." -> "서울"
            - "경기도 성남시 ..." -> "경기도"
            - "부산광역시 해운대구 ..." -> "부산"
        """
        # 주소의 첫 번째 부분 추출 (공백 기준)
        sido_raw = address.split()[0] if address else ""

        # 특별시/광역시/도 등 제거하여 정규화
        sido_normalized = re.sub(
            r"(특별시|광역시|특별자치시|특별자치도|도)$", "", sido_raw
        )

        # region_group 매핑 (RegionGroupType 사용)
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
            "세종": RegionGroupType.JEOLLA.value,
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

    async def collect_and_process(self, categories: List[str]):
        """
        전국 관광지를 Tour API로 수집합니다.

        Args:
            categories: 수집할 카테고리 리스트 (예: ['tourism', 'culture', 'food'])
        """
        # 지역 필터링
        if self.region_filter:
            regions = [self.region_filter]
            region_name = self.region_filter
        else:
            regions = list(TourAPIService.AREA_CODES.keys())
            region_name = "전국"

        logger.info("=" * 80)
        logger.info("Tour API 기반 장소 데이터 수집 시작")
        logger.info(f"대상 지역: {region_name} ({len(regions)}개 지역)")
        logger.info(f"대상 카테고리: {categories}")
        logger.info(f"리뷰 처리: {'ON' if self.process_reviews else 'OFF'}")
        if self.process_reviews:
            logger.info(f"네이버 API 제한: {self.max_naver_api_calls}건")
        logger.info("=" * 80)

        for region in regions:
            # API 제한 도달 시 중단
            if self.api_limit_reached:
                logger.warning("\n네이버 API 호출 제한에 도달하여 수집을 중단합니다.")
                break

            logger.info(f"\n[{region}] 데이터 수집 시작...")
            await self._collect_for_region(region=region, categories=categories)

        # 최종 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("데이터 수집 완료!")
        logger.info(f"- 새로 수집: {self.collected_count}개")
        logger.info(f"- 중복 건너뜀: {self.skipped_count}개")
        logger.info(f"- 오류: {self.error_count}개")
        if self.process_reviews:
            logger.info(f"- 네이버 API 호출 수: {self.naver_api_call_count}건")
        logger.info("=" * 80)

    async def _collect_for_region(self, region: str, categories: List[str]):
        """특정 지역의 데이터 수집"""
        area_code = TourAPIService.AREA_CODES.get(region)

        if not area_code:
            logger.warning(f"알 수 없는 지역: {region}")
            return

        for category in categories:
            await self._collect_for_category(
                region=region, area_code=area_code, category=category
            )

    async def _collect_for_category(self, region: str, area_code: str, category: str):
        """특정 카테고리의 데이터 수집"""
        content_type_id = TourAPIService.CONTENT_TYPES.get(category)

        if not content_type_id:
            logger.warning(f"알 수 없는 카테고리: {category}")
            return

        logger.info(
            f"  - 카테고리: {category} (contentTypeId={content_type_id}) 검색 중..."
        )

        # Tour API에서 전체 페이지 수집 (최대 10페이지 = 1000개)
        tour_items = self.tour_service.search_all_pages(
            area_code=area_code,
            content_type_id=content_type_id,
            max_pages=10,
        )

        logger.info(f"    검색 결과: {len(tour_items)}개")

        for tour_item in tour_items:
            await self._handle_place(tour_item)

    async def _handle_place(self, tour_item: dict):
        """개별 장소 처리"""
        # API 제한 도달 확인
        if (
            self.process_reviews
            and self.naver_api_call_count >= self.max_naver_api_calls
        ):
            self.api_limit_reached = True
            return

        # Tour API 데이터를 Place 형식으로 변환
        place_data = self.tour_service.convert_to_place_data(tour_item)

        # 필수 필드 검증
        if not place_data["title"] or not place_data["address"]:
            logger.warning(f"✗ 필수 정보 누락: {tour_item}")
            return

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
                logger.info(
                    f"    ✗ 숙박시설 필터링: {place_data['title']} (키워드: {keyword})"
                )
                self.skipped_count += 1
                return

        # 좌표 검증 (위도/경도가 0이면 스킵)
        if place_data["longitude"] == 0.0 or place_data["latitude"] == 0.0:
            logger.warning(f"    ✗ 좌표 정보 없음: {place_data['title']}")
            return

        # 중복 확인 (title + address 기준)
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

        # 리뷰 처리 (선택)
        if self.process_reviews:
            await self._process_reviews(new_place)

    def _create_place(self, place_data: dict) -> Place:
        """Place 객체 생성 및 DB 저장"""
        # categories 리스트에서 첫 번째 카테고리만 사용 (category는 단수 필드)
        category_value = None
        if place_data.get("categories") and len(place_data["categories"]) > 0:
            category_value = place_data["categories"][0]

        # 주소에서 region 자동 설정
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

    async def _process_reviews(self, place: Place):
        """리뷰 처리 (Naver API 사용)"""
        logger.info("    → 리뷰 처리 시작...")
        try:
            await self.place_service.process_place_reviews(self.db, place)
            self.db.commit()

            # 네이버 API 호출 수 추적
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
        # Tour API 기반 전국 관광지 수집
        # 리뷰는 별도로 처리 (1단계: 장소만 수집)
        collector = TourPlaceCollector(
            db=db,
            process_reviews=False,  # 리뷰는 나중에 별도 스크립트로 처리
        )

        # 주요 카테고리 수집
        # tourism: 관광지, culture: 문화시설, food: 음식점
        # leisure: 레포츠, shopping: 쇼핑
        await collector.collect_and_process(
            categories=[
                # "tourism",  # 관광지 (핵심)
                # "culture",  # 문화시설 (핵심)
                # # "food",       # 음식점
                # "leisure",  # 레포츠
                "accommodation",  # 숙박
                # "shopping",   # 쇼핑
            ]
        )

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
