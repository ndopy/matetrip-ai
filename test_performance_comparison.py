"""
주변 장소 검색 성능 비교 테스트
- PostGIS 공간 인덱스 사용 vs Haversine 공식 (공간 인덱스 미사용)
"""

import time
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.service.place_service import PlaceService


def measure_time(func, *args, **kwargs):
    """함수 실행 시간을 측정하는 헬퍼"""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


def run_performance_test():
    """성능 비교 테스트 실행"""
    db: Session = SessionLocal()

    try:
        service = PlaceService(db)

        # 테스트 파라미터
        test_cases = [
            {
                "name": "서울 강남역 주변 5km",
                "latitude": 37.498095,
                "longitude": 127.027610,
                "radius_km": 5.0,
                "category": None,
                "limit": 10,
            },
            {
                "name": "서울 강남역 주변 10km (더 넓은 범위)",
                "latitude": 37.498095,
                "longitude": 127.027610,
                "radius_km": 10.0,
                "category": None,
                "limit": 20,
            },
            {
                "name": "부산 해운대 주변 5km",
                "latitude": 35.158698,
                "longitude": 129.160385,
                "radius_km": 5.0,
                "category": None,
                "limit": 10,
            },
        ]

        print("=" * 80)
        print("주변 장소 검색 성능 비교 테스트")
        print("=" * 80)
        print()

        for idx, test_case in enumerate(test_cases, 1):
            print(f"[테스트 케이스 {idx}] {test_case['name']}")
            print(f"  - 위치: ({test_case['latitude']}, {test_case['longitude']})")
            print(f"  - 반경: {test_case['radius_km']}km")
            print(f"  - 카테고리: {test_case['category'] or '전체'}")
            print(f"  - 제한: {test_case['limit']}개")
            print()

            # 1. PostGIS 공간 인덱스 사용
            # print("  [방법 1] PostGIS 공간 인덱스 사용")
            # places_postgis, time_postgis = measure_time(
            #     service.find_nearby_places,
            #     latitude=test_case["latitude"],
            #     longitude=test_case["longitude"],
            #     radius_km=test_case["radius_km"],
            #     category=test_case["category"],
            #     limit=test_case["limit"],
            # )
            # print(f"    ⏱️  실행 시간: {time_postgis:.4f}초")
            # print(f"    📍 결과 개수: {len(places_postgis)}개")

            # 2. Haversine 공식 (공간 인덱스 미사용)
            print()
            print("  [방법 2] Haversine 공식 (공간 인덱스 미사용)")
            places_haversine, time_haversine = measure_time(
                service.find_nearby_places_haversine,
                latitude=test_case["latitude"],
                longitude=test_case["longitude"],
                radius_km=test_case["radius_km"],
                category=test_case["category"],
                limit=test_case["limit"],
            )
            print(f"    ⏱️  실행 시간: {time_haversine:.4f}초")
            print(f"    📍 결과 개수: {len(places_haversine)}개")

            # # 성능 비교
            # print()
            # if time_haversine > 0:
            #     speedup = time_haversine / time_postgis
            #     percentage = ((time_haversine - time_postgis) / time_haversine) * 100
            #     print(f"  📊 성능 비교:")
            #     print(f"    - PostGIS가 {speedup:.2f}배 빠름")
            #     print(f"    - PostGIS가 {percentage:.1f}% 더 빠름")

            # # 결과 샘플 출력 (상위 3개)
            # if places_postgis:
            #     print()
            #     print("  📍 PostGIS 결과 샘플 (상위 3개):")
            #     for i, place in enumerate(places_postgis[:3], 1):
            #         print(f"    {i}. {place.title} ({place.address})")

            # if places_haversine:
            #     print()
            #     print("  📍 Haversine 결과 샘플 (상위 3개):")
            #     for i, place in enumerate(places_haversine[:3], 1):
            #         print(f"    {i}. {place.title} ({place.address})")

            print()
            print("-" * 80)
            print()

        print()
        print("=" * 80)
        print("테스트 완료!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_performance_test()
