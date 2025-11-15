"""
장소 임베딩 배치 업데이트 스크립트

임베딩이 없거나 오래된 장소들을 대상으로 전체 재계산을 수행

사용법:
    # 임베딩이 없는 장소 1000개 처리
    python scripts/update_place_embeddings.py --limit 1000

    # 30일 이상 업데이트 안 된 장소 처리
    python scripts/update_place_embeddings.py --limit 5000 --days 30

    # 전체 재계산
    python scripts/update_place_embeddings.py --limit 100000 --days 0
"""

import argparse
import logging
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from app.database.database import SessionLocal
from app.models.review import PlaceReview
from app.service.place_embedding_service import PlaceEmbeddingService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="장소 임베딩 배치 업데이트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="한 번에 처리할 장소 수 (기본값: 1000)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="업데이트 기준일 (기본값: 30일, 0이면 전체)",
    )

    args = parser.parse_args()

    db = SessionLocal()
    embedding_service = PlaceEmbeddingService()

    try:
        places = embedding_service.get_places_needing_update(
            db=db,
            days_threshold=args.days,
            limit=args.limit,
        )

        logger.info("=" * 80)
        logger.info(f"장소 임베딩 배치 업데이트 시작")
        logger.info(f"대상 장소 수: {len(places)}")
        logger.info(f"업데이트 기준: {args.days}일 이상 또는 임베딩 없음")
        logger.info("=" * 80)

        success_count = 0
        error_count = 0
        skip_count = 0

        for idx, place in enumerate(places, 1):
            try:
                # 진행 상황 표시
                if idx % 100 == 0:
                    logger.info(
                        f"\n진행: [{idx}/{len(places)}] ({idx/len(places)*100:.1f}%)"
                    )

                logger.info(f"[{idx}/{len(places)}] {place.title} 처리 중...")

                # 리뷰 개수 확인 (DB 조회)
                review_count = (
                    db.query(func.count(PlaceReview.id))
                    .filter(
                        PlaceReview.place_id == place.id,
                        PlaceReview.is_deleted.is_(False),
                        PlaceReview.embedding.isnot(None),
                    )
                    .scalar()
                    or 0
                )

                # 리뷰가 없는 장소는 스킵
                if review_count == 0:
                    logger.info(f"  ⊘ 리뷰가 없어 스킵")
                    skip_count += 1
                    continue

                # 전체 재계산
                embedding_service.refresh_embedding(
                    db=db,
                    place_id=place.id,
                )

                success_count += 1
                logger.info(f"  ✓ 완료 (리뷰 수: {review_count})")

            except Exception as e:
                error_count += 1
                logger.error(f"  ✗ 오류 발생: {e}", exc_info=True)
                db.rollback()

        # 최종 결과
        logger.info("\n" + "=" * 80)
        logger.info("배치 업데이트 완료!")
        logger.info(f"- 성공: {success_count}개")
        logger.info(f"- 스킵: {skip_count}개 (리뷰 없음)")
        logger.info(f"- 실패: {error_count}개")
        logger.info(f"- 총 처리: {success_count + skip_count + error_count}개")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
