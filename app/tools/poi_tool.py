import httpx
import logging
from typing import Dict
from langchain_core.tools import tool

from app.common.config import nestJSConfig
from app.service.place_service import PlaceService
from app.schemas.place import NearbyPlaceRequest
from app.database.database import get_db
from app.repository.place_repository import PlaceRepository

BASE_URL = nestJSConfig.NESTJS_BACKEND_URL
logger = logging.getLogger(__name__)


def get_poi_tools():
    """
    [POI 분석 및 추천 도구 모음]
    현재 사용자가 일정에 추가한 장소를 분석하여 부족한 부분을 채워주는 도구입니다.
    """

    @tool
    def recommend_next_poi(workspace_id: str):
        """
        현재 사용자가 일정에 추가한 장소들을 분석하여 부족한 카테고리의 장소를 추천합니다.

        **이 도구를 사용해야 하는 상황:**
        - "다음에 뭘 추가하면 좋을까?"
        - "일정이 괜찮은지 확인해줘"
        - "뭐가 부족해?"
        - "숙소 추천해줘" (현재 추가한 곳들 근처)
        - "밥 먹을 곳 알려줘" (현재 추가한 곳들 근처)
        - "여행 일정 균형이 맞나?"
        - "뭘 더 넣으면 좋을까?"

        **분석하는 내용:**
        1. 숙박 시설 부족 여부
           - 예: 2박 3일이면 숙소 2개 필요
        2. 식사 장소 부족 여부
           - 하루 2~3끼 기준으로 판단
        3. 카테고리 다양성
           - 관광지만 많고 휴식 공간이 없는지 등

        Args:
            workspace_id: 분석할 워크스페이스 ID (현재 사용자가 작업 중인 여행 계획의 고유 ID)

        Returns:
            분석 결과와 추천 장소 목록

        **답변 작성 규칙:**
        1. 분석 결과(analysis.reason)를 바탕으로 부족한 이유를 자연스럽게 설명하세요.
        2. 추천 장소는 **이름, 주소, 카테고리, 태그, 요약**만 사용하여 소개하세요.
        3. 기술적 정보(ID, 좌표, distance_km 등)는 절대 언급하지 마세요.
        4. 부족한 카테고리가 없으면 "현재 일정이 균형잡혀 있습니다!"라고 답변하세요.

        **답변 예시:**
        "2박 3일 여행인데 숙소가 1개만 추가되어 있네요. 1개 더 필요합니다.
        현재 추가하신 장소들 중심으로 근처 숙소를 추천드릴게요:

        1. **제주 힐링 펜션** (제주 서귀포시...)
           - 바다 전망, 조용한 분위기, 가족 단위 추천

        2. **오션뷰 게스트하우스** (제주 제주시...)
           - 깨끗한 시설, 친절한 사장님, 가성비 좋음"
        """
        try:
            logger.info(f"[recommend_next_poi] workspace_id={workspace_id}")

            # 1. NestJS에서 scheduled POI 데이터 가져오기
            with httpx.Client(timeout=30.0) as client:
                logger.info(
                    f"NestJS API 호출: GET {BASE_URL}/workspace/{workspace_id}/scheduled-pois"
                )
                response = client.get(
                    f"{BASE_URL}/workspace/{workspace_id}/scheduled-pois",
                )
                response.raise_for_status()
                data = response.json()

            plan_day_groups = data.get("planDayScheduledPoisGroup", [])
            logger.info(f"총 {len(plan_day_groups)}일 일정 데이터 수신")

            # 2. POI가 없으면 조기 반환
            if not plan_day_groups:
                return {
                    "analysis": {
                        "reason": "아직 일정에 추가된 장소가 없습니다. 먼저 장소를 추가해주세요.",
                        "missing_categories": [],
                        "category_distribution": {},
                        "total_days": 0,
                        "current_poi_count": 0,
                    },
                    "recommendations": [],
                }

            # 3. 모든 POI 수집 및 Places DB 조회하여 카테고리 매핑
            db = next(get_db())
            try:
                place_repo = PlaceRepository(db)
                all_pois = []
                category_count: Dict[str, int] = {}

                for group in plan_day_groups:
                    pois = group.get("pois", [])
                    for poi in pois:
                        # placeId로 Places DB 조회 (인덱스 활용)
                        place_id = poi.get("placeId")
                        place = place_repo.find_by_id(place_id)

                        category = place.category if place else "기타"

                        # 카테고리 집계
                        category_count[category] = category_count.get(category, 0) + 1

                        all_pois.append(
                            {
                                "id": poi.get("id"),
                                "place_name": poi.get("placeName"),
                                "category": category,
                                "latitude": poi.get("latitude"),
                                "longitude": poi.get("longitude"),
                            }
                        )

                logger.info(f"총 {len(all_pois)}개 POI 수집 완료")
                logger.info(f"카테고리 분포: {category_count}")

                # 4. 부족한 카테고리 판단
                total_days = len(plan_day_groups)
                missing_categories = []
                reason_parts = []

                # 숙박 체크 (총 일수 - 1개 필요, 예: 2박 3일이면 숙소 2개)
                required_accommodation = max(0, total_days - 1)
                current_accommodation = category_count.get("숙박", 0)

                if current_accommodation < required_accommodation:
                    missing_categories.append("숙박")
                    shortage = required_accommodation - current_accommodation
                    reason_parts.append(
                        f"{total_days}일 일정인데 숙소가 {current_accommodation}개만 있습니다. {shortage}개 더 필요합니다."
                    )

                # 음식 체크 (하루 2끼 기준)
                required_meals = total_days * 2
                current_meals = category_count.get("음식", 0)

                if current_meals < required_meals:
                    missing_categories.append("음식")
                    shortage = required_meals - current_meals
                    reason_parts.append(
                        f"식사 장소가 {current_meals}개만 있습니다. {shortage}개 정도 더 추가하시면 좋습니다."
                    )

                # 5. 추천 이유 생성
                if reason_parts:
                    recommendation_reason = " ".join(reason_parts)
                else:
                    recommendation_reason = "현재 일정이 균형잡혀 있습니다!"

                # 6. 부족한 카테고리가 없으면 조기 반환
                if not missing_categories:
                    return {
                        "analysis": {
                            "reason": recommendation_reason,
                            "missing_categories": [],
                            "category_distribution": category_count,
                            "total_days": total_days,
                            "current_poi_count": len(all_pois),
                        },
                        "recommendations": [],
                    }

                # 7. 중심 좌표 계산
                latitudes = [poi["latitude"] for poi in all_pois]
                longitudes = [poi["longitude"] for poi in all_pois]
                center_lat = sum(latitudes) / len(latitudes)
                center_lng = sum(longitudes) / len(longitudes)

                logger.info(f"중심 좌표: ({center_lat}, {center_lng})")

                # 8. 부족한 카테고리 중 가장 우선순위가 높은 것 추천
                primary_category = missing_categories[0]
                logger.info(f"가장 부족한 카테고리: {primary_category}")

                # 9. 중심점 기준 15km 반경에서 장소 검색
                request = NearbyPlaceRequest.from_coordinates(
                    latitude=center_lat,
                    longitude=center_lng,
                    radius_km=15.0,
                    category=primary_category,
                    limit=10,
                )

                place_service = PlaceService(db)
                recommendations = place_service.get_nearby_place(request)

                logger.info(f"{len(recommendations)}개 추천 장소 발견")

                return {
                    "analysis": {
                        "reason": recommendation_reason,
                        "missing_categories": missing_categories,
                        "category_distribution": category_count,
                        "total_days": total_days,
                        "current_poi_count": len(all_pois),
                    },
                    "recommendations": [place.model_dump() for place in recommendations],
                }

            finally:
                db.close()

        except httpx.HTTPStatusError as e:
            error_msg = f"NestJS API 오류: {e.response.status_code}"
            if e.response.status_code == 404:
                error_msg = "워크스페이스를 찾을 수 없습니다. workspace_id를 확인해주세요."
            logger.error(f"{error_msg} - {e.response.text}")
            return error_msg
        except httpx.RequestError as e:
            error_msg = f"NestJS 서버에 연결할 수 없습니다: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"POI 분석 중 에러 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    return [recommend_next_poi]
