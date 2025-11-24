"""
장소 추천 도구 결과 추출 유틸리티
"""

from typing import List, Any
from app.schemas.place import SimplePlace
from app.common.logger import logger


# 장소 추천 도구 목록 (하드코딩)
PLACE_RECOMMENDATION_TOOLS = [
    "recommend_popular_places_in_region",
    "recommend_nearby_places",
    "create_travel_route",
]


def is_place_recommendation_tool(tool_name: str) -> bool:
    """
    장소 추천 도구인지 확인

    Args:
        tool_name: 도구 이름

    Returns:
        장소 추천 도구이면 True
    """
    return tool_name in PLACE_RECOMMENDATION_TOOLS


def extract_places_from_result(result: Any, tool_name: str) -> List[SimplePlace]:
    """
    도구 실행 결과에서 장소 목록 추출

    Args:
        result: 도구 실행 결과
        tool_name: 도구 이름

    Returns:
        추출된 SimplePlace 리스트
    """
    if not is_place_recommendation_tool(tool_name):
        return []

    places = []

    try:
        if tool_name == "create_travel_route":
            # 여행 코스: route -> waypoints -> nearby_places
            places = _extract_from_travel_route(result)
        else:
            # recommend_popular_places_in_region, recommend_nearby_places
            # 둘 다 List[Dict] 형태로 반환
            places = _extract_from_place_list(result)

    except Exception as e:
        logger.error(f"[extract_places_from_result] Error extracting places from {tool_name}: {e}")

    logger.info(f"[extract_places_from_result] Extracted {len(places)} places from {tool_name}")
    return places


def _extract_from_travel_route(result: Any) -> List[SimplePlace]:
    """
    여행 코스 결과에서 장소 추출

    구조:
    {
        "route": [
            {
                "waypoint_name": "...",
                "nearby_places": [
                    {"id": "...", "title": "...", ...},
                    ...
                ]
            },
            ...
        ]
    }
    """
    places = []

    if not isinstance(result, dict) or "route" not in result:
        return places

    for waypoint in result.get("route", []):
        if not isinstance(waypoint, dict):
            continue

        for place in waypoint.get("nearby_places", []):
            if isinstance(place, dict) and "id" in place and "title" in place:
                places.append(SimplePlace(id=place["id"], title=place["title"]))

    return places


def _extract_from_place_list(result: Any) -> List[SimplePlace]:
    """
    장소 리스트 결과에서 장소 추출

    구조:
    [
        {"id": "...", "title": "...", ...},
        {"id": "...", "title": "...", ...},
        ...
    ]
    """
    places = []

    if not isinstance(result, list):
        return places

    for place in result:
        if isinstance(place, dict) and "id" in place and "title" in place:
            places.append(SimplePlace(id=place["id"], title=place["title"]))

    return places
