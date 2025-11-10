"""
전체 파이프라인을 1개 장소로 테스트하는 스크립트

실행 방법:
    uv run python scripts/test_full_pipeline.py
"""

import sys
import os
import asyncio
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.place import Place
from app.service.kakao_local_service import KakaoLocalService
from app.service.place_service import PlaceService
from app.data.seoul_districts import SEOUL_DISTRICTS

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_full_pipeline():
    """전체 파이프라인을 1개 장소로 테스트"""
    db = SessionLocal()
    kakao_service = KakaoLocalService()
    place_service = PlaceService()

    try:
        logger.info("=" * 80)
        logger.info("전체 파이프라인 테스트 시작 (1개 장소)")
        logger.info("=" * 80)

        # 강남구에서 관광명소 검색 (1개만)
        district = SEOUL_DISTRICTS[5]  # 강남구
        logger.info(f"\n{district['name']}에서 관광명소 검색 중...")

        kakao_places = kakao_service.search_places_by_category(
            category_code="AT4",  # 관광명소
            x=district["longitude"],
            y=district["latitude"],
            radius=5000,
            max_pages=1,  # 1페이지만 (15개)
        )

        if not kakao_places:
            logger.error("검색된 장소가 없습니다.")
            return

        # 첫 번째 장소만 사용
        kakao_place = kakao_places[0]
        place_data = kakao_service.convert_to_place_data(kakao_place)

        logger.info(f"\n선택된 장소: {place_data['title']}")
        logger.info(f"주소: {place_data['address']}")
        logger.info(f"카카오 카테고리: {place_data['categories']}")

        # 1. Place 객체 생성 및 저장
        new_place = Place(
            title=place_data["title"],
            address=place_data["address"],
            categories=place_data["categories"],
            longitude=place_data["longitude"],
            latitude=place_data["latitude"],
        )

        db.add(new_place)
        db.commit()
        db.refresh(new_place)

        logger.info(f"\n✓ 장소 DB 저장 완료 (ID: {new_place.id})")

        # 2. 전체 파이프라인 실행
        logger.info("\n" + "=" * 80)
        logger.info("전체 파이프라인 실행 시작")
        logger.info("=" * 80)

        await place_service.process_place_reviews(db, new_place)
        db.commit()

        logger.info("\n" + "=" * 80)
        logger.info("✓ 전체 파이프라인 완료!")
        logger.info("=" * 80)

        # 3. 결과 확인
        logger.info("\n[처리 결과]")
        logger.info(f"장소명: {new_place.title}")
        logger.info(
            f"이미지 URL: {new_place.image_url[:50] + '...' if new_place.image_url else 'None'}"
        )
        logger.info(f"카테고리: {new_place.categories}")
        logger.info(f"태그: {new_place.tags}")
        logger.info(
            f"요약: {new_place.summary[:100] + '...' if new_place.summary else 'None'}"
        )

        # 리뷰 개수 확인
        from app.models.review import PlaceReview

        review_count = (
            db.query(PlaceReview).filter(PlaceReview.place_id == new_place.id).count()
        )
        logger.info(f"리뷰 개수: {review_count}개")

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


async def main():
    await test_full_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
