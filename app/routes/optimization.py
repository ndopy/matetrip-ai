from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.service.route_optimization_service import RouteOptimizationService

router = APIRouter(prefix="/optimization", tags=["optimization"])


class POICoordinate(BaseModel):
    """POI 좌표 정보"""
    id: str = Field(..., description="POI 고유 ID")
    longitude: float = Field(..., description="경도")
    latitude: float = Field(..., description="위도")


class OptimizeRouteRequest(BaseModel):
    """경로 최적화 요청"""
    poi_list: List[POICoordinate] = Field(..., description="최적화할 POI 리스트")
    start_index: Optional[int] = Field(None, description="시작 지점 인덱스 (고정)")
    end_index: Optional[int] = Field(None, description="종료 지점 인덱스 (고정)")


class OptimizeAndBroadcastRequest(BaseModel):
    """경로 최적화 + NestJS 브로드캐스트 요청"""
    workspace_id: str = Field(..., description="워크스페이스 ID")
    plan_day_id: str = Field(..., description="일정 day ID")
    poi_list: List[POICoordinate] = Field(..., description="최적화할 POI 리스트")
    start_index: Optional[int] = Field(None, description="시작 지점 인덱스 (고정)")
    end_index: Optional[int] = Field(None, description="종료 지점 인덱스 (고정)")


@router.post("/route")
async def optimize_route(request: OptimizeRouteRequest):
    """
    POI 리스트를 최적화합니다 (TSP 알고리즘 사용).

    - **poi_list**: 최적화할 POI 좌표 리스트
    - **start_index**: 시작 지점을 고정하려면 인덱스 지정 (선택)
    - **end_index**: 종료 지점을 고정하려면 인덱스 지정 (선택)

    Returns:
        - **optimized_poi_order**: 최적화된 POI 순서 (order 필드 포함)
        - **total_duration**: 총 소요시간(초)
        - **total_distance**: 총 거리(미터)
    """
    if len(request.poi_list) == 0:
        raise HTTPException(status_code=400, detail="POI 리스트가 비어있습니다.")

    if len(request.poi_list) == 1:
        return {
            "optimized_poi_order": [
                {**request.poi_list[0].dict(), "order": 0}
            ],
            "total_duration": 0,
            "total_distance": 0
        }

    service = RouteOptimizationService()

    # Pydantic 모델을 dict로 변환
    poi_list_dict = [poi.dict() for poi in request.poi_list]

    try:
        result = await service.optimize_route(
            poi_list_dict,
            request.start_index,
            request.end_index
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"경로 최적화 실패: {str(e)}")


@router.post("/route/broadcast")
async def optimize_and_broadcast(request: OptimizeAndBroadcastRequest):
    """
    POI 리스트를 최적화하고 NestJS 서버로 WebSocket 브로드캐스트합니다.

    - **workspace_id**: 워크스페이스 ID
    - **plan_day_id**: 일정 day ID
    - **poi_list**: 최적화할 POI 좌표 리스트
    - **start_index**: 시작 지점을 고정하려면 인덱스 지정 (선택)
    - **end_index**: 종료 지점을 고정하려면 인덱스 지정 (선택)

    Returns:
        - **success**: 브로드캐스트 성공 여부
        - **optimized_poi_order**: 최적화된 POI 순서
        - **total_duration**: 총 소요시간(초)
        - **total_distance**: 총 거리(미터)
        - **nestjs_response**: NestJS 서버 응답
    """
    if len(request.poi_list) == 0:
        raise HTTPException(status_code=400, detail="POI 리스트가 비어있습니다.")

    service = RouteOptimizationService()

    # Pydantic 모델을 dict로 변환
    poi_list_dict = [poi.dict() for poi in request.poi_list]

    try:
        result = await service.optimize_and_broadcast_to_nestjs(
            request.workspace_id,
            request.plan_day_id,
            poi_list_dict,
            request.start_index,
            request.end_index
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"경로 최적화/브로드캐스트 실패: {str(e)}")
