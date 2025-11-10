"""
이미 DB에 수집된 장소들에 대해 전체 파이프라인을 실행하는 스크립트
- 이미지 URL 수집 (네이버 이미지 검색)
- 리뷰 URL 수집 (네이버 블로그 검색)
- 리뷰 크롤링 (Crawl4AI)
- 리뷰 임베딩 생성 (로컬 모델)
- 태그/요약 생성 (OpenAI GPT)

실행 방법:
    uv run python scripts/process_existing_places.py

또는 특정 개수만:
    uv run python scripts/process_existing_places.py --limit 5
"""

import sys
import os
import asyncio
import logging
import argparse
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


async def process_places(limit: int | None = None):
    """
    DB에 있는 장소들에 대해 전체 파이프라인 실행

    Args:
        limit: 처리할 장소 개수 제한 (None 또는 0이면 전체)
    """
    db = SessionLocal()
    place_service = PlaceService()

    try:
        # 이미지 URL, 태그, 요약이 없는 장소들 조회
        query = db.query(Place).filter(
            (Place.image_url == None) | (Place.tags == None) | (Place.summary == None)
        )

        if limit:
            query = query.limit(limit)

        places = query.all()

        total = len(places)
        logger.info("=" * 80)
        logger.info(f"처리할 장소: {total}개")
        logger.info("=" * 80)

        if total == 0:
            logger.info("처리할 장소가 없습니다.")
            return

        success_count = 0
        fail_count = 0

        for idx, place in enumerate(places, 1):
            logger.info(f"\n[{idx}/{total}] {place.title} 처리 시작...")
            logger.info(f"주소: {place.address}")

            try:
                # 전체 파이프라인 실행
                # 1. 이미지 URL 수집
                # 2. 리뷰 URL 수집
                # 3. 리뷰 크롤링
                # 4. 리뷰 임베딩 생성
                # 5. 태그/요약 생성
                await place_service.process_place_reviews(db, place)

                db.commit()
                success_count += 1
                logger.info(f"✓ [{idx}/{total}] {place.title} 처리 완료!")

            except Exception as e:
                logger.error(
                    f"✗ [{idx}/{total}] {place.title} 처리 실패: {e}", exc_info=True
                )
                db.rollback()
                fail_count += 1
                continue

        # 최종 결과
        logger.info("\n" + "=" * 80)
        logger.info("전체 파이프라인 처리 완료!")
        logger.info(f"- 성공: {success_count}개")
        logger.info(f"- 실패: {fail_count}개")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
    finally:
        db.close()


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="기존 장소에 대해 전체 파이프라인 실행"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 장소 개수 제한 (기본값: 전체)",
    )

    args = parser.parse_args()

    logger.info("기존 장소 전체 파이프라인 처리 시작")
    if args.limit:
        logger.info(f"처리 제한: {args.limit}개")

    await process_places(limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
