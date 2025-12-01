"""지오코딩 유틸리티 (Kakao Local API)"""

import httpx
import logging
import os

logger = logging.getLogger(__name__)

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_LOCAL_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def fetch_coordinates_from_address(location_name: str) -> tuple[float, float]:
    """Kakao Local API를 사용하여 주소/장소명으로 좌표 검색"""
    if not KAKAO_REST_API_KEY:
        raise ValueError(
            "Kakao API 키가 설정되지 않았습니다. .env 파일에 KAKAO_REST_API_KEY를 추가해주세요."
        )

    with httpx.Client(timeout=60.0) as client:
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        search_response = client.get(
            KAKAO_LOCAL_SEARCH_URL,
            headers=headers,
            params={"query": location_name, "size": 1},
        )
        logger.info("Kakao Local API 호출 완료")
        search_response.raise_for_status()
        search_data = search_response.json()

    documents = search_data.get("documents", [])
    if not documents:
        raise ValueError(
            f"'{location_name}'에 대한 검색 결과가 없습니다. 다른 이름으로 시도해보세요."
        )

    doc = documents[0]
    latitude = float(doc["y"])
    longitude = float(doc["x"])

    logger.info(f"좌표 검색 완료: {location_name} -> ({latitude}, {longitude})")
    return latitude, longitude
