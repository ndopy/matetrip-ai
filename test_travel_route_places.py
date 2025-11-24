"""
TravelRouteData에서 places 필드가 올바르게 생성되는지 테스트
"""

from app.schemas.tool_response import TravelRouteData

# 테스트 데이터
test_route = [
    {
        "waypoint_name": "연동",
        "waypoint_index": 0,
        "nearby_places": [
            {"id": "place1", "title": "한라수목원", "address": "제주시 연동"},
            {"id": "place2", "title": "제주 카페", "address": "제주시 연동"},
        ]
    },
    {
        "waypoint_name": "해녀촌",
        "waypoint_index": 1,
        "nearby_places": [
            {"id": "place3", "title": "해녀의 집", "address": "제주시 구좌읍"},
        ]
    }
]

# TravelRouteData 생성
travel_route_data = TravelRouteData(
    total_days=2,
    waypoints_count=2,
    route=test_route
)

print("=== TravelRouteData 객체 ===")
print(f"total_days: {travel_route_data.total_days}")
print(f"waypoints_count: {travel_route_data.waypoints_count}")
print(f"places 개수: {len(travel_route_data.places)}")
print(f"places: {travel_route_data.places}")

print("\n=== model_dump() 결과 ===")
dumped = travel_route_data.model_dump()
print(f"places in dump: {dumped.get('places')}")

print("\n=== extract_places_from_result 시뮬레이션 ===")
# ToolResult로 감싸진 형태
from app.schemas.tool_response import ToolResult

tool_result = ToolResult(
    success=True,
    data=travel_route_data,
    message="테스트"
)

# model_dump 호출
result_dict = tool_result.model_dump()
print(f"result_dict keys: {result_dict.keys()}")
print(f"result_dict['data'] type: {type(result_dict.get('data'))}")

data = result_dict.get("data", {})
places = data.get("places", [])
print(f"추출된 places 개수: {len(places)}")
print(f"추출된 places: {places}")
