"""
단일 장소로 전체 파이프라인 테스트
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import SessionLocal
from app.models.place import Place
from app.service.place_service import PlaceService


async def test_single_place():
    """경복궁으로 전체 파이프라인 테스트"""
    db = SessionLocal()

    try:
        # 경복궁 검색 (title에 경복궁이 포함된 장소)
        place = db.query(Place).filter(Place.title.like("%경복궁%")).first()

        if not place:
            print("경복궁을 찾을 수 없습니다. 다른 유명 관광지로 테스트합니다.")
            # 대안: 남산타워, 북촌한옥마을 등
            alternatives = ["남산", "북촌", "명동", "광화문"]
            for alt in alternatives:
                place = db.query(Place).filter(Place.title.like(f"%{alt}%")).first()
                if place:
                    break

        if not place:
            print("테스트할 장소를 찾을 수 없습니다.")
            return

        print("=" * 80)
        print(f"테스트 장소: {place.title}")
        print(f"주소: {place.address}")
        print("=" * 80)

        # 전체 파이프라인 실행 (force_update=True로 강제 재처리)
        place_service = PlaceService()
        await place_service.process_place_reviews(db, place, force_update=True)

        db.commit()

        print("\n" + "=" * 80)
        print("파이프라인 완료!")
        print(f"- 장소: {place.title}")
        print(f"- 태그: {place.tags}")
        print(f"- 요약: {place.summary[:200] if place.summary else '없음'}...")
        print(f"- 임베딩: {'있음' if place.embedding else '없음'}")
        print("=" * 80)

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_single_place())
