"""
실제 도구 함수 테스트
place_tool.py와 route_tool.py의 실제 도구들이 ToolResult를 반환하는지 확인합니다.
"""

import json
from app.tools.place_tool import get_place_tools


def test_recommend_popular_places():
    """recommend_popular_places_in_region 실제 테스트"""
    print("=" * 50)
    print("1. recommend_popular_places_in_region 테스트")
    print("=" * 50)

    tools = get_place_tools()
    recommend_popular = tools[0]

    # 실제 도구 호출 (서울 맛집)
    result = recommend_popular.invoke({
        "region": "서울",
        "category": "맛집",
        "limit": 3
    })

    print(f"Result type: {type(result)}")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 검증
    assert isinstance(result, dict), "결과가 dict여야 합니다"
    assert "success" in result, "success 필드가 있어야 합니다"
    assert "data" in result or "error" in result, "data 또는 error 필드가 있어야 합니다"

    if result["success"]:
        assert "data" in result, "성공 시 data 필드가 있어야 합니다"
        assert "places" in result["data"], "data에 places 필드가 있어야 합니다"
        print(f"✅ 성공: {len(result['data']['places'])}개 장소 추천")
    else:
        print(f"⚠️  도구 실행 실패: {result.get('error')}")

    print()


def test_recommend_nearby_places():
    """recommend_nearby_places 실제 테스트"""
    print("=" * 50)
    print("2. recommend_nearby_places 테스트")
    print("=" * 50)

    tools = get_place_tools()
    recommend_nearby = tools[1]

    # 실제 도구 호출 (강남역 주변 카페)
    result = recommend_nearby.invoke({
        "location_name": "강남역",
        "category": "카페",
        "radius_km": 2.0,
        "limit": 3
    })

    print(f"Result type: {type(result)}")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 검증
    assert isinstance(result, dict), "결과가 dict여야 합니다"
    assert "success" in result, "success 필드가 있어야 합니다"

    if result["success"]:
        assert "data" in result, "성공 시 data 필드가 있어야 합니다"
        assert "places" in result["data"], "data에 places 필드가 있어야 합니다"
        print(f"✅ 성공: {len(result['data']['places'])}개 장소 추천")
    else:
        print(f"⚠️  도구 실행 실패: {result.get('error')}")

    print()


def test_place_extractor_integration():
    """place_extractor와 실제 도구 통합 테스트"""
    print("=" * 50)
    print("3. place_extractor 통합 테스트")
    print("=" * 50)

    from app.agent.utils.place_extractor import extract_places_from_result
    from app.tools.place_tool import get_place_tools

    tools = get_place_tools()
    recommend_popular = tools[0]

    # 도구 실행
    result = recommend_popular.invoke({
        "region": "제주도",
        "limit": 5
    })

    print("도구 실행 결과:")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:500] + "...")

    # place_extractor로 추출
    places = extract_places_from_result(result, "recommend_popular_places_in_region")

    print(f"\n추출된 장소 ({len(places)}개):")
    for place in places[:5]:  # 최대 5개만 출력
        print(f"  - {place.title} (ID: {place.id})")

    if result["success"]:
        assert len(places) > 0, "성공 시 장소가 추출되어야 합니다"
        print("\n✅ place_extractor 통합 성공")
    else:
        assert len(places) == 0, "실패 시 장소가 없어야 합니다"
        print("\n⚠️  도구 실행 실패했지만 extractor는 정상 작동")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("실제 도구 테스트 시작")
    print("=" * 50 + "\n")

    try:
        test_recommend_popular_places()
        test_recommend_nearby_places()
        test_place_extractor_integration()

        print("=" * 50)
        print("✅ 모든 테스트 완료!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        raise
