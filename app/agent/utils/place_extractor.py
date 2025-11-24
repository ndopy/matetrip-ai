"""
장소 추천 도구 결과 추출 유틸리티

모든 도구가 ToolResult 형식으로 반환하므로 추출 로직이 단순화되었습니다.
"""

from typing import List, Any
from app.schemas.place import SimplePlace
from app.common.logger import logger


def extract_places_from_result(result: Any, tool_name: str) -> List[SimplePlace]:
    """
    도구 실행 결과에서 장소 목록 추출

    모든 도구가 ToolResult[T] 형식으로 반환하므로 처리가 일관적입니다.

    Args:
        result: 도구 실행 결과 (ToolResult의 dict 형태)
        tool_name: 도구 이름 (로깅용)

    Returns:
        추출된 SimplePlace 리스트
    """
    try:
        # result가 dict인지 확인
        if not isinstance(result, dict):
            logger.warning(
                f"[extract_places_from_result] Invalid result type from {tool_name}: {type(result)}"
            )
            return []

        # 성공 여부 확인
        if not result.get("success", False):
            logger.warning(
                f"[extract_places_from_result] Tool {tool_name} failed: {result.get('error')}"
            )
            return []

        # data 필드 추출
        data = result.get("data", {})
        if not data or not isinstance(data, dict):
            logger.info(f"[extract_places_from_result] No data in result from {tool_name}")
            return []

        # places 필드 추출
        # PlaceRecommendationData는 places 필드를 직접 가지고 있고,
        # TravelRouteData는 places 프로퍼티를 통해 평탄화된 리스트를 반환합니다.
        places_data = data.get("places", [])

        if not isinstance(places_data, list):
            logger.warning(
                f"[extract_places_from_result] 'places' field is not a list in {tool_name}"
            )
            return []

        # SimplePlace로 변환
        places = []
        for place in places_data:
            if isinstance(place, dict) and "id" in place and "title" in place:
                places.append(SimplePlace(id=place["id"], title=place["title"]))

        logger.info(
            f"[extract_places_from_result] Extracted {len(places)} places from {tool_name}"
        )
        return places

    except Exception as e:
        logger.error(
            f"[extract_places_from_result] Error extracting places from {tool_name}: {e}"
        )
        return []
