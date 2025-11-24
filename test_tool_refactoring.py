"""
도구 리팩토링 테스트 스크립트
ToolResult 응답 구조가 제대로 작동하는지 확인합니다.
"""

import json
from app.schemas.tool_response import ToolResult, PlaceRecommendationData, TravelRouteData


def test_place_recommendation_data():
    """PlaceRecommendationData 테스트"""
    print("=" * 50)
    print("1. PlaceRecommendationData 테스트")
    print("=" * 50)

    # 성공 케이스
    result = ToolResult(
        success=True,
        data=PlaceRecommendationData(
            places=[
                {"id": "place1", "title": "강남역 맛집", "address": "서울 강남구"},
                {"id": "place2", "title": "홍대 카페", "address": "서울 마포구"},
            ],
            count=2
        ),
        message="서울에서 2곳을 찾았습니다."
    )

    result_dict = result.model_dump()
    print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    # 검증
    assert result_dict["success"] == True
    assert result_dict["data"]["count"] == 2
    assert len(result_dict["data"]["places"]) == 2
    print("✅ PlaceRecommendationData 성공 케이스 통과\n")

    # 실패 케이스
    error_result = ToolResult(
        success=False,
        error="위치를 찾을 수 없습니다."
    )
    error_dict = error_result.model_dump()
    print(json.dumps(error_dict, indent=2, ensure_ascii=False))

    assert error_dict["success"] == False
    assert error_dict["error"] is not None
    print("✅ PlaceRecommendationData 실패 케이스 통과\n")


def test_travel_route_data():
    """TravelRouteData 테스트"""
    print("=" * 50)
    print("2. TravelRouteData 테스트")
    print("=" * 50)

    route_data = TravelRouteData(
        total_days=2,
        waypoints_count=2,
        route=[
            {
                "waypoint_name": "연동",
                "waypoint_index": 0,
                "coordinates": {"latitude": 33.4996, "longitude": 126.5312},
                "nearby_places": [
                    {"id": "place1", "title": "제주 흑돼지", "address": "제주시 연동"},
                    {"id": "place2", "title": "연동 카페", "address": "제주시 연동"},
                ]
            },
            {
                "waypoint_name": "해녀촌",
                "waypoint_index": 1,
                "coordinates": {"latitude": 33.5108, "longitude": 126.8697},
                "nearby_places": [
                    {"id": "place3", "title": "해녀의 집", "address": "제주 구좌읍"},
                ]
            }
        ]
    )

    result = ToolResult(
        success=True,
        data=route_data,
        message="2일 여행 코스를 생성했습니다."
    )

    result_dict = result.model_dump()
    print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    # places 프로퍼티 테스트
    places = route_data.places
    print(f"\n평탄화된 장소 목록 (총 {len(places)}개):")
    for place in places:
        print(f"  - {place['title']}")

    assert len(places) == 3  # 연동 2개 + 해녀촌 1개
    print("\n✅ TravelRouteData 테스트 통과\n")


def test_place_extractor():
    """place_extractor 테스트"""
    print("=" * 50)
    print("3. place_extractor 통합 테스트")
    print("=" * 50)

    from app.agent.utils.place_extractor import extract_places_from_result

    # PlaceRecommendationData 케이스
    place_result = {
        "success": True,
        "data": {
            "places": [
                {"id": "p1", "title": "장소1"},
                {"id": "p2", "title": "장소2"},
                {"id": "p3", "title": "장소3"},
            ],
            "count": 3
        },
        "message": "3곳을 찾았습니다."
    }

    places = extract_places_from_result(place_result, "recommend_popular_places_in_region")
    print(f"추출된 장소: {[p.title for p in places]}")
    assert len(places) == 3
    print("✅ PlaceRecommendationData 추출 성공\n")

    # TravelRouteData 케이스
    route_result = {
        "success": True,
        "data": {
            "total_days": 1,
            "waypoints_count": 2,
            "route": [
                {
                    "waypoint_name": "강남",
                    "nearby_places": [
                        {"id": "p4", "title": "강남역 맛집"},
                        {"id": "p5", "title": "강남 카페"},
                    ]
                },
                {
                    "waypoint_name": "홍대",
                    "nearby_places": [
                        {"id": "p6", "title": "홍대 클럽"},
                    ]
                }
            ],
            "places": [  # TravelRouteData.places 프로퍼티의 결과
                {"id": "p4", "title": "강남역 맛집"},
                {"id": "p5", "title": "강남 카페"},
                {"id": "p6", "title": "홍대 클럽"},
            ]
        },
        "message": "1일 코스 생성 완료"
    }

    places = extract_places_from_result(route_result, "create_travel_route")
    print(f"추출된 장소: {[p.title for p in places]}")
    assert len(places) == 3
    print("✅ TravelRouteData 추출 성공\n")

    # 실패 케이스
    error_result = {
        "success": False,
        "error": "위치를 찾을 수 없습니다."
    }

    places = extract_places_from_result(error_result, "recommend_nearby_places")
    assert len(places) == 0
    print("✅ 에러 케이스 처리 성공\n")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("도구 리팩토링 테스트 시작")
    print("=" * 50 + "\n")

    try:
        test_place_recommendation_data()
        test_travel_route_data()
        test_place_extractor()

        print("=" * 50)
        print("✅ 모든 테스트 통과!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        raise
