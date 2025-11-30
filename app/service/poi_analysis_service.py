"""POI 분석 서비스 (순수 비즈니스 로직)"""

import httpx
from typing import Dict, List
from uuid import UUID
from pydantic import ValidationError

from app.common.config import nestJSConfig
from app.common.logger import logger
from app.repository.place_repository import PlaceRepository
from app.service.place_service import PlaceService
from app.schemas.poi import PlanDayScheduledPoisGroupDto, PlanDayScheduleSummaryDto
from app.schemas.poi_analysis import (
    AnalyzePoiRequest,
    CategoryBalanceInput,
    CategoryBalanceResult,
    DayAnalysis,
    DayPoi,
    DayPoiCollection,
    DayRecommendation,
    PoiAnalysisResponse,
)
from app.schemas.place import NearbyPlaceResponse
from app.models.place import Place

BACKEND_BASE_URL = nestJSConfig.NESTJS_BACKEND_URL


class PoiAnalysisService:
    """POI 분석 서비스"""

    def __init__(self, place_repo: PlaceRepository):
        self.place_repo = place_repo

    def analyze_workspace_pois(self, request: AnalyzePoiRequest) -> PoiAnalysisResponse:
        """워크스페이스의 POI를 분석하여 부족한 카테고리 추천"""
        # 1. 메인 Backend서버에서 일정 데이터 가져오기
        plan_day_groups = self._fetch_plan_day_groups(request.workspace_id)

        # 2. 특정 일차 필터링
        if request.day_no is not None:
            plan_day_groups = self._filter_by_day(plan_day_groups, request.day_no)

        if not plan_day_groups:
            return PoiAnalysisResponse(total_days=0, daily_reports=[])

        # 3. 일차별 분석
        daily_reports: List[DayRecommendation] = self._analyze_daily_pois(
            plan_day_groups
        )

        return PoiAnalysisResponse(
            total_days=len(plan_day_groups), daily_reports=daily_reports
        )

    def _fetch_plan_day_groups(
        self, workspace_id: str
    ) -> List[PlanDayScheduledPoisGroupDto]:
        """Backend API에서 일정 데이터 조회"""
        with httpx.Client(timeout=30.0) as client:
            url = f"{BACKEND_BASE_URL}/workspace/{workspace_id}/scheduled-pois"
            logger.info(f"NestJS API 호출: {url}")
            response = client.get(url)
            response.raise_for_status()
            raw_data = response.json()

        if not isinstance(raw_data, list):
            raise ValueError("API 응답이 리스트 형식이 아닙니다")

        try:
            return [
                PlanDayScheduledPoisGroupDto.model_validate(item) for item in raw_data
            ]
        except ValidationError as e:
            raise ValueError(f"API 응답 데이터 검증 실패: {str(e)}") from e

    def _filter_by_day(
        self, groups: List[PlanDayScheduledPoisGroupDto], day_no: int
    ) -> List[PlanDayScheduledPoisGroupDto]:
        """특정 일차만 필터링"""
        return [g for g in groups if g.planDay.dayNo == day_no]

    def _analyze_daily_pois(
        self, plan_day_groups: List[PlanDayScheduledPoisGroupDto]
    ) -> List[DayRecommendation]:
        """일차별 POI 분석"""
        # Place 정보 일괄 조회
        place_map = self._build_place_map(plan_day_groups)
        total_days = len(plan_day_groups)
        daily_reports = []

        for day_idx, group in enumerate(plan_day_groups):
            collection = self._collect_day_pois(group, place_map)

            if not collection.pois:
                # 장소가 없는 경우
                analysis = DayAnalysis(
                    reason="아직 이 날짜에 추가된 장소가 없습니다. 먼저 장소를 추가해주세요.",
                    missing_categories=[],
                    category_distribution={},
                    current_poi_count=0,
                )
                daily_reports.append(
                    DayRecommendation(
                        day_no=group.planDay.dayNo,
                        plan_date=group.planDay.planDate,
                        analysis=analysis,
                        recommendations=[],
                    )
                )
                continue

            # 카테고리 균형 분석
            balance_input = CategoryBalanceInput.create(
                category_count=collection.category_count,
                day_idx=day_idx,
                total_days=total_days,
                day_label=f"{group.planDay.dayNo}일차",
            )
            balance_result: CategoryBalanceResult = self._analyze_category_balance(
                balance_input
            )

            analysis = DayAnalysis(
                reason=balance_result.reason,
                missing_categories=balance_result.missing_categories,
                category_distribution=collection.category_count,
                current_poi_count=len(collection.pois),
            )

            # 추천 생성 (첫 번째 POI 위치 기준)
            recommendations = []
            if balance_result.missing_categories and collection.pois:
                first_poi = collection.pois[0]
                recommendations = self._generate_recommendations(
                    first_poi.latitude,
                    first_poi.longitude,
                    balance_result.missing_categories,
                )

            daily_reports.append(
                DayRecommendation(
                    day_no=group.planDay.dayNo,
                    plan_date=group.planDay.planDate,
                    analysis=analysis,
                    recommendations=recommendations,
                )
            )

        return daily_reports

    def _build_place_map(
        self, plan_day_groups: List[PlanDayScheduledPoisGroupDto]
    ) -> Dict[str, Place]:
        """Place ID → Place 매핑 생성"""
        all_poi_ids = [poi.placeId for group in plan_day_groups for poi in group.pois]

        if not all_poi_ids:
            return {}

        try:
            uuid_ids = [UUID(pid) for pid in all_poi_ids]
        except (ValueError, TypeError) as e:
            raise ValueError(f"유효하지 않은 UUID: {e}") from e

        places = self.place_repo.find_by_ids(uuid_ids)
        return {str(p.id): p for p in places}

    def _collect_day_pois(
        self, group: PlanDayScheduledPoisGroupDto, place_map: Dict[str, Place]
    ) -> DayPoiCollection:
        """일차별 POI 수집 및 카테고리 집계"""
        pois: List[DayPoi] = []
        category_count: Dict[str, int] = {}

        for poi in group.pois:
            place = place_map.get(poi.placeId)
            category = place.category if place else "기타"
            category_count[category] = category_count.get(category, 0) + 1

            pois.append(
                DayPoi(
                    id=str(poi.id),
                    place_name=poi.placeName,
                    category=category,
                    latitude=poi.latitude,
                    longitude=poi.longitude,
                )
            )

        return DayPoiCollection(pois=pois, category_count=category_count)

    def _analyze_category_balance(
        self, input_dto: CategoryBalanceInput
    ) -> CategoryBalanceResult:
        """카테고리 균형 분석"""
        missing = []
        reasons = []

        # 숙박 체크 (마지막 날 제외)
        if (
            input_dto.day_idx < input_dto.total_days - 1
            and input_dto.category_count.get("숙박", 0) < 1
        ):
            missing.append("숙박")
            reasons.append(
                f"{input_dto.day_label} 일정에 숙소가 없습니다. 밤을 보낼 숙소를 추가해주세요."
            )

        # 식사 체크
        required_meals = 2
        current_meals = input_dto.category_count.get("음식", 0)
        if current_meals < required_meals:
            missing.append("음식")
            shortage = required_meals - current_meals
            total_pois = sum(input_dto.category_count.values())
            reasons.append(
                f"{input_dto.day_label}에 식사 장소(음식 카테고리)가 {current_meals}개만 있습니다. "
                f"(전체 장소 {total_pois}개 중) {shortage}개 정도 더 추가하시면 좋습니다."
            )

        reason = (
            " ".join(reasons)
            if reasons
            else f"{input_dto.day_label} 일정은 균형잡혀 있습니다!"
        )
        return CategoryBalanceResult(missing_categories=missing, reason=reason)

    def _generate_recommendations(
        self, center_lat: float, center_lng: float, missing_categories: List[str]
    ) -> List[NearbyPlaceResponse]:
        """부족한 카테고리별 장소 추천"""
        recommendations = []
        place_service = PlaceService(self.place_repo.session)

        # 최대 2개 카테고리, 카테고리당 5개
        for category in missing_categories[:2]:
            places = place_service.get_closest_places(
                latitude=center_lat,
                longitude=center_lng,
                category=category,
                limit=5,
            )
            recommendations.extend(places)

        return recommendations
