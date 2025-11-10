#!/usr/bin/env python3
"""
리뷰 배치 처리 스크립트

DB에 저장된 장소들에 대해 리뷰를 배치로 처리합니다.
네이버 API 하루 25,000건 제한을 고려하여 안전하게 20,000건으로 제한합니다.

사용법:
    # 배치 0 (전체의 0/7~1/7)
    python scripts/process_reviews_batch.py --batch 0 --total-batches 7

    # 배치 1 (전체의 1/7~2/7)
    python scripts/process_reviews_batch.py --batch 1 --total-batches 7

    # 특정 지역만 처리
    python scripts/process_reviews_batch.py --batch 0 --total-batches 7 --region 서울
"""

import sys
import os
import asyncio
import argparse
import logging
from typing import List

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


class ReviewBatchProcessor:
    """리뷰 배치 처리기"""

    def __init__(
        self,
        db: Session,
        batch_index: int,
        total_batches: int,
        max_naver_api_calls: int = 20000,
        region: str = None,
    ):
        self.db = db
        self.batch_index = batch_index
        self.total_batches = total_batches
        self.max_naver_api_calls = max_naver_api_calls
        self.region = region
        self.place_service = PlaceService()
        self.naver_api_call_count = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def get_places_without_reviews(self) -> List[Place]:
        """리뷰가 없는 장소 가져오기"""
        from app.models.review import PlaceReview

        query = (
            self.db.query(Place)
            .outerjoin(PlaceReview, Place.id == PlaceReview.place_id)
            .filter(PlaceReview.id == None)
        )

        # 지역 필터링
        if self.region:
            query = query.filter(Place.address.like(f"{self.region}%"))

        all_places = query.all()

        # 배치 분할
        total_count = len(all_places)
        batch_size = (total_count + self.total_batches - 1) // self.total_batches
        start_idx = self.batch_index * batch_size
        end_idx = min(start_idx + batch_size, total_count)

        batch_places = all_places[start_idx:end_idx]

        logger.info(f"전체 리뷰 없는 장소: {total_count}개")
        logger.info(
            f"배치 {self.batch_index}/{self.total_batches}: {len(batch_places)}개 처리 예정"
        )
        logger.info(f"인덱스 범위: {start_idx}~{end_idx}")

        return batch_places

    async def process_batch(self):
        """배치 처리 실행"""
        places = self.get_places_without_reviews()

        if not places:
            logger.info("처리할 장소가 없습니다.")
            return

        logger.info("=" * 80)
        logger.info(f"리뷰 배치 처리 시작 (배치 {self.batch_index})")
        logger.info(f"처리 대상: {len(places)}개 장소")
        logger.info(f"네이버 API 제한: {self.max_naver_api_calls}건")
        logger.info("=" * 80)

        for idx, place in enumerate(places, 1):
            # API 제한 체크
            if self.naver_api_call_count >= self.max_naver_api_calls:
                logger.warning(
                    f"\n네이버 API 호출 제한({self.max_naver_api_calls}건)에 도달하여 중단합니다."
                )
                break

            logger.info(
                f"\n[{idx}/{len(places)}] {place.title} ({place.address}) 처리 중..."
            )

            try:
                await self.place_service.process_place_reviews(self.db, place)
                self.db.commit()

                # 네이버 API 호출 수 추적 (장소당 평균 5회)
                self.naver_api_call_count += 5
                self.processed_count += 1

                logger.info(
                    f"  ✓ 리뷰 처리 완료 (API 호출 누적: {self.naver_api_call_count}건)"
                )

            except Exception as e:
                self.error_count += 1
                self.db.rollback()
                logger.error(f"  ✗ 리뷰 처리 실패: {e}")

        # 최종 결과
        logger.info("\n" + "=" * 80)
        logger.info(f"배치 {self.batch_index} 처리 완료!")
        logger.info(f"- 처리 완료: {self.processed_count}개")
        logger.info(f"- 오류: {self.error_count}개")
        logger.info(f"- 네이버 API 호출 수: {self.naver_api_call_count}건")
        logger.info("=" * 80)


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="리뷰 배치 처리 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--batch",
        type=int,
        required=True,
        help="배치 인덱스 (0부터 시작)",
    )
    parser.add_argument(
        "--total-batches",
        type=int,
        default=7,
        help="전체 배치 수 (기본값: 7)",
    )
    parser.add_argument(
        "--max-naver-calls",
        type=int,
        default=20000,
        help="네이버 API 최대 호출 수 (기본값: 20000)",
    )
    parser.add_argument(
        "--region",
        type=str,
        help="특정 지역만 처리 (예: 서울, 부산)",
    )

    args = parser.parse_args()

    # 배치 인덱스 검증
    if args.batch < 0 or args.batch >= args.total_batches:
        logger.error(
            f"배치 인덱스는 0~{args.total_batches-1} 범위여야 합니다."
        )
        return

    db = SessionLocal()

    try:
        processor = ReviewBatchProcessor(
            db=db,
            batch_index=args.batch,
            total_batches=args.total_batches,
            max_naver_api_calls=args.max_naver_calls,
            region=args.region,
        )

        await processor.process_batch()

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
