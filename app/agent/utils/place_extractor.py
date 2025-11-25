"""
장소 추천 도구 결과 추출 유틸리티

모든 도구가 ToolResult 형식으로 반환하므로 추출 로직이 단순화되었습니다.
"""

from typing import List, Any
from app.schemas.place import SimplePlace
from app.common.logger import logger
from app.schemas.tool_response import TravelRouteData


def is_success(result: dict) -> bool:
    return result.get("success", False)


def extract_places_from_result(result: dict, tool_name: str) -> List[SimplePlace]:
    """
    도구 실행 결과에서 장소 목록 추출

    모든 도구가 ToolResult[T] 형식으로 반환하므로 처리가 일관적입니다.

    Args:
        result: 도구 실행 결과 (ToolResult의 dict 형태)
        tool_name: 도구 이름 (로깅용)

    Returns:
        추출된 SimplePlace 리스트
    """
    # 성공 여부 확인
    if not is_success(result):
        logger.warning(f"[extract_places] {tool_name} failed: {result.get('error')}")
        return []

    # data 필드 추출
    data = result.get("data", {})
    if data is None or not isinstance(data, dict):
        logger.info(f"[extract_places_from_result] No data in result from {tool_name}")
        return []

    # places 필드 추출
    places: List[SimplePlace] = TravelRouteData.model_validate(data).places
    logger.info(
        f"[extract_places_from_result] Extracted {len(places)} places from {tool_name}"
    )
    return places
