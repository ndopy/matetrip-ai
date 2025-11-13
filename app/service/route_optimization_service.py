import httpx
import numpy as np
from typing import Dict, List, Optional, Tuple

from python_tsp.exact import solve_tsp_dynamic_programming
from python_tsp.heuristics import solve_tsp_simulated_annealing

from app.common.config import kakaoMobilityConfig
from app.service.kakao_mobility_service import KakaoMobilityService

RouteInfo = Dict[str, float]
DistanceMatrix = List[List[Optional[RouteInfo]]]
MISSING_ROUTE_DURATION = 1e9


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
        if not poi_list:
            return {"optimized_poi_order": [], "total_duration": 0, "total_distance": 0}

        coordinates: List[Tuple[float, float]] = self._extract_coordinates(poi_list)
        print(f"{len(coordinates)}개 POI의 거리 매트릭스 생성 중...")
        distance_matrix = await self.mobility_service.get_distance_matrix(coordinates)

        print("🔄 경로 최적화 중...")
        optimized_indices, total_duration, total_distance = self._solve_tsp(
            distance_matrix, start_index, end_index
        )
        optimized_poi_order = self._build_optimized_order(poi_list, optimized_indices)

        return {
            "optimized_poi_order": optimized_poi_order,
            "total_duration": total_duration,
            "total_distance": total_distance,
        }

    def _solve_tsp(
        self,
        distance_matrix: DistanceMatrix,
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> Tuple[List[int], float, float]:
        """
        python-tsp 라이브러리를 사용하여 TSP 문제를 해결합니다.
        """
        n = len(distance_matrix)
        if n <= 1:
            return ([0] if n == 1 else []), 0.0, 0.0

        duration_matrix = self._build_duration_matrix(distance_matrix)
        permutation = self._run_tsp_solver(duration_matrix)
        path = self._apply_path_constraints(permutation, start_index, end_index)

        totals = self._accumulate_path_totals(path, distance_matrix)
        if totals is None:
            return path, float("inf"), float("inf")

        return path, totals[0], totals[1]

    def _build_duration_matrix(self, distance_matrix: DistanceMatrix) -> np.ndarray:
        n = len(distance_matrix)
        duration_matrix = np.full(
            (n, n), fill_value=MISSING_ROUTE_DURATION, dtype=float
        )
        np.fill_diagonal(duration_matrix, 0.0)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                route_info = distance_matrix[i][j]
                if route_info is not None:
                    duration_matrix[i][j] = route_info["duration"]
        return duration_matrix

    def _run_tsp_solver(self, duration_matrix: np.ndarray) -> List[int]:
        try:
            if len(duration_matrix) <= 20:
                permutation, _ = solve_tsp_dynamic_programming(duration_matrix)
            else:
                permutation, _ = solve_tsp_simulated_annealing(duration_matrix)
        except Exception as exc:  # pragma: no cover - best-effort fallback
            print(f"⚠️ TSP 해결 중 오류 발생: {exc}")
            return list(range(len(duration_matrix)))

        return [int(x) for x in permutation]

    def _apply_path_constraints(
        self, path: List[int], start_index: Optional[int], end_index: Optional[int]
    ) -> List[int]:
        rotated = self._rotate_start(path, start_index)
        return self._ensure_end(rotated, start_index, end_index)

    def _rotate_start(self, path: List[int], start_index: Optional[int]) -> List[int]:
        if start_index is None or start_index not in path:
            return path
        pivot = path.index(start_index)
        return path[pivot:] + path[:pivot]

    def _ensure_end(
        self, path: List[int], start_index: Optional[int], end_index: Optional[int]
    ) -> List[int]:
        if end_index is None or end_index not in path:
            return path

        if start_index is not None and start_index == end_index:
            return path + [start_index]

        reordered = [idx for idx in path if idx != end_index]
        reordered.append(end_index)
        return reordered

    def _accumulate_path_totals(
        self, path: List[int], distance_matrix: DistanceMatrix
    ) -> Optional[Tuple[float, float]]:
        total_duration = 0.0
        total_distance = 0.0

        for from_idx, to_idx in zip(path, path[1:]):
            route_info = distance_matrix[from_idx][to_idx]
            if not route_info:
                print(f"⚠️ 경로 정보 없음: {from_idx} -> {to_idx}")
                return None
            total_duration += route_info["duration"]
            total_distance += route_info["distance"]

        return total_duration, total_distance

    def _build_optimized_order(
        self, poi_list: List[Dict], optimized_indices: List[int]
    ) -> List[Dict]:
        optimized_poi_order = []
        for order, idx in enumerate(optimized_indices):
            poi = poi_list[idx].copy()
            poi["order"] = order
            optimized_poi_order.append(poi)
        return optimized_poi_order

    def _extract_coordinates(self, poi_list: List[Dict]) -> List[Tuple[float, float]]:
        return [(poi["longitude"], poi["latitude"]) for poi in poi_list]

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
        """
        optimization_result = await self.optimize_route(
            poi_list, start_index, end_index
        )
        optimized_poi_ids = [
            poi["id"] for poi in optimization_result["optimized_poi_order"]
        ]

        nestjs_url = f"{kakaoMobilityConfig.NESTJS_SERVER_URL}/workspace/poi/optimize"
        api_key = kakaoMobilityConfig.NESTJS_API_KEY
        payload = {
            "workspaceId": workspace_id,
            "planDayId": plan_day_id,
            "poiIds": optimized_poi_ids,
        }
        if api_key:
            payload["apiKey"] = api_key

        success, nestjs_payload = await self._post_to_nestjs(nestjs_url, payload)

        result = {
            "success": success,
            "optimized_poi_order": optimization_result["optimized_poi_order"],
            "total_duration": optimization_result["total_duration"],
            "total_distance": optimization_result["total_distance"],
        }

        if success:
            result["nestjs_response"] = nestjs_payload
        else:
            result["error"] = nestjs_payload.get("error")

        return result

    async def _post_to_nestjs(self, url: str, payload: Dict) -> Tuple[bool, Dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                nestjs_response = response.json()
                print(f"✅ NestJS 브로드캐스트 성공: {nestjs_response}")
                return True, nestjs_response
        except Exception as exc:
            print(f"❌ NestJS 브로드캐스트 실패: {exc}")
            return False, {"error": str(exc)}
