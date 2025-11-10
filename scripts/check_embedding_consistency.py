#!/usr/bin/env python3
"""
임베딩 데이터 정합성 체크 스크립트

아래 항목을 검사합니다.
1. 장소에 저장된 임베딩은 있지만 유효한 리뷰 임베딩이 없는 경우
2. 유효한 리뷰 임베딩이 있지만 장소 임베딩이 비어 있는 경우
3. 전체 통계 (평균 리뷰 수, 최근 업데이트 등)

사용법:
    python scripts/check_embedding_consistency.py
    python scripts/check_embedding_consistency.py --auto-fix
"""

import sys
import os
import argparse
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.service.place_embedding_service import PlaceEmbeddingService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_consistency(db: Session):
    """임베딩은 있지만 유효한 리뷰가 없는 장소를 찾는다."""

    logger.info("=" * 80)
    logger.info("임베딩 데이터 정합성 체크 시작")
    logger.info("=" * 80)

    query = text(
        """
        WITH review_counts AS (
            SELECT place_id, COUNT(*) AS review_count
            FROM place_review
            WHERE is_deleted = FALSE
              AND embedding IS NOT NULL
            GROUP BY place_id
        )
        SELECT
            p.id,
            p.title,
            COALESCE(rc.review_count, 0) AS review_count
        FROM places p
        LEFT JOIN review_counts rc ON rc.place_id = p.id
        WHERE p.embedding IS NOT NULL
          AND COALESCE(rc.review_count, 0) = 0
        ORDER BY p.updated_at DESC NULLS LAST
        LIMIT 100
        """
    )

    dangling = db.execute(query).fetchall()

    if not dangling:
        logger.info("✓ 임베딩과 리뷰 개수 정합성 정상")
        return []

    logger.warning(f"\n⚠ 임베딩은 있지만 리뷰가 없는 장소: {len(dangling)}개")
    logger.warning("=" * 80)

    for idx, row in enumerate(dangling, 1):
        logger.warning(f"{idx}. {row.title} (임베딩 유지, 리뷰 0개)")

    return dangling


def check_embedding_integrity(db: Session):
    """임베딩 무결성 체크"""

    logger.info("\n임베딩 무결성 체크...")

    # 2. 리뷰는 있지만 임베딩이 없는 장소
    query = text(
        """
        SELECT p.id, p.title, COUNT(pr.id) as review_count
        FROM places p
        JOIN place_review pr
          ON p.id = pr.place_id
         AND pr.is_deleted = FALSE
         AND pr.embedding IS NOT NULL
        WHERE p.embedding IS NULL
        GROUP BY p.id, p.title
        ORDER BY COUNT(pr.id) DESC
        LIMIT 20
        """
    )

    missing_embeddings = db.execute(query).fetchall()

    if missing_embeddings:
        logger.warning(
            f"\n⚠ 리뷰는 있지만 임베딩이 없는 장소: {len(missing_embeddings)}개"
        )
        for idx, row in enumerate(missing_embeddings, 1):
            logger.warning(f"{idx}. {row.title}: {row.review_count}개 리뷰")
    else:
        logger.info("✓ 임베딩 무결성 정상")

    return missing_embeddings


def check_statistics(db: Session):
    """통계 정보 확인"""

    logger.info("\n전체 통계 확인...")

    # 전체 장소 수
    total_places = db.execute(text("SELECT COUNT(*) FROM places")).scalar()

    # 임베딩이 있는 장소 수
    places_with_embedding = db.execute(
        text("SELECT COUNT(*) FROM places WHERE embedding IS NOT NULL")
    ).scalar()

    # 평균 리뷰 개수 (유효한 리뷰만 집계)
    avg_reviews = db.execute(
        text(
            """
            SELECT AVG(review_count)
            FROM (
                SELECT COUNT(*) AS review_count
                FROM place_review
                WHERE is_deleted = FALSE
                  AND embedding IS NOT NULL
                GROUP BY place_id
            ) sub
            """
        )
    ).scalar()

    # 최근 7일간 업데이트된 장소 (updated_at 사용)
    recent_updates = db.execute(
        text(
            "SELECT COUNT(*) FROM places "
            "WHERE updated_at > NOW() - INTERVAL '7 days'"
        )
    ).scalar()

    logger.info("=" * 80)
    logger.info("📊 전체 통계")
    logger.info(f"- 전체 장소 수: {total_places:,}개")
    logger.info(f"- 임베딩 있는 장소: {places_with_embedding:,}개")
    logger.info(f"- 임베딩 없는 장소: {total_places - places_with_embedding:,}개")
    logger.info(f"- 평균 리뷰 개수: {avg_reviews:.1f}개")
    logger.info(f"- 최근 7일 업데이트: {recent_updates:,}개")
    logger.info("=" * 80)


def auto_fix_inconsistencies(db: Session, inconsistent_places):
    """불일치 자동 수정"""

    if not inconsistent_places:
        logger.info("수정할 항목이 없습니다.")
        return

    logger.info(f"\n자동 수정 시작: {len(inconsistent_places)}개 장소")

    embedding_service = PlaceEmbeddingService()
    success_count = 0
    error_count = 0

    for idx, row in enumerate(inconsistent_places, 1):
        try:
            logger.info(f"[{idx}/{len(inconsistent_places)}] {row.title} 수정 중...")

            embedding_service.refresh_embedding(db=db, place_id=row.id)

            success_count += 1

        except Exception as e:
            error_count += 1
            logger.error(f"  ✗ 오류 발생: {e}")
            db.rollback()

    logger.info("\n" + "=" * 80)
    logger.info("자동 수정 완료!")
    logger.info(f"- 성공: {success_count}개")
    logger.info(f"- 실패: {error_count}개")
    logger.info("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="임베딩 데이터 정합성 체크",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="불일치 항목 자동 수정",
    )

    args = parser.parse_args()

    db = SessionLocal()

    try:
        # 1. 정합성 체크
        inconsistent = check_consistency(db)

        # 2. 임베딩 무결성 체크
        missing = check_embedding_integrity(db)

        # 3. 통계 확인
        check_statistics(db)

        # 4. 자동 수정 (옵션)
        if args.auto_fix:
            if inconsistent or missing:
                logger.info("\n자동 수정 모드 활성화")
                auto_fix_inconsistencies(db, inconsistent)
            else:
                logger.info("\n수정할 항목이 없습니다.")
        else:
            if inconsistent or missing:
                logger.info(
                    "\n💡 불일치 항목을 수정하려면 --auto-fix 옵션을 사용하세요."
                )

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
