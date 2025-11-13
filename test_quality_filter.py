"""
품질 필터링 테스트 스크립트

Tour API에서 가져온 데이터의 품질을 검증하고,
필터링이 제대로 동작하는지 확인합니다.
"""

import sys
import os
import asyncio
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.service.tour_api_service import TourAPIService
from app.service.naver_search_service import NaverSearchService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_quality_filter():
    """품질 필터 테스트"""
    tour_service = TourAPIService()

    logger.info("=" * 80)
    logger.info("서울 관광지 품질 필터링 테스트")
    logger.info("=" * 80)

    # 서울(areaCode=1) 관광지(contentTypeId=12) 1페이지만 테스트
    items = tour_service.search_area_based_list(
        area_code="1",  # 서울
        content_type_id="12",  # 관광지
        page=1,
        num_of_rows=20,  # 20개만 테스트
    )

    logger.info(f"\n총 {len(items)}개 장소 검색됨\n")

    passed_count = 0
    filtered_count = 0
    quality_scores = []

    for idx, item in enumerate(items, 1):
        title = item.get("title", "Unknown")
        is_quality, reason = tour_service.is_quality_place(item)
        quality_score = tour_service.calculate_quality_score(item)
        quality_scores.append(quality_score)

        if is_quality:
            passed_count += 1
            logger.info(f"[{idx}] ✓ {title}")
            logger.info(f"    품질점수: {quality_score}점")
            logger.info(f"    주소: {item.get('addr1', 'N/A')}")
            logger.info(f"    이미지: {'O' if item.get('firstimage') else 'X'}")
            logger.info(f"    전화: {item.get('tel', 'N/A')}")
        else:
            filtered_count += 1
            logger.info(f"[{idx}] ✗ {title}")
            logger.info(f"    필터링 이유: {reason}")
            logger.info(f"    품질점수: {quality_score}점")

        logger.info("")

    # 통계 출력
    logger.info("=" * 80)
    logger.info("품질 필터링 결과")
    logger.info(f"- 총 검색: {len(items)}개")
    logger.info(f"- ✓ 통과: {passed_count}개 ({passed_count/len(items)*100:.1f}%)")
    logger.info(f"- ✗ 필터링: {filtered_count}개 ({filtered_count/len(items)*100:.1f}%)")

    if quality_scores:
        avg_score = sum(quality_scores) / len(quality_scores)
        logger.info(f"\n평균 품질 점수: {avg_score:.1f}점")
        logger.info(f"최고 점수: {max(quality_scores)}점")
        logger.info(f"최저 점수: {min(quality_scores)}점")

    logger.info("=" * 80)


async def test_popularity_filter():
    """인기도 필터 테스트"""
    tour_service = TourAPIService()
    naver_service = NaverSearchService()

    logger.info("\n" + "=" * 80)
    logger.info("서울 주요 관광지 인기도 테스트")
    logger.info("=" * 80)

    # 서울 관광지 몇 개만 테스트
    items = tour_service.search_area_based_list(
        area_code="1",
        content_type_id="12",
        page=1,
        num_of_rows=5,  # 5개만 테스트 (네이버 API 호출 제한)
    )

    for idx, item in enumerate(items, 1):
        title = item.get("title", "Unknown")
        addr1 = item.get("addr1", "")

        # 품질 체크
        is_quality, reason = tour_service.is_quality_place(item)
        if not is_quality:
            logger.info(f"[{idx}] ✗ {title} - 품질 필터링: {reason}")
            continue

        # 인기도 체크
        popularity = naver_service.get_place_popularity_score(title, addr1)

        logger.info(f"[{idx}] {title}")
        logger.info(f"    인기도: {popularity}개 리뷰")
        logger.info(f"    상태: {'✓ 통과' if popularity >= 30 else '✗ 필터링'}")
        logger.info("")

    logger.info("=" * 80)


async def main():
    """메인 함수"""
    # 1. 품질 필터 테스트
    test_quality_filter()

    # 2. 인기도 필터 테스트
    await test_popularity_filter()


if __name__ == "__main__":
    asyncio.run(main())
