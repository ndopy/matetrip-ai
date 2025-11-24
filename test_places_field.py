"""
TravelRouteData의 places 필드가 model_dump()에 포함되는지 확인
"""

import json
from app.schemas.tool_response import TravelRouteData

# 테스트 데이터
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

print("=" * 60)
print("TravelRouteData.model_dump() 결과:")
print("=" * 60)

dumped = route_data.model_dump()
print(json.dumps(dumped, indent=2, ensure_ascii=False))

print("\n" + "=" * 60)
print("places 필드 확인:")
print("=" * 60)

if "places" in dumped:
    print(f"✅ places 필드 존재: {len(dumped['places'])}개 장소")
    for place in dumped['places']:
        print(f"  - {place['title']} (ID: {place['id']})")
else:
    print("❌ places 필드 없음!")

print("\n" + "=" * 60)
print("place_extractor 테스트:")
print("=" * 60)

from app.agent.utils.place_extractor import extract_places_from_result

# ToolResult 형식으로 감싸기
tool_result = {
    "success": True,
    "data": dumped,
    "message": "테스트"
}

places = extract_places_from_result(tool_result, "create_travel_route")
print(f"추출된 장소: {len(places)}개")
for place in places:
    print(f"  - {place.title} (ID: {place.id})")

if len(places) == 3:
    print("\n✅ create_travel_route 장소 추출 성공!")
else:
    print(f"\n❌ 장소 추출 실패! 예상: 3개, 실제: {len(places)}개")
