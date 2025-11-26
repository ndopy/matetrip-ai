"""
장소 추천 도구 결과 추출 유틸리티

모든 도구가 ToolResult 형식으로 반환하므로 추출 로직이 단순화되었습니다.
"""

from typing import List, Any
from app.schemas.place import SimplePlace
from app.common.logger import logger
from app.schemas.tool_response import ToolResult, TravelRouteData

# PlaceRecommendationData: places, count만 포함
# (recommend_popular_places_in_region, recommend_nearby_places, replace_single_place)
from app.schemas.tool_response import PlaceRecommendationData


def is_success(result: dict) -> bool:
    return result.get("success", False)


def extract_simple_places_from_result(
    result: dict, tool_name: str
) -> List[SimplePlace]:
    """
    도구 실행 결과에서 장소 목록 추출
    모든 도구가 ToolResult[T] 형식으로 반환
    Args:
        result: 도구 실행 결과 (ToolResult의 dict 형태)
        tool_name: 도구 이름 (로깅용)

    Returns:
        추출된 SimplePlace 리스트
    """
    if not is_success(result):
        logger.warning(f"[extract_places] {tool_name} failed: {result.get('error')}")
        return []

    data = result.get("data", {})
    if data is None or not isinstance(data, dict):
        logger.info(f"[extract_places_from_result] No data in result from {tool_name}")
        return []

    # 도구별로 다른 스키마 사용
    if tool_name == "create_travel_route":
        # TravelRouteData: total_days, waypoints_count, route, places 포함
        places: List[SimplePlace] = TravelRouteData.model_validate(data).places
    else:
        place_data = PlaceRecommendationData.model_validate(data)
        # dict를 SimplePlace로 변환
        places = [
            SimplePlace(id=str(p.get("id", "")), title=str(p.get("title", "")))
            for p in place_data.places
            if isinstance(p, dict) and "id" in p and "title" in p
        ]

    logger.info(
        f"[extract_places_from_result] Extracted {len(places)} places from {tool_name}"
    )
    return places
