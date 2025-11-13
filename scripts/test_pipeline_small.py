"""
전체 파이프라인 테스트 (3~5개 장소만)

하이브리드 방식:
- review.embedding: 각 리뷰 임베딩 저장
- place.embedding: 리뷰 임베딩들의 평균 (검색 정확도 - 긍정/부정 비율 보존)
- place.summary: LLM 요약 (사용자 표시용)

실행 방법:
    uv run python scripts/test_pipeline_small.py
"""

import sys
import os
import asyncio
import logging
import time
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.place import Place
from app.service.place_service import PlaceService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_pipeline():
    """3~5개 장소에 대해 전체 파이프라인 테스트"""
    db = SessionLocal()
    place_service = PlaceService()

    try:
        # 테스트할 장소 개수
        test_count = 3

        # 태그/요약이 없는 장소 조회
        places = (
            db.query(Place)
            .filter((Place.tags == None) | (Place.summary == None))
            .limit(test_count)
            .all()
        )

        if not places:
            logger.info("=" * 80)
            logger.info("테스트할 장소가 없습니다.")
            logger.info("먼저 장소 데이터를 수집해주세요:")
            logger.info("  uv run python crawler/tour_api_crawler.py --limit 5")
            logger.info("=" * 80)
            return

        total = len(places)
        logger.info("=" * 80)
        logger.info(f"하이브리드 파이프라인 테스트 시작")
        logger.info("=" * 80)
        logger.info(f"테스트할 장소: {total}개")
        logger.info("")
        logger.info("파이프라인:")
        logger.info("  1. 네이버 블로그 검색 → 리뷰 URL 수집")
        logger.info("  2. Crawl4AI → 리뷰 크롤링")
        logger.info("  3. 키워드 필터링")
        logger.info("  4. 리뷰 저장 (content)")
        logger.info("  5. 리뷰 임베딩 생성 (각 리뷰) ← 긍정/부정 비율 보존")
        logger.info("  6. Claude → 태그 & 요약 생성 (사용자 표시용)")
        logger.info("  7. Place 임베딩 = 리뷰 임베딩 평균 (검색 정확도)")
        logger.info("=" * 80)
        logger.info("")

        start_time = time.time()
        success_count = 0
        fail_count = 0

        for idx, place in enumerate(places, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"[{idx}/{total}] {place.title}")
            logger.info(f"{'='*80}")
            logger.info(f"주소: {place.address}")
            logger.info(f"카테고리: {place.categories}")

            place_start = time.time()

            try:
                # 전체 파이프라인 실행
                await place_service.process_place_reviews(db, place)

                db.commit()

                # 결과 확인
                db.refresh(place)

                place_end = time.time()
                elapsed = place_end - place_start

                logger.info(f"\n{'='*80}")
                logger.info(f"✅ [{idx}/{total}] {place.title} 처리 완료!")
                logger.info(f"{'='*80}")
                logger.info(f"소요 시간: {elapsed:.2f}초")
                logger.info(f"\n생성 결과:")
                logger.info(f"  - 태그: {place.tags}")
                logger.info(f"  - 요약: {place.summary[:100] if place.summary else '(없음)'}...")
                logger.info(
                    f"  - Place 임베딩: {'생성됨' if place.embedding is not None else '없음'}"
                )

                # 리뷰 개수 확인
                from app.models.review import PlaceReview

                review_count = (
                    db.query(PlaceReview)
                    .filter(
                        PlaceReview.place_id == place.id,
                        PlaceReview.is_deleted == False,
                    )
                    .count()
                )
                review_with_embedding = (
                    db.query(PlaceReview)
                    .filter(
                        PlaceReview.place_id == place.id,
                        PlaceReview.is_deleted == False,
                        PlaceReview.embedding.isnot(None),
                    )
                    .count()
                )
                logger.info(f"  - 리뷰 개수: {review_count}개")
                logger.info(
                    f"  - 리뷰 임베딩: {review_with_embedding}/{review_count}개 생성"
                )
                logger.info(f"{'='*80}\n")

                success_count += 1

            except Exception as e:
                logger.error(
                    f"\n❌ [{idx}/{total}] {place.title} 처리 실패: {e}", exc_info=True
                )
                db.rollback()
                fail_count += 1
                continue

        # 최종 결과
        total_elapsed = time.time() - start_time

        logger.info("\n" + "=" * 80)
        logger.info("테스트 완료!")
        logger.info("=" * 80)
        logger.info(f"성공: {success_count}개")
        logger.info(f"실패: {fail_count}개")
        logger.info(f"총 소요 시간: {total_elapsed:.2f}초 ({total_elapsed/60:.1f}분)")
        logger.info(f"평균 처리 시간: {total_elapsed/total:.2f}초/장소")
        logger.info("=" * 80)

        if success_count > 0:
            logger.info("\n🎉 하이브리드 파이프라인이 정상 작동합니다!")
            logger.info("\n장점:")
            logger.info("  ✓ 검색 정확도: 리뷰 임베딩 평균 (긍정/부정 비율 보존)")
            logger.info("  ✓ 사용자 경험: LLM 요약 (읽기 쉬운 요약)")

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    logger.info(f"\n🚀 하이브리드 파이프라인 테스트 시작")
    logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    asyncio.run(test_pipeline())

    logger.info(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
