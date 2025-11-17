"""인기 장소 추천 기능 테스트 스크립트"""
import sys
from app.database.database import get_db
from app.schemas.place import PopularPlaceRequest
from app.service.place_service import PlaceService


def test_popular_places():
    """인기 장소 추천 기능 테스트"""

    # DB 세션 가져오기
    db = next(get_db())

    try:
        service = PlaceService(db)

        # 테스트 케이스 1: 제주도 전체 인기 장소
        print("\n=== 테스트 1: 제주도 전체 인기 장소 ===")
        request1 = PopularPlaceRequest.create(
            region="제주도",
            category=None,
            limit=5
        )
        results1 = service.get_popular_places_in_region(request1)
        print(f"결과 개수: {len(results1)}")
        for place in results1:
            print(f"  - {place.title} (인기도: {place.popularity_score})")

        # 테스트 케이스 2: 서울 맛집
        print("\n=== 테스트 2: 서울 맛집 ===")
        request2 = PopularPlaceRequest.create(
            region="서울",
            category="음식",
            limit=5
        )
        results2 = service.get_popular_places_in_region(request2)
        print(f"결과 개수: {len(results2)}")
        for place in results2:
            print(f"  - {place.title} (인기도: {place.popularity_score})")

        # 테스트 케이스 3: 부산 관광지
        print("\n=== 테스트 3: 부산 관광지 ===")
        request3 = PopularPlaceRequest.create(
            region="부산",
            category="자연",
            limit=5
        )
        results3 = service.get_popular_places_in_region(request3)
        print(f"결과 개수: {len(results3)}")
        for place in results3:
            print(f"  - {place.title} (인기도: {place.popularity_score})")

        # 테스트 케이스 4: 잘못된 지역명
        print("\n=== 테스트 4: 잘못된 지역명 ===")
        try:
            request4 = PopularPlaceRequest.create(
                region="화성",
                category=None,
                limit=5
            )
            results4 = service.get_popular_places_in_region(request4)
        except ValueError as e:
            print(f"예상된 에러 발생: {e}")

        print("\n✅ 모든 테스트 완료!")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    test_popular_places()
