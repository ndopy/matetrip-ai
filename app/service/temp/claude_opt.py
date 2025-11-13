import httpx
import numpy as np
from typing import List, Dict, Tuple, Optional
from python_tsp.exact import solve_tsp_dynamic_programming
from python_tsp.heuristics import solve_tsp_simulated_annealing

from app.service.kakao_mobility_service import KakaoMobilityService
from app.common.config import kakaoMobilityConfig


class RouteOptimizationService:
    """경로 최적화 서비스 (TSP 알고리즘 사용)"""

    def __init__(self):
        self.mobility_service = KakaoMobilityService()

    async def optimize_route(
        self,
        poi_list: List[Dict],
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> Dict:
        """
        POI 리스트를 최적화합니다.

        Args:
            poi_list: [{"id": "poi-uuid", "longitude": 127.0, "latitude": 37.0}, ...]
            start_index: 시작 지점 인덱스 (None이면 최적화에 포함)
            end_index: 종료 지점 인덱스 (None이면 최적화에 포함)

        Returns:
            {
                "optimized_poi_order": [{"id": "...", "order": 0, ...}, ...],
                "total_duration": 1234,  # 총 소요시간(초)
                "total_distance": 12345  # 총 거리(미터)
            }
        """
        if len(poi_list) == 0:
            return {"optimized_poi_order": [], "total_duration": 0, "total_distance": 0}

        # 좌표 추출
        coordinates = [(poi["longitude"], poi["latitude"]) for poi in poi_list]

        # 거리 매트릭스 생성
        print(f"{len(coordinates)}개 POI의 거리 매트릭스 생성 중...")
        distance_matrix = await self.mobility_service.get_distance_matrix(coordinates)

        # TSP 알고리즘으로 최적 순서 계산
        print("🔄 경로 최적화 중...")
        optimized_indices, total_duration, total_distance = self._solve_tsp(
            distance_matrix, start_index, end_index
        )

        # 최적화된 순서로 POI 재정렬
        optimized_poi_order = []
        for order, idx in enumerate(optimized_indices):
            poi = poi_list[idx].copy()
            poi["order"] = order
            optimized_poi_order.append(poi)

        return {
            "optimized_poi_order": optimized_poi_order,
            "total_duration": total_duration,
            "total_distance": total_distance,
        }

    def _solve_tsp(
        self,
        distance_matrix: List[List[Optional[Dict]]],
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> Tuple[List[int], float, float]:
        """
        python-tsp 라이브러리를 사용하여 TSP 문제를 해결합니다.

        Args:
            distance_matrix: N×N 거리/시간 매트릭스
            start_index: 시작 지점 (고정)
            end_index: 종료 지점 (고정)

        Returns:
            (최적 경로 인덱스 리스트, 총 소요시간, 총 거리)
        """
        n = len(distance_matrix)

        if n <= 1:
            return [0] if n == 1 else [], 0, 0

        # 거리 매트릭스를 numpy array로 변환 (duration 기준)
        # None을 매우 큰 값(1e9)으로 대체
        duration_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    duration_matrix[i][j] = 0
                else:
                    route_info = distance_matrix[i][j]
                    if route_info is not None:
                        duration_matrix[i][j] = route_info["duration"]
                    else:
                        duration_matrix[i][j] = 1e9  # 경로가 없는 경우

        # TSP 해결 (20개 이하는 exact, 이상은 heuristic)
        try:
            if n <= 20:
                permutation, _ = solve_tsp_dynamic_programming(duration_matrix)
            else:
                permutation, _ = solve_tsp_simulated_annealing(duration_matrix)

        except Exception as e:
            print(f"⚠️ TSP 해결 중 오류 발생: {e}")
            # 오류 시 순차 경로 반환
            permutation = list(range(n))

        # start_index, end_index 처리
        path: List[int] = [int(x) for x in permutation]

        # 시작 지점 조정
        if start_index is not None and start_index in path:
            # start_index가 맨 앞에 오도록 회전
            start_pos = path.index(start_index)
            path = path[start_pos:] + path[:start_pos]

        # 종료 지점 조정 (시작과 같은 경우 왕복)
        if end_index is not None:
            if start_index is not None and start_index == end_index:
                # 왕복: 끝에 start_index 추가
                path = path + [start_index]
            elif end_index in path:
                # end_index가 맨 뒤에 오도록 회전
                end_pos = path.index(end_index)
                # start_index가 있으면 그 다음부터 회전
                if start_index is not None and start_index in path:
                    start_pos = path.index(start_index)
                    # start_index 이후 부분을 end_index가 마지막이 되도록 재배치
                    remaining = [x for x in path if x != start_index and x != end_index]
                    path = [start_index] + remaining + [end_index]
                else:
                    path = path[end_pos + 1 :] + path[: end_pos + 1]

        # 총 시간과 거리 계산
        total_duration: float = 0.0
        total_distance: float = 0.0

        for i in range(len(path) - 1):
            from_idx: int = path[i]
            to_idx: int = path[i + 1]

            route_info = distance_matrix[from_idx][to_idx]
            if route_info:
                total_duration += route_info["duration"]
                total_distance += route_info["distance"]
            else:
                # 경로 정보가 없으면 오류
                print(f"경로 정보 없음: {from_idx} -> {to_idx}")
                return path, float("inf"), float("inf")

        return path, total_duration, total_distance

    async def optimize_and_broadcast_to_nestjs(
        self,
        workspace_id: str,
        plan_day_id: str,
        poi_list: List[Dict],
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> Dict:
        """
        경로를 최적화하고 NestJS 서버로 브로드캐스트합니다.

        Args:
            workspace_id: 워크스페이스 ID
            plan_day_id: 일정 day ID
            poi_list: [{"id": "poi-uuid", "longitude": 127.0, "latitude": 37.0}, ...]
            start_index: 시작 지점 인덱스 (선택)
            end_index: 종료 지점 인덱스 (선택)

        Returns:
            {
                "success": True/False,
                "optimized_poi_order": [...],
                "total_duration": 1234,
                "total_distance": 12345,
                "nestjs_response": {...}
            }
        """
        # 경로 최적화
        optimization_result = await self.optimize_route(
            poi_list, start_index, end_index
        )

        # 최적화된 POI ID 리스트 추출
        optimized_poi_ids = [
            poi["id"] for poi in optimization_result["optimized_poi_order"]
        ]

        # NestJS 서버로 브로드캐스트
        nestjs_url = f"{kakaoMobilityConfig.NESTJS_SERVER_URL}/workspace/poi/optimize"
        api_key = kakaoMobilityConfig.NESTJS_API_KEY

        payload = {
            "workspaceId": workspace_id,
            "planDayId": plan_day_id,
            "poiIds": optimized_poi_ids,
        }

        if api_key:
            payload["apiKey"] = api_key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(nestjs_url, json=payload, timeout=10.0)
                response.raise_for_status()

                nestjs_response = response.json()
                print(f"✅ NestJS 브로드캐스트 성공: {nestjs_response}")

                return {
                    "success": True,
                    "optimized_poi_order": optimization_result["optimized_poi_order"],
                    "total_duration": optimization_result["total_duration"],
                    "total_distance": optimization_result["total_distance"],
                    "nestjs_response": nestjs_response,
                }

        except Exception as e:
            print(f"❌ NestJS 브로드캐스트 실패: {e}")
            return {
                "success": False,
                "optimized_poi_order": optimization_result["optimized_poi_order"],
                "total_duration": optimization_result["total_duration"],
                "total_distance": optimization_result["total_distance"],
                "error": str(e),
            }
