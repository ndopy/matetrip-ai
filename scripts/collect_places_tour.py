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
from typing import List, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.place import Place
from app.service.tour_api_service import TourAPIService
from app.service.place_service import PlaceService
from app.service.naver_search_service import NaverSearchService

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
        min_quality_score: int = 50,
        min_popularity_score: int = 30,
        enable_quality_filter: bool = True,
        enable_popularity_filter: bool = True,
        food_min_popularity_score: Optional[int] = None,
    ):
        self.db = db
        self.tour_service = TourAPIService()
        self.naver_service = NaverSearchService()
        self.place_service = PlaceService()
        self.collected_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.quality_filtered_count = 0
        self.popularity_filtered_count = 0
        self.naver_api_call_count = 0
        self.max_naver_api_calls = max_naver_api_calls
        self.region_filter = region_filter
        self.process_reviews = process_reviews
        self.api_limit_reached = False

        # 품질 필터링 설정
        self.min_quality_score = min_quality_score
        self.min_popularity_score = min_popularity_score
        self.enable_quality_filter = enable_quality_filter
        self.enable_popularity_filter = enable_popularity_filter

        # 카테고리별 인기도 기준
        self.food_min_popularity_score = (
            food_min_popularity_score
            if food_min_popularity_score is not None
            else min_popularity_score
        )

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
        logger.info("")
        logger.info("품질 필터링 설정:")
        logger.info(f"  - 품질 필터링: {'ON' if self.enable_quality_filter else 'OFF'}")
        if self.enable_quality_filter:
            logger.info(f"  - 최소 품질 점수: {self.min_quality_score}점")
        logger.info(
            f"  - 인기도 필터링: {'ON' if self.enable_popularity_filter else 'OFF'}"
        )
        if self.enable_popularity_filter:
            logger.info(f"  - 일반 카테고리 최소 리뷰: {self.min_popularity_score}개")
            logger.info(
                f"  - 음식점 카테고리 최소 리뷰: {self.food_min_popularity_score}개"
            )
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
        total_processed = (
            self.collected_count
            + self.skipped_count
            + self.quality_filtered_count
            + self.popularity_filtered_count
            + self.error_count
        )

        logger.info("\n" + "=" * 80)
        logger.info("데이터 수집 완료!")
        logger.info(f"- 총 처리: {total_processed}개")
        logger.info(f"- ✓ 새로 수집: {self.collected_count}개")
        logger.info(f"- ⊘ 중복 건너뜀: {self.skipped_count}개")
        if self.enable_quality_filter:
            logger.info(f"- ✗ 품질 필터링: {self.quality_filtered_count}개")
        if self.enable_popularity_filter:
            logger.info(f"- ✗ 인기도 필터링: {self.popularity_filtered_count}개")
        logger.info(f"- ✗ 오류: {self.error_count}개")

        if total_processed > 0:
            acceptance_rate = (self.collected_count / total_processed) * 100
            logger.info(f"\n수집률: {acceptance_rate:.1f}%")

        if self.process_reviews:
            logger.info(f"\n네이버 API 호출 수: {self.naver_api_call_count}건")
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
            await self._handle_place(tour_item, category)

    async def _handle_place(self, tour_item: dict, category: str):
        """개별 장소 처리 (품질 검증 포함)"""
        # API 제한 도달 확인
        if (
            self.process_reviews
            and self.naver_api_call_count >= self.max_naver_api_calls
        ):
            self.api_limit_reached = True
            return

        # 1단계: 기본 품질 체크 (Tour API 데이터 기반)
        if self.enable_quality_filter:
            is_quality, reason = self.tour_service.is_quality_place(tour_item)
            if not is_quality:
                logger.debug(
                    f"    ✗ 품질 필터링: {tour_item.get('title', 'Unknown')} - {reason}"
                )
                self.quality_filtered_count += 1
                return

        # Tour API 데이터를 Place 형식으로 변환
        place_data = self.tour_service.convert_to_place_data(tour_item)

        # 중복 확인 (title + address 기준)
        if self.place_exists(place_data["title"], place_data["address"]):
            self.skipped_count += 1
            return

        # 2단계: 인기도 검증 (네이버 API 기반) - 선택적
        # 카테고리별 최소 인기도 기준 적용
        required_popularity = (
            self.food_min_popularity_score
            if category == "food"
            else self.min_popularity_score
        )

        if self.enable_popularity_filter:
            popularity_score = self.naver_service.get_place_popularity_score(
                place_data["title"], place_data["address"]
            )

            if popularity_score < required_popularity:
                logger.debug(
                    f"    ✗ 인기도 필터링: {place_data['title']} "
                    f"(리뷰 {popularity_score}개 < 최소 {required_popularity}개, 카테고리: {category})"
                )
                self.popularity_filtered_count += 1
                return

            logger.debug(
                f"    ✓ 인기도 통과: {place_data['title']} (리뷰 {popularity_score}개, 카테고리: {category})"
            )

        # 3단계: 품질 점수 계산 (선택적, 로깅용)
        quality_score = self.tour_service.calculate_quality_score(tour_item)
        if self.enable_quality_filter and quality_score < self.min_quality_score:
            logger.debug(
                f"    ✗ 품질 점수 필터링: {place_data['title']} "
                f"(점수 {quality_score} < 최소 {self.min_quality_score})"
            )
            self.quality_filtered_count += 1
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
            f"    ✓ 저장: {place_data['title']} " f"(품질점수: {quality_score}점)"
        )

        # 리뷰 처리 (선택)
        if self.process_reviews:
            await self._process_reviews(new_place)

    def _create_place(self, place_data: dict) -> Place:
        """Place 객체 생성 및 DB 저장"""
        new_place = Place(
            title=place_data["title"],
            address=place_data["address"],
            categories=place_data["categories"],
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
        # 품질 필터링을 통해 진짜 유명한 장소만 수집
        collector = TourPlaceCollector(
            db=db,
            process_reviews=False,  # 리뷰는 나중에 별도 스크립트로 처리
            enable_quality_filter=True,  # 품질 필터링 활성화
            min_quality_score=70,  # 최소 품질 점수 70점 (상향)
            enable_popularity_filter=True,  # 인기도 필터링 활성화
            min_popularity_score=250,  # 최소 리뷰 150개 (초유명 관광명소만)
            food_min_popularity_score=1000,  # 음식점은 더 엄격하게 200개 (초유명 맛집만)
        )

        # 주요 카테고리 수집
        # tourism: 관광지, leisure: 레포츠, course: 여행코스
        # 제외: food(음식점), shopping(쇼핑), accommodation(숙박), culture(문화시설), festival(축제)
        await collector.collect_and_process(
            categories=[
                "tourism",  # 관광지 (핵심) - 유명 관광명소만
                "leisure",  # 레포츠 - 액티비티, 체험 관광
                "course",  # 여행코스 - 추천 관광 코스
            ]
        )

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
