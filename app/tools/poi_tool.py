import httpx
import logging
from dataclasses import dataclass
from typing import Dict, List
from uuid import UUID

from langchain_core.tools import tool
from pydantic import ValidationError

from app.common.config import nestJSConfig
from app.service.place_service import PlaceService
from app.schemas.poi import (
    PlanDayScheduledPoisGroupDto,
    PlanDayScheduleSummaryDto,
    PoiResDto,
)
from app.database.database import get_db
from app.repository.place_repository import PlaceRepository
from app.models.place import Place
from app.common.logger import logger  # use shared loguru logger so INFO logs show up

BACKEND_BASE_URL = nestJSConfig.NESTJS_BACKEND_URL


@dataclass
class PlanDayPOIDetails:
    plan_day: PlanDayScheduleSummaryDto
    pois: list[dict]
    category_count: Dict[str, int]


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
            {
                "total_days": 전체 일정 일수,
                "daily_reports": [
                    {
                        "day_no": 일차 번호,
                        "plan_date": 일정 날짜,
                        "analysis": {
                            "reason": 분석 사유,
                            "missing_categories": 부족 카테고리 목록,
                            "category_distribution": 카테고리 분포,
                            "current_poi_count": 해당 날짜 POI 수
                        },
                        "recommendations": [
                            {
                                장소 정보...,
                                "recommended_category": 이 장소가 추천된 카테고리 (예: "숙박", "음식")
                            }
                        ]
                    },
                    ...
                ]
            }

        **답변 작성 규칙:**
        1. 분석 결과(analysis.reason)를 바탕으로 부족한 이유를 자연스럽게 설명하세요.
        2. 추천 장소는 **이름, 주소, 카테고리, 태그, 요약**만 사용하여 소개하세요.
        3. 기술적 정보(ID, 좌표, distance_km 등)는 절대 언급하지 마세요.
        4. 부족한 카테고리가 없으면 "현재 일정이 균형잡혀 있습니다!"라고 답변하세요.

        **답변 예시:**
        "1일차 일정에 숙소가 없습니다. 밤을 보낼 숙소를 추가해주세요.
        1일차에 식사 장소가 0개만 있습니다. 2개 정도 더 추가하시면 좋습니다.
        현재 추가하신 장소들 중심으로 근처 추천 장소를 알려드릴게요:

        **[숙박 추천]**
        1. **제주 힐링 펜션** (제주 서귀포시...)
           - 바다 전망, 조용한 분위기, 가족 단위 추천

        **[음식 추천]**
        2. **성산 해물뚝배기** (제주 서귀포시 성산읍...)
           - 신선한 해산물, 현지인 맛집, 가성비 좋음"
        """
        print(f"[recommend_next_poi] workspaceId = {workspace_id}")
        try:
            # logger.info(f"[recommend_try문 시작작] workspace_id={workspace_id}")
            print(f"[recommend_try문 시작작] workspace_id={workspace_id}")

            plan_day_groups: list[PlanDayScheduledPoisGroupDto] = (
                _fetch_plan_day_groups(workspace_id)
            )

            if not plan_day_groups:
                return _build_empty_schedule_response()

            db = next(get_db())
            try:
                place_repo = PlaceRepository(db)
                plan_day_details: list[PlanDayPOIDetails] = _collect_plan_day_details(
                    plan_day_groups, place_repo
                )

                if not plan_day_details:
                    return _build_empty_schedule_response()

                total_days = len(plan_day_details)
                daily_reports = []

                # plan_day: PlanDayScheduleSummaryDto
                # pois: list[dict]
                # category_count: Dict[str, int]

                for idx, day_detail in enumerate(plan_day_details):

                    plan_day_info: PlanDayScheduleSummaryDto = day_detail.plan_day
                    # pois: list[PoiResDto] = day_detail.pois
                    day_label = f"{plan_day_info.dayNo}일차"

                    if not day_detail.pois:
                        analysis_payload = _build_day_analysis_payload(
                            "아직 이 날짜에 추가된 장소가 없습니다. 먼저 장소를 추가해주세요.",
                            [],
                            day_detail.category_count,
                            0,
                        )
                        daily_reports.append(
                            {
                                "day_no": plan_day_info.dayNo,
                                "plan_date": plan_day_info.planDate,
                                "analysis": analysis_payload,
                                "recommendations": [],
                            }
                        )
                        continue

                    missing_categories, recommendation_reason = (
                        _analyze_day_category_balance(
                            day_detail.category_count,
                            idx,
                            total_days,
                            day_label,
                        )
                    )
                    analysis_payload = _build_day_analysis_payload(
                        recommendation_reason,
                        missing_categories,
                        day_detail.category_count,
                        len(day_detail.pois),
                    )

                    recommendations = []
                    if missing_categories:
                        center_latitude, center_longitude = (
                            _calculate_center_coordinates(day_detail.pois)
                        )
                        # 부족한 카테고리별로 추천 (최대 2개 카테고리)
                        for category in missing_categories[:2]:
                            category_places = _recommend_places(
                                db,
                                center_latitude,
                                center_longitude,
                                category,
                            )
                            # 카테고리당 5개씩 추천 (총 최대 10개)
                            for place in category_places[:5]:
                                place_dict = place.model_dump()
                                place_dict["recommended_category"] = category
                                recommendations.append(place_dict)

                    daily_reports.append(
                        {
                            "day_no": plan_day_info.dayNo,
                            "plan_date": plan_day_info.planDate,
                            "analysis": analysis_payload,
                            "recommendations": recommendations,
                        }
                    )

                return {
                    "total_days": total_days,
                    "daily_reports": daily_reports,
                }
            finally:
                db.close()

        except httpx.HTTPStatusError as e:
            error_msg = f"NestJS API 오류: {e.response.status_code}"
            if e.response.status_code == 404:
                error_msg = (
                    "워크스페이스를 찾을 수 없습니다. workspace_id를 확인해주세요."
                )
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


def _fetch_plan_day_groups(workspace_id: str) -> list[PlanDayScheduledPoisGroupDto]:
    logger.info("=====================_fetch_plan_day_groups=====================")
    with httpx.Client(timeout=30.0) as client:
        url = f"{BACKEND_BASE_URL}/workspace/{workspace_id}/scheduled-pois"
        logger.info(f"NestJS API 호출: GET {url}")
        response = client.get(
            f"{BACKEND_BASE_URL}/workspace/{workspace_id}/scheduled-pois"
        )
        response.raise_for_status()
        raw_data = response.json()

    if not isinstance(raw_data, list):
        raise ValueError("NestJS 응답 형식이 올바르지 않습니다: 리스트가 필요합니다.")

    try:
        plan_day_groups = [
            PlanDayScheduledPoisGroupDto.model_validate(item) for item in raw_data
        ]
    except ValidationError as e:
        error_msg = f"NestJS 응답 데이터 검증 실패: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e

    logger.info("총 %d일 일정 데이터 수신", len(plan_day_groups))
    return plan_day_groups


def _build_empty_schedule_response() -> dict:
    return {
        "total_days": 0,
        "daily_reports": [],
        "message": "아직 일정에 추가된 장소가 없습니다. 먼저 장소를 추가해주세요.",
    }


def _collect_plan_day_details(
    plan_day_groups: list[PlanDayScheduledPoisGroupDto], place_repo: PlaceRepository
) -> list[PlanDayPOIDetails]:
    all_poi_dtos: list[PoiResDto] = [
        poi for group in plan_day_groups for poi in group.pois
    ]

    place_ids = [poi.placeId for poi in all_poi_dtos]
    try:
        uuid_place_ids = _validate_place_ids(place_ids) if place_ids else []
    except ValueError as e:
        logger.error(f"[collect_plan_day_details] ${str(e)}")
        raise

    place_map: Dict[str, Place] = {}

    if uuid_place_ids:
        places: List[Place] = place_repo.find_by_ids(uuid_place_ids)
        place_map = {str(place.id): place for place in places}

    plan_day_details: list[PlanDayPOIDetails] = []
    total_pois = 0

    for group in plan_day_groups:
        day_pois = []
        day_category_count: Dict[str, int] = {}

        for poi in group.pois:
            place = place_map.get(poi.placeId)
            category = place.category if place else "기타"
            day_category_count[category] = day_category_count.get(category, 0) + 1
            day_pois.append(
                {
                    "id": poi.id,
                    "place_name": poi.placeName,
                    "category": category,
                    "latitude": poi.latitude,
                    "longitude": poi.longitude,
                }
            )

        total_pois += len(day_pois)
        plan_day_details.append(
            PlanDayPOIDetails(
                plan_day=group.planDay,
                pois=day_pois,
                category_count=day_category_count,
            )
        )

    logger.info(
        "총 %d개 POI 수집 완료 (Bulk 조회: %d개 place_id)", total_pois, len(place_ids)
    )

    return plan_day_details


def _validate_place_ids(place_ids: list[str]) -> list[UUID]:
    valid_ids: list[UUID] = []
    for place_id in place_ids:
        try:
            valid_ids.append(UUID(place_id))
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"유효하지 않은 UUID 형식의 place_id가 포함되어 있습니다: {place_id}"
            ) from e

    return valid_ids


def _build_day_analysis_payload(
    reason: str,
    missing_categories: list[str],
    category_count: Dict[str, int],
    current_poi_count: int,
) -> dict:
    return {
        "reason": reason,
        "missing_categories": missing_categories,
        "category_distribution": category_count,
        "current_poi_count": current_poi_count,
    }


def _analyze_day_category_balance(
    category_count: Dict[str, int],
    day_index: int,
    total_days: int,
    day_label: str,
) -> tuple[list[str], str]:
    missing_categories: list[str] = []
    reason_parts: list[str] = []

    # 첫날부터 마지막 전날까지는 숙소가 필요하다고 가정
    requires_accommodation = day_index < total_days - 1
    current_accommodation = category_count.get("숙박", 0)
    if requires_accommodation and current_accommodation < 1:
        missing_categories.append("숙박")
        reason_parts.append(
            f"{day_label} 일정에 숙소가 없습니다. 밤을 보낼 숙소를 추가해주세요."
        )

    required_meals = 2
    current_meals = category_count.get("음식", 0)
    if current_meals < required_meals:
        missing_categories.append("음식")
        shortage = required_meals - current_meals
        reason_parts.append(
            f"{day_label}에 식사 장소가 {current_meals}개만 있습니다. {shortage}개 정도 더 추가하시면 좋습니다."
        )

    recommendation_reason = (
        " ".join(reason_parts)
        if reason_parts
        else f"{day_label} 일정은 균형잡혀 있습니다!"
    )

    if missing_categories:
        logger.info("%s 부족 카테고리: %s", day_label, missing_categories)
    else:
        logger.info("%s 부족 카테고리 없음", day_label)

    return missing_categories, recommendation_reason


def _calculate_center_coordinates(all_pois: list[dict]) -> tuple[float, float]:
    if not all_pois:
        raise ValueError("중심 좌표를 계산할 POI가 없습니다.")

    latitudes = [poi["latitude"] for poi in all_pois]
    longitudes = [poi["longitude"] for poi in all_pois]
    center_lat = sum(latitudes) / len(latitudes)
    center_lng = sum(longitudes) / len(longitudes)
    logger.info("중심 좌표: (%f, %f)", center_lat, center_lng)
    return center_lat, center_lng


def _recommend_places(db, center_lat: float, center_lng: float, category: str):
    logger.info("'%s' 카테고리 장소 추천 중...", category)
    place_service = PlaceService(db)
    recommendations = place_service.get_closest_places(
        latitude=center_lat,
        longitude=center_lng,
        category=category,
        limit=10,
    )
    logger.info("'%s' 카테고리: %d개 추천 장소 발견", category, len(recommendations))
    return recommendations
