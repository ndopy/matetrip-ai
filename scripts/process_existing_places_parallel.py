"""
이미 DB에 수집된 장소들에 대해 전체 파이프라인을 **병렬**로 실행하는 스크립트

주요 개선사항:
1. 병렬 배치 처리 (동시에 N개씩 처리)
2. 재시작 가능 (이미 처리된 장소 건너뛰기)
3. 진행률 추적 (매 10개마다 로그)
4. 실패 복구 (일부 실패해도 계속 진행)

실행 방법:
    uv run python scripts/process_existing_places_parallel.py

옵션:
    --limit: 처리할 장소 개수 제한 (기본값: 전체)
    --batch-size: 동시 처리 개수 (기본값: 5)
    --skip-completed: 이미 처리된 장소 건너뛰기 (기본값: True)

예시:
    # 전체 처리 (배치 크기 10)
    uv run python scripts/process_existing_places_parallel.py --batch-size 10

    # 테스트 (10개만, 배치 크기 3)
    uv run python scripts/process_existing_places_parallel.py --limit 10 --batch-size 3
"""

import sys
import os
import asyncio
import logging
import argparse
from typing import List
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.models.place import Place
from app.service.place_service import PlaceService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def process_single_place(
    place_id: str, place_title: str, idx: int, total: int
) -> bool:
    """
    단일 장소 처리 (각 태스크마다 새 DB 세션 생성)

    Args:
        place_id: 장소 ID (UUID)
        place_title: 장소 제목 (로그용)
        idx: 인덱스
        total: 전체 개수

    Returns:
        bool: 성공 여부
    """
    db = None
    try:
        # 각 태스크마다 새 DB 세션 생성
        db = SessionLocal()
        place_service = PlaceService(db)

        # 새 세션에서 place 재조회
        place = db.query(Place).filter(Place.id == place_id).first()
        if not place:
            logger.error(f"✗ [{idx}/{total}] 장소를 찾을 수 없습니다: {place_id}")
            return False

        logger.info(f"[{idx}/{total}] {place.title} 처리 시작...")

        # 전체 파이프라인 실행
        await place_service.process_place_reviews(place)

        db.commit()
        logger.info(f"✓ [{idx}/{total}] {place.title} 완료")
        return True

    except Exception as e:
        logger.error(f"✗ [{idx}/{total}] {place_title} 실패: {e}")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()


async def process_batch(
    places_batch: List[tuple],  # [(place_id, place_title, idx, total), ...]
    batch_num: int,
    total_batches: int,
) -> tuple[int, int]:
    """
    배치 단위로 장소들을 병렬 처리

    Returns:
        (success_count, fail_count)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"배치 {batch_num}/{total_batches} 시작 ({len(places_batch)}개)")
    logger.info(f"{'='*80}")

    # 각 장소마다 독립적인 태스크 생성
    tasks = [
        process_single_place(place_id, place_title, idx, total)
        for place_id, place_title, idx, total in places_batch
    ]

    # 병렬 실행
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 결과 집계
    success_count = sum(1 for r in results if r is True)
    fail_count = len(results) - success_count

    logger.info(
        f"배치 {batch_num}/{total_batches} 완료: 성공 {success_count}, 실패 {fail_count}"
    )

    return success_count, fail_count


async def process_places(
    limit: int | None = None, batch_size: int = 5, skip_completed: bool = True
):
    """
    DB에 있는 장소들을 병렬로 처리

    Args:
        limit: 처리할 장소 개수 제한 (None이면 전체)
        batch_size: 동시 처리 개수 (기본값: 5)
        skip_completed: 이미 처리된 장소 건너뛰기 (기본값: True)
    """
    db = SessionLocal()

    try:
        # 처리 대상 장소 조회
        if skip_completed:
            # embedding이 없는 장소만 (가장 중요한 조건)
            query = db.query(Place).filter(Place.embedding.is_(None))
        else:
            # 전체 장소
            query = db.query(Place)

        if limit:
            query = query.limit(limit)

        places = query.all()
        total = len(places)

        logger.info("=" * 80)
        logger.info(f"처리 대상: {total}개")
        logger.info(f"배치 크기: {batch_size}개")
        logger.info(f"예상 배치 수: {(total + batch_size - 1) // batch_size}개")
        logger.info("=" * 80)

        if total == 0:
            logger.info("처리할 장소가 없습니다.")
            return

        # 시작 시간 기록
        start_time = datetime.now()

        # 배치 단위로 나누기 (place_id, place_title, idx, total 전달)
        batches = []
        for i in range(0, total, batch_size):
            batch = [
                (place.id, place.title, idx + 1, total)
                for idx, place in enumerate(places[i : i + batch_size], start=i)
            ]
            batches.append(batch)

        total_batches = len(batches)
        total_success = 0
        total_fail = 0

        # 각 배치 순차 실행 (배치 내에서는 병렬)
        for batch_num, batch in enumerate(batches, 1):
            success, fail = await process_batch(batch, batch_num, total_batches)
            total_success += success
            total_fail += fail

            # 진행률 출력
            processed = total_success + total_fail
            progress = (processed / total) * 100
            logger.info(f"\n진행률: {processed}/{total} ({progress:.1f}%)")

        # 종료 시간 및 통계
        end_time = datetime.now()
        elapsed = end_time - start_time

        logger.info("\n" + "=" * 80)
        logger.info("전체 파이프라인 처리 완료!")
        logger.info(f"- 성공: {total_success}개")
        logger.info(f"- 실패: {total_fail}개")
        logger.info(f"- 소요 시간: {elapsed}")
        logger.info(f"- 평균 처리 시간: {elapsed.total_seconds() / total:.2f}초/개")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="기존 장소에 대해 전체 파이프라인을 병렬로 실행"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 장소 개수 제한 (기본값: 전체)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="동시 처리 개수 (기본값: 5)",
    )
    parser.add_argument(
        "--skip-completed",
        type=bool,
        default=True,
        help="이미 처리된 장소 건너뛰기 (기본값: True)",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("기존 장소 전체 파이프라인 처리 시작 (병렬 버전)")
    logger.info(f"배치 크기: {args.batch_size}")
    if args.limit:
        logger.info(f"처리 제한: {args.limit}개")
    logger.info("=" * 80)

    await process_places(
        limit=args.limit, batch_size=args.batch_size, skip_completed=args.skip_completed
    )


if __name__ == "__main__":
    asyncio.run(main())
