"""POI 분석 도구 (LLM 어댑터)"""

import httpx
from typing import Optional
from langchain_core.tools import tool

from app.common.logger import logger
from app.database.database import get_db_session
from app.repository.place_repository import PlaceRepository
from app.service.poi_analysis_service import PoiAnalysisService
from app.schemas.poi_analysis import AnalyzePoiRequest
from app.schemas.tool_response import ToolResult


def get_poi_tools():
    """
    [POI 분석 및 추천 도구 모음]
    현재 사용자가 일정에 추가한 장소를 분석하여 부족한 부분을 채워주는 도구입니다.
    """

    @tool
    def recommend_next_poi(workspace_id: str, day_no: Optional[int] = None):
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
        - 특정 일차만 확인해달라고 하면 day_no를 함께 넘겨 호출하세요. 일차가 명시되지 않았다면 먼저 몇 일차인지 짧게 물어본 뒤 호출하세요.

        **분석하는 내용:**
        1. 숙박 시설 부족 여부
           - 예: 2박 3일이면 숙소 2개 필요
        2. 식사 장소 부족 여부
           - 하루 2~3끼 기준으로 판단
        3. 카테고리 다양성
           - 관광지만 많고 휴식 공간이 없는지 등

        Args:
            workspace_id: 분석할 워크스페이스 ID (현재 사용자가 작업 중인 여행 계획의 고유 ID)
            day_no: 특정 일차만 보고 싶을 때 전달하는 일차 번호 (예: 1, 2, 3). None이면 전체 일정 분석

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
        1. **analysis.reason 텍스트를 절대 바꾸지 말고 그대로 복사해서 사용**하세요.
        2. **절대로 current_poi_count를 카테고리별 개수로 착각하지 마세요.**
           - current_poi_count: 해당 날짜의 전체 장소 개수
           - category_distribution: 카테고리별 개수 (예: {"음식": 0, "숙박": 1, "관광지": 2})
        3. 추천 장소는 **이름, 주소, 카테고리, 태그, 요약**만 사용하여 소개하세요.
        4. 기술적 정보(ID, 좌표, distance_km, recommended_category 등)는 절대 언급하지 마세요.
        5. 부족한 카테고리가 없으면 "현재 일정이 균형잡혀 있습니다!"라고 답변하세요.

        **올바른 답변 예시:**
        "1일차 일정에 숙소가 없습니다. 밤을 보낼 숙소를 추가해주세요.
        1일차에 식사 장소(음식 카테고리)가 0개만 있습니다. (전체 장소 3개 중) 2개 정도 더 추가하시면 좋습니다.

        현재 추가하신 장소들 중심으로 근처 추천 장소를 알려드릴게요:

        **[숙박 추천]**
        - **제주 힐링 펜션** (제주 서귀포시...)
          바다 전망, 조용한 분위기, 가족 단위 추천

        **[음식 추천]**
        - **성산 해물뚝배기** (제주 서귀포시 성산읍...)
          신선한 해산물, 현지인 맛집, 가성비 좋음"
        """
        try:
            logger.info(f"[recommend_next_poi] workspace_id={workspace_id}")
            request = AnalyzePoiRequest.create(workspace_id=workspace_id, day_no=day_no)

            with get_db_session() as db:
                place_repo = PlaceRepository(db)
                poi_service = PoiAnalysisService(place_repo)
                response = poi_service.analyze_workspace_pois(request)

            day_label = f"{day_no}일차" if day_no else "전체 일정"
            return ToolResult(
                success=True,
                data=response.model_dump(),
                message=f"{day_label} POI 분석을 완료했습니다.",
            ).model_dump()

        except httpx.HTTPStatusError as e:
            error_msg = f"NestJS API 오류: {e.response.status_code}"
            if e.response.status_code == 404:
                error_msg = (
                    "워크스페이스를 찾을 수 없습니다. workspace_id를 확인해주세요."
                )
            logger.error(f"{error_msg} - {e.response.text}")
            return ToolResult(success=False, error=error_msg).model_dump()
        except httpx.RequestError as e:
            error_msg = f"NestJS 서버에 연결할 수 없습니다: {str(e)}"
            logger.error(error_msg)
            return ToolResult(success=False, error=error_msg).model_dump()
        except Exception as e:
            error_msg = f"POI 분석 중 에러 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ToolResult(success=False, error=error_msg).model_dump()

    return [recommend_next_poi]
