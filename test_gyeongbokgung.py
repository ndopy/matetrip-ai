"""경복궁 장소만 테스트하는 스크립트"""
import sys
import os
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal
from app.models.place import Place
from app.service.place_service import PlaceService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_gyeongbokgung():
    """경복궁 장소 처리 테스트"""
    db = SessionLocal()

    try:
        # 경복궁 조회
        place = db.query(Place).filter(Place.title == "경복궁").first()

        if not place:
            logger.error("경복궁을 찾을 수 없습니다!")
            return

        logger.info(f"\n{'='*80}")
        logger.info(f"경복궁 파이프라인 테스트 시작")
        logger.info(f"ID: {place.id}")
        logger.info(f"제목: {place.title}")
        logger.info(f"주소: {place.address}")
        logger.info(f"{'='*80}\n")

        # PlaceService로 처리 (force_update=True)
        place_service = PlaceService()
        await place_service.process_place_reviews(db, place, force_update=True)

        db.commit()

        logger.info(f"\n{'='*80}")
        logger.info("경복궁 처리 완료!")
        logger.info(f"{'='*80}\n")

        # 결과 확인
        db.refresh(place)
        logger.info(f"태그: {place.tags}")
        logger.info(f"요약: {place.summary[:200] if place.summary else 'None'}...")
        logger.info(f"임베딩: {'생성됨' if place.embedding is not None else '없음'}")

        # 리뷰 수 확인
        from app.models.review import PlaceReview
        review_count = db.query(PlaceReview).filter(PlaceReview.place_id == place.id).count()
        logger.info(f"리뷰 수: {review_count}개")

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_gyeongbokgung())
