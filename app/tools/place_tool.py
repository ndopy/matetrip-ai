import json
import logging
import time
import httpx
import os
from typing import List, Optional
from langchain_core.tools import tool

from app.common.category_mapping import CATEGORY_MAPPING
from app.service.place_service import PlaceService
from app.database.database import get_db, get_db_session
from app.utils.geocoding import fetch_coordinates_from_address
from app.schemas.place import (
    NearbyPlaceRequest,
    NearbyPlaceResponse,
    PopularPlaceRequest,
    PopularPlaceResponse,
    ReplacePlaceRequest,
)
from app.schemas.tool_response import ToolResult, PlaceRecommendationData

logger = logging.getLogger(__name__)

# Kakao Local API 설정
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_LOCAL_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

# 지역명 정규화 매핑 (약칭 → 정식명 또는 sido)
REGION_NORMALIZATION = {
    # 광역시 약칭 → sido (정식명)
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    # 광역시 정식명 → sido (그대로 통과)
    "서울특별시": "서울특별시",
    "부산광역시": "부산광역시",
    "대구광역시": "대구광역시",
    "인천광역시": "인천광역시",
    "광주광역시": "광주광역시",
    "대전광역시": "대전광역시",
    "울산광역시": "울산광역시",
    "세종특별자치시": "세종특별자치시",
    # 도 약칭 → sido (정식명)
    "경기": "경기도",
    "강원": "강원특별자치도",
    "제주": "제주특별자치도",
    # 도 정식명 → sido (그대로 통과)
    "경기도": "경기도",
    "강원특별자치도": "강원특별자치도",
    "강원도": "강원특별자치도",  # 옛 이름도 지원
    "제주특별자치도": "제주특별자치도",
    "제주도": "제주특별자치도",
    # 지역 그룹 약칭 → region (RegionGroupType enum 값)
    "충북": "충청도",
    "충남": "충청도",
    "충청": "충청도",
    "충청도": "충청도",
    "충청북도": "충청도",
    "충청남도": "충청도",
    "전북": "전라도",
    "전남": "전라도",
    "전라": "전라도",
    "전라도": "전라도",
    "전북특별자치도": "전라도",
    "전라북도": "전라도",
    "전라남도": "전라도",
    "경북": "경상도",
    "경남": "경상도",
    "경상": "경상도",
    "경상도": "경상도",
    "경상북도": "경상도",
    "경상남도": "경상도",
}


def normalize_region_name(region: str) -> str:
    """
    지역명 정규화
    Args:
        region: 입력 지역명 (예: "대전", "서울", "경기" 등)
    Returns:
        정규화된 지역명 (예: "대전광역시", "서울특별시", "경기도" 등)
    """
    region = region.strip()
    return REGION_NORMALIZATION.get(region, region)


def normalize_category(category: Optional[str]) -> Optional[str]:
    """카테고리를 DB 카테고리로 매핑하고 정규화합니다."""
    if not category:
        return None

    lowered = str(category).lower()
    # "None"/"none"/"없음" 같이 의미 없는 값은 제거
    if lowered in {"none", "null", "없음", "모두", "전체"}:
        return None

    return CATEGORY_MAPPING.get(lowered, category)


