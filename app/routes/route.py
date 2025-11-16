from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import time
from typing import List, Optional

from langchain_core.tools import tool

from app.schemas.routes import (
    OptimizeRouteRequest,
    POICoordinate,
    RouteOptimizeResponse,
)
from app.service.route_optimization_service import RouteOptimizationService

router = APIRouter(prefix="/optimization", tags=["optimization"])


service = RouteOptimizationService()

@tool
@router.post("/route", response_model=RouteOptimizeResponse)
async def optimize_route(request: OptimizeRouteRequest):
    """
    POI 리스트를 최적화 (TSP 알고리즘 사용).

    - poi_list: 최적화할 POI 좌표 리스트
    - start_index: 시작 지점을 고정하려면 인덱스 지정 (선택)
    - end_index: 종료 지점을 고정하려면 인덱스 지정 (선택)

    Returns:
        RouteOptimizeResponse
    """
    start_time = time.time()
    if len(request.poi_list) == 1:
        single_poi = request.poi_list[0]
        return RouteOptimizeResponse(
            ids=[single_poi.id],
            routes=[],
            total_duration=0.0,
            total_distance=0.0,
        )

    try:
        print("[optimize_route] Calling optimization service...")
        result = await service.optimize_route(
            request.poi_list, request.start_index, request.end_index
        )
        end_time = time.time()
        print(f"[optimize_route] Total request processing time: {end_time - start_time:.2f} seconds")
        return result

    except Exception as e:
        end_time = time.time()
        print(f"[optimize_route] Exception after {end_time - start_time:.2f} seconds: {e}")
        raise HTTPException(status_code=500, detail=f"경로 최적화 실패: {str(e)}")
