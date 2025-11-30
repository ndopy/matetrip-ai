"""여행 루트 생성 도구 (LLM 어댑터)"""

from typing import List, Optional
from langchain_core.tools import tool

from app.common.logger import logger
from app.database.database import get_db_session
from app.service.place_service import PlaceService
from app.service.route_service import RouteService
from app.schemas.route_request import CreateRouteRequest
from app.schemas.tool_response import ToolResult, TravelRouteData
from app.tools.place_tool import normalize_category


def get_route_tools():
    """
    [여행 코스 생성 도구]
    사용자가 지정한 경유지를 기반으로 여행 코스를 생성합니다.
    """

    @tool
    def create_travel_route(
        waypoints: List[str],
        days: int = 1,
        nearby_places_per_waypoint: int = 2,
        radius_km: float = 4.0,
        category: Optional[str] = None,
        excluded_place_ids: Optional[List[str]] = None,
    ):
        """
        사용자가 지정한 경유지를 기준으로 여행 코스를 생성합니다.
        각 경유지마다 근처 장소를 추천하여 전체 여행 일정을 구성합니다.

        **이 도구를 사용해야 하는 상황:**
        - "제주도 연동에서 시작해서 해녀촌을 경유하고 김영해수욕장을 경유하는 코스 만들어줘"
        - "서울 홍대에서 시작해서 이태원, 강남을 거쳐가는 1박 2일 여행 계획"
        - "부산 해운대에서 광안리, 감천문화마을을 거치는 여행 코스"
        - "경주 불국사부터 첨성대, 안압지를 도는 당일치기 코스"

        Args:
            waypoints: 경유지 리스트 (순서대로 방문)
                - 예: ["연동", "해녀촌", "김영해수욕장"]
                - 예: ["홍대", "이태원", "강남"]
                - 최소 1개 이상의 경유지 필요
            days: 여행 일수 (기본값: 1일)
                - 1박 2일이면 2로 설정
                - 2박 3일이면 3으로 설정
            nearby_places_per_waypoint: 각 경유지마다 추천할 근처 장소 개수 (기본값: 2개)
                - 경유지가 많으면 1~2개로 제한
                - 경유지가 적으면 3~5개로 늘릴 수 있음
            radius_km: 경유지 주변 검색 반경 (km 단위, 기본값: 4km)
                - 도시 내 코스: 2~3km
                - 지역 코스: 5~10km
            category: 추천받을 카테고리 (선택사항)
                - '음식' 또는 '맛집': 레스토랑, 카페 등
                - '숙박' 또는 '호텔': 호텔, 펜션 등
                - '레포츠' 또는 '놀거리': 레저, 스포츠 등
                - '자연' 또는 '관광지': 자연관광지, 산, 바다 등
                - '인문' 또는 '문화': 박물관, 미술관 등
                - None이면 모든 카테고리 검색
            excluded_place_ids: 제외할 장소 ID 리스트 (선택사항)
                - 이미 추천받은 장소나 제외하고 싶은 장소의 ID 목록
                - 이 ID들은 추천 결과에서 제외됩니다

        Returns:
            {
                "total_days": 총 여행 일수,
                "waypoints_count": 경유지 개수,
                "route": [
                    {
                        "waypoint_name": 경유지 이름,
                        "waypoint_index": 경유지 순서 (0부터 시작),
                        "coordinates": {"latitude": ..., "longitude": ...},
                        "nearby_places": [
                            {
                                장소 정보 (title, address, category, tags, summary 등)
                            }
                        ]
                    }
                ]
            }

        **답변 작성 규칙:**
        1. 경유지 순서대로 코스를 설명하세요.
        2. 각 경유지마다 추천된 근처 장소를 소개하세요.
        3. 기술적 정보(ID, 좌표, distance_km 등)는 절대 언급하지 마세요.
        4. **이름, 주소, 카테고리, 태그, 요약**만 사용하여 소개하세요.
        5. N박 M일 형식으로 일정을 구성하여 설명하세요.

        **올바른 답변 예시:**
        "제주도 1박 2일 여행 코스를 만들어드렸어요!

        **1일차: 연동 출발**
        연동을 시작으로 주변 맛집 2곳을 추천드려요:
        - **제주 흑돼지 맛집** (제주시 연동...)
          현지인 추천, 두툼한 고기, 깔끔한 분위기
        - **연동 카페거리** (제주시 연동...)
          조용한 분위기, 디저트 맛집

        **1일차: 해녀촌 경유**
        해녀촌 근처에서 이런 곳들을 들러보세요:
        - **해녀의 집** (제주시 구좌읍...)
          신선한 해산물, 전통 방식, 가성비 좋음

        **2일차: 김영해수욕장**
        마지막 경유지 김영해수욕장 주변 추천:
        - **김영해변 카페** (제주 서귀포시...)
          오션뷰, 여유로운 분위기"
        """
        # 입력값 검증
        validation_error = _validate_inputs(
            waypoints, days, nearby_places_per_waypoint
        )
        if validation_error:
            return validation_error

        logger.info(f"여행 코스 생성: {len(waypoints)}개 경유지, {days}일")

        # 카테고리 매핑
        mapped_category = normalize_category(category)

        # DTO 생성 (6개 파라미터 → DTO 캡슐화)
        request = CreateRouteRequest.create(
            waypoints=waypoints,
            days=days,
            nearby_places_per_waypoint=nearby_places_per_waypoint,
            radius_km=radius_km,
            category=mapped_category,
            excluded_place_ids=excluded_place_ids,
        )

        # ========================================
        # Service Layer 호출 (순수 비즈니스 로직)
        # ========================================
        with get_db_session() as db:
            place_service = PlaceService(db)
            route_service = RouteService(place_service)
            response = route_service.create_travel_route(request)

        # ========================================
        # Tool Layer: ToolResult로 포장 (LLM 어댑터)
        # ========================================
        response_dict = response.model_dump()
        return ToolResult(
            success=True,
            data=TravelRouteData(**response_dict),
            message=f"{days}일 여행 코스를 생성했습니다. (경유지 {len(waypoints)}개)",
        ).model_dump()

    return [create_travel_route]


def _validate_inputs(
    waypoints: List[str], days: int, nearby_places_per_waypoint: int
) -> Optional[dict]:
    """입력값 검증"""
    if not waypoints:
        return ToolResult(
            success=False, error="최소 1개 이상의 경유지를 지정해주세요."
        ).model_dump()

    if len(waypoints) > 5:
        return ToolResult(
            success=False,
            error=f"경유지는 최대 5개까지 지정할 수 있습니다. (현재: {len(waypoints)}개)",
        ).model_dump()

    if days <= 0:
        return ToolResult(
            success=False, error="여행 일수는 최소 1일 이상이어야 합니다."
        ).model_dump()

    if nearby_places_per_waypoint > 5:
        return ToolResult(
            success=False,
            error=f"경유지당 추천 장소는 최대 5개까지 가능합니다. (현재: {nearby_places_per_waypoint}개)",
        ).model_dump()

    return None