# TODO: 다른 서비스에 넣어놓기
def get_place_tools():
    """
    [장소 추천 관련 도구 모음]
    우리 DB에 저장된 장소 데이터를 기반으로 추천합니다.
    """

    @tool
    def recommend_popular_places_in_region(
        region: str,
        category: Optional[str] = None,
        limit: int = 10,
    ):
        """
        **[PRIMARY TOOL for BROAD regions]**
        **CRITICAL: This is the MAIN tool when user asks about popular/famous places in BROAD regions!**

        **ONLY use for these broad regions:**
        '서울', '부산', '대전', '대구', '광주', '울산', '세종', '인천', '제주도', '제주', '강원도', '강원', '경기도', '경기', '경상도', '전라도', '충청도'

        **For specific locations (like '강남', '홍대', '해운대', '경주', '전주') → use recommend_nearby_places instead!**

        광역 지역 또는 광역시에서 인기 있는 장소를 추천합니다.

        특정 지역에서 다른 사용자들의 과거 기록을 기반으로 인기 장소를 추천합니다.
        사용자들이 많이 관심 있어하는(마크하거나 일정에 추가한) 장소를 우선적으로 추천합니다.

        Args:
            region: 광역 지역명 또는 광역시명
                - 광역시: '서울', '부산', '대전', '대구', '광주', '인천', '울산', '세종'
                - 광역 지역: '제주도', '제주', '강원도', '강원', '경기도', '경기', '경상도', '전라도', '충청도'
            category: 추천받을 카테고리 (선택사항)
                - '음식' 또는 '맛집': 레스토랑, 카페 등
                - '숙박' 또는 '호텔': 호텔, 펜션, 게스트하우스, 캠핑장 등
                - '레포츠' 또는 '놀거리': 레저, 스포츠, 액티비티 등
                - '자연' 또는 '관광지': 자연관광지, 산, 바다 등
                - '인문' 또는 '문화': 박물관, 미술관, 역사유적지 등
                - '추천코스' 또는 '여행코스': 여행 코스
                - None이면 모든 카테고리 검색
            limit: 추천할 장소 개수 (기본값: 20개)

        올바른 사용 예시:
            - "제주도 인기장소" → recommend_popular_places_in_region("제주도", None, 10)
            - "제주도에서 놀려고 하는데 사람들이 많이 가는 곳 추천해줘"
              → recommend_popular_places_in_region("제주도", None, 10)
            - "제주 핫플" → recommend_popular_places_in_region("제주", None, 10)
            - "부산에서 사람들이 많이 찾는 맛집 알려줘"
              → recommend_popular_places_in_region("부산", "음식", 10)
            - "서울에서 인기 많은 관광지 5곳만"
              → recommend_popular_places_in_region("서울", "자연", 5)
            - "대전 여행지 추천해줘"
              → recommend_popular_places_in_region("대전", None, 10)
            - "광주에서 핫한 카페"
              → recommend_popular_places_in_region("광주", "음식", 10)

        잘못된 사용 예시 (이럴 때는 recommend_nearby_places 사용):
            - "강남 맛집" → X (강남은 구체적인 지역)
            - "홍대 카페" → X (홍대는 구체적인 지역)
            - "명동 관광지" → X (명동은 구체적인 지역)
            - "경주 문화유적지" → X (경주는 구체적인 도시)
            - "전주 맛집" → X (전주는 구체적인 도시)

        [중요: 의미적 필터링 규칙]
        이 도구는 카테고리별로 넓게 검색합니다. 사용자가 구체적인 장소 타입을 요청한 경우:
        1. 먼저 적절한 카테고리로 검색을 수행하세요
        2. 결과를 받은 후, 각 장소의 title, tags, summary를 분석하여 사용자 요청과 의미적으로 일치하는 장소만 선별하세요

        [답변 작성 규칙]
        1. 이 도구의 실행 결과에는 기술적인 정보(ID, 좌표 등)가 포함될 수 있습니다.
        2. 하지만 사용자에게 답변할 때는 **절대 기술적인 정보(ID, 좌표)를 말하지 마세요.**
        3. 오직 **이름, 주소, 카테고리, 태그, 요약** 등 사람이 읽을 수 있는 정보만 사용하여 자연스럽게 요약해 주세요.
        4. 각 장소의 summary(리뷰 요약)가 있으면 함께 소개하면 좋습니다.
        5. 태그(tags)가 있으면 장소의 특징을 설명할 때 활용하세요.
        6. "다른 사용자들이 많이 찾는" 또는 "인기 있는" 장소임을 자연스럽게 언급하세요.
        """
        try:
            if limit <= 0 or limit > 100:
                raise ValueError(f"limit must be between 1 and 100, but got {limit}")

            # 지역명 정규화
            normalized_region = normalize_region_name(region.strip())

            # 카테고리를 DB 카테고리로 매핑
            mapped_category = normalize_category(category)

            # 요청 DTO 생성
            request = PopularPlaceRequest.create(
                region=normalized_region,
                category=mapped_category,
                limit=limit,
            )

            with get_db_session() as db:
                place_responses = PlaceService(db).get_popular_places_in_region(request)
                place_dicts = [place.model_dump() for place in place_responses]
                return ToolResult(
                    success=True,
                    data=PlaceRecommendationData(
                        places=place_dicts, count=len(place_dicts)
                    ),
                    message=f"{normalized_region}에서 인기 있는 장소 {len(place_dicts)}곳을 찾았습니다.",
                ).model_dump()

        except ValueError as e:
            return ToolResult(
                success=False, error=f"지역명 검증 실패: {str(e)}"
            ).model_dump()
        except Exception as e:
            logger.error(f"인기 장소 추천 중 에러 발생: {str(e)}")
            return ToolResult(
                success=False, error=f"인기 장소 추천 중 에러 발생: {str(e)}"
            ).model_dump()

    @tool
    def recommend_nearby_places(
        location_name: str,
        category: Optional[str] = None,
        radius_km: float = 5.0,
        limit: int = 20,
    ):
        """
        특정 위치 주변의 장소를 추천합니다. 우리 DB에 저장된 실제 장소 데이터를 기반으로 추천합니다.

        Args:
            location_name: 기준이 될 장소명 (예: '강남역', '제주공항', '성수동')
            category: 추천받을 카테고리 (선택사항)
                - '음식' 또는 '맛집': 레스토랑, 카페 등
                - '숙박' 또는 '호텔': 호텔, 펜션, 게스트하우스, 캠핑장 등
                - '레포츠' 또는 '놀거리': 레저, 스포츠, 액티비티 등
                - '자연' 또는 '관광지': 자연관광지, 산, 바다 등
                - '인문' 또는 '문화': 박물관, 미술관, 역사유적지 등
                - '추천코스' 또는 '여행코스': 여행 코스
                - None이면 모든 카테고리 검색
            radius_km: 검색 반경 (km 단위, 기본값: 5km)
                - 사용자가 '가까운', '근처'라고 하면 3km 정도
                - '~km 이내'라고 구체적으로 말하면 해당 값 사용
                - '주변'이라고 하면 5km 정도
                - '~km 이내'라고 구체적으로 말하면 해당 값 사용
            limit: 추천할 장소 개수 (기본값: 10개)
                - 사용자가 '몇 개'라고 구체적으로 말하면 해당 값 사용
                - 특별한 언급이 없으면 10개 정도

        올바른 사용 예시:
            - "강남 맛집 추천해줘" -> recommend_nearby_places("강남", "음식", 5.0, 10)

        사용 예시:
            - "강남역 주변 맛집 추천해줘" -> recommend_nearby_places("강남역", "음식", 5.0, 10)
            - "제주공항 근처 3km 이내 숙소 5개만" -> recommend_nearby_places("제주공항", "숙박", 3.0, 5)
            - "성수동 가까운 곳에 놀거리" -> recommend_nearby_places("성수동", "레포츠", 3.0, 10)
            - "홍대 주변 관광지" -> recommend_nearby_places("홍대", "자연", 5.0, 10)
            - "경주 문화유적지" -> recommend_nearby_places("경주", "인문", 5.0, 10)
            - "전주 맛집" -> recommend_nearby_places("전주", "음식", 5.0, 10)
            - "속초 주변 캠핑장" -> recommend_nearby_places("속초", "숙박", 5.0, 15)
            - "부산 주변 캠핑장" -> recommend_nearby_places("부산", "숙박", 5.0, 15)
                → 결과를 받은 후, tags에 "캠핑", "노지", "글램핑" 등이 포함된 장소만 선별하여 답변

        [중요: 의미적 필터링 규칙]
        이 도구는 카테고리별로 넓게 검색합니다. 사용자가 구체적인 장소 타입을 요청한 경우:
        1. 먼저 적절한 카테고리로 검색을 수행하세요
        2. 결과를 받은 후, 각 장소의 title, tags, summary를 분석하여 사용자 요청과 의미적으로 일치하는 장소만 선별하세요
        3. 예시:
           - "캠핑장" 요청 시 → '숙박' 카테고리로 검색 → tags에 "캠핑", "노지", "글램핑", "취사 가능" 등이 있는 장소 선별
           - "카페" 요청 시 → '음식' 카테고리로 검색 → title이나 tags에 "카페", "커피", "디저트" 등이 있는 장소 선별
           - "수영장" 요청 시 → '레포츠' 카테고리로 검색 → tags에 "수영", "워터파크", "물놀이" 등이 있는 장소 선별
           - "사찰" 요청 시 → '인문' 카테고리로 검색 → title이나 tags에 "사찰", "절", "전통" 등이 있는 장소 선별

        [답변 작성 규칙]
        1. 이 도구의 실행 결과에는 기술적인 정보(ID, 좌표 등)가 포함될 수 있습니다.
        2. 하지만 사용자에게 답변할 때는 **절대 기술적인 정보(ID, 좌표)를 말하지 마세요.**
        3. 오직 **이름, 주소, 카테고리, 태그, 요약** 등 사람이 읽을 수 있는 정보만 사용하여 자연스럽게 요약해 주세요.
        4. 각 장소의 summary(리뷰 요약)가 있으면 함께 소개하면 좋습니다.
        5. 태그(tags)가 있으면 장소의 특징을 설명할 때 활용하세요.
        6. 의미적 필터링을 수행한 경우, 사용자가 요청한 타입의 장소임을 자연스럽게 언급하세요.
           예: "부산 주변 캠핑장 3곳을 추천드립니다"
        """
        try:
            # 카테고리를 DB 카테고리로 매핑
            mapped_category = normalize_category(category)

            # 1. Kakao Local API로 장소명을 좌표로 변환
            t0 = time.perf_counter()
            try:
                latitude, longitude = fetch_coordinates_from_address(location_name)
            except ValueError as error:
                return ToolResult(
                    success=False, error=f"위치 조회 실패: {str(error)}"
                ).model_dump()

            t1 = time.perf_counter()
            print(f"[fetch_coordinates_from_address] took {t1-t0:.4f} seconds")

            # 2. NearbyPlaceRequest DTO로 캡슐화
            search_request = NearbyPlaceRequest.from_coordinates(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                category=mapped_category,
                limit=limit,
            )

            with get_db_session() as db:
                t2 = time.perf_counter()
                place_responses = PlaceService(db).get_nearby_place(search_request)
                t3 = time.perf_counter()
                print(f"[PlaceService.get_nearby_place] took {t3-t2:.4f} seconds")

                place_dicts = [place.model_dump() for place in place_responses]

                if not place_dicts:
                    category_text = f"({mapped_category}) " if mapped_category else ""
                    return ToolResult(
                        success=False,
                        error=f"{location_name} 주변 {radius_km}km 이내에 {category_text}장소를 찾을 수 없습니다.",
                    ).model_dump()

                return ToolResult(
                    success=True,
                    data=PlaceRecommendationData(
                        places=place_dicts, count=len(place_dicts)
                    ),
                    message=f"{location_name} 주변 {len(place_dicts)}곳을 찾았습니다.",
                ).model_dump()

        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False,
                error=f"API 오류 발생: {e.response.status_code} - {e.response.text}",
            ).model_dump()
        except Exception as e:
            return ToolResult(
                success=False, error=f"장소 추천 중 에러 발생: {str(e)}"
            ).model_dump()

    @tool
    def replace_places(
        replace_target_ids: List[str],
        latitude: float,
        longitude: float,
        excluded_place_ids: List[str],
        category: Optional[str] = None,
        radius_km: float = 5.0,
    ):
        """
        특정 장소들을 대체할 새로운 장소들을 추천합니다.
        기존 추천 장소 중 일부를 제외하고 같은 위치에서 새로운 장소로 교체할 때 사용합니다.

        Args:
            replace_target_ids: 교체 대상 장소 ID 리스트 (이 개수만큼 새로운 장소 추천)
                - 예: ["place1_id", "place3_id"] → 2개의 새로운 장소 추천
            latitude: 기준 위도 (교체할 장소들이 있던 지역의 좌표)
            longitude: 기준 경도
            excluded_place_ids: 추천에서 제외할 모든 장소 ID 리스트 (기존 추천 전체 + 교체 대상 포함)
                - 중복 방지를 위해 이미 추천된 모든 장소 ID를 포함해야 합니다
            category: 추천받을 카테고리 (선택사항)
            radius_km: 검색 반경 (km 단위, 기본값: 5km)

        Returns:
            len(replace_target_ids)만큼의 새로운 장소 리스트

        사용 예시:
            - 사용자: "1번이랑 3번 빼고 다른 거로 바꿔줘"
            - replace_target_ids: ["place1_id", "place3_id"]
            - excluded_place_ids: ["place1_id", "place2_id", ..., "place10_id"] (전체 기존 추천)
            - 결과: 2개의 새로운 장소 추천

            - 사용자: "카페 다 빼고"
            - replace_target_ids: ["cafe1_id", "cafe2_id"]
            - excluded_place_ids: [모든 기존 추천 장소 ID들]
            - 결과: 2개의 새로운 장소 추천
        """
        if not replace_target_ids:
            return ToolResult(
                success=False,
                error="교체할 장소가 지정되지 않았습니다.",
            ).model_dump()

        try:
            request = ReplacePlaceRequest.create(
                latitude=latitude,
                longitude=longitude,
                replace_count=len(replace_target_ids),  # 교체할 개수
                excluded_place_ids=excluded_place_ids,
                category=normalize_category(category),  # 카테고리 정규화
                radius_km=radius_km,
            )

            with get_db_session() as db:
                place_service = PlaceService(db)
                place_responses = place_service.find_replacement_places(request)

                if not place_responses:
                    return ToolResult(
                        success=False,
                        error=f"해당 위치 주변에서 대체할 장소를 찾을 수 없습니다.",
                    ).model_dump()

                place_dicts = [place.model_dump() for place in place_responses]

                return ToolResult(
                    success=True,
                    data=PlaceRecommendationData(
                        places=place_dicts,
                        count=len(place_dicts),
                        replaced_place_ids=replace_target_ids,  # 메타정보
                    ),
                    message=f"대체 장소 {len(place_dicts)}곳을 찾았습니다.",
                ).model_dump()

        except Exception as e:
            logger.error(f"장소 대체 중 에러 발생: {str(e)}")
            return ToolResult(
                success=False, error=f"장소 대체 중 에러 발생: {str(e)}"
            ).model_dump()

    return [
        recommend_popular_places_in_region,
        recommend_nearby_places,
        replace_places,
    ]
