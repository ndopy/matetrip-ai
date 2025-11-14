import numpy as np
from typing import Dict, List, Optional, Tuple

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from app.schemas.routes import (
    POICoordinate,
    RouteOptimizeResponse,
    RouteSummary,
)
from app.service.kakao_mobility_service import KakaoMobilityService

DistanceMatrix = List[List[Optional[RouteSummary]]]
MISSING_ROUTE_DURATION = 1e9
SCALE_FACTOR = 1000


class RouteOptimizationService:
    """경로 최적화 서비스 (TSP 알고리즘 사용)"""

    def __init__(self):
        self.mobility_service = KakaoMobilityService()

    async def optimize_route(
        self,
        poi_list: List[POICoordinate],
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> RouteOptimizeResponse:
        """
        POI 리스트를 최적화합니다.

        Args:
            poi_list: [{"id": "poi-uuid", "longitude": 127.0, "latitude": 37.0}, ...]
            start_index: 시작 지점 인덱스 (None이면 최적화에 포함)
            end_index: 종료 지점 인덱스 (None이면 최적화에 포함)

        Returns:
            Optimized POI 순서 (ids), 최적 경로를 구성하는 구간 요약들 (순서대로), total duration/distance
        """
        coordinates = self._extract_coordinates(poi_list)
        print(f"Creating distance matrix for {len(coordinates)} POIs...")

        # 여러 좌표 간의 거리/시간 매트릭스 생성
        distance_matrix = await self.mobility_service.get_distance_matrix(coordinates)

        print("Optimizing route with OR-Tools...")
        # OR-Tools에게 tsp 맡기기
        optimized_indices, total_duration, total_distance, route_summaries = (
            self._solve_tsp_with_ortools(distance_matrix, start_index, end_index)
        )
        print("Optimizing finished")

        optimized_ids = [poi_list[idx].id for idx in optimized_indices]

        return RouteOptimizeResponse(
            ids=optimized_ids,
            routes=route_summaries,
            total_duration=total_duration,
            total_distance=total_distance,
        )

    def _solve_tsp_with_ortools(
        self,
        distance_matrix: DistanceMatrix,
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> Tuple[List[int], float, float, List[RouteSummary]]:
        """
        OR-Tools 라이브러리를 사용하여 TSP 문제를 해결

        Args:
            distance_matrix: Distance/duration 정보 between POIs
            start_index: 시작 point (default: 0)
            end_index: 끝 point (optional, if None: open tour)

        Returns:
            (optimal path indices, total duration, total distance, route summaries)
        """
        n = len(distance_matrix)
        if n <= 1:
            return ([0] if n == 1 else []), 0.0, 0.0, []

        duration_matrix = self._build_duration_matrix(distance_matrix)

        manager = pywrapcp.RoutingIndexManager(n, 1, start_index or 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(duration_matrix[from_node][to_node] * SCALE_FACTOR)

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 30

        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            print("OR-Tools could not find solution. Returning sequential path.")
            path = list(range(n))
            totals = self._accumulate_path_totals(path, distance_matrix)
            if totals is None:
                return path, float("inf"), float("inf"), []
            return path, totals[0], totals[1], totals[2]

        path = self._extract_path_from_solution(manager, routing, solution)

        # Handle end_index constraint
        if end_index is not None:
            if end_index == start_index or end_index == (start_index or 0):
                # Round trip: add start point at the end
                path = path + [path[0]]
            elif end_index in path:
                # Move end_index to the end of the path
                path = [idx for idx in path if idx != end_index] + [end_index]

        totals = self._accumulate_path_totals(path, distance_matrix)
        if totals is None:
            return path, float("inf"), float("inf"), []

        total_duration, total_distance, route_summaries = totals
        return path, total_duration, total_distance, route_summaries

    def _extract_path_from_solution(
        self,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        solution,
    ) -> List[int]:
        """Extract path from OR-Tools solution."""
        path = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            path.append(node)
            index = solution.Value(routing.NextVar(index))
        return path

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
                    duration_matrix[i][j] = route_info.duration

        return duration_matrix

    def _accumulate_path_totals(
        self, path: List[int], distance_matrix: DistanceMatrix
    ) -> Optional[Tuple[float, float, List[RouteSummary]]]:
        """Calculate total duration, distance, and summaries for a path."""
        total_duration = 0.0
        total_distance = 0.0
        route_summaries: List[RouteSummary] = []

        for from_idx, to_idx in zip(path, path[1:]):
            route_info = distance_matrix[from_idx][to_idx]
            if not route_info:
                print(f"Missing route info: {from_idx} -> {to_idx}")
                return None
            total_duration += route_info.duration
            total_distance += route_info.distance
            route_summaries.append(route_info)

        return total_duration, total_distance, route_summaries

    def _calculate_path_cost(
        self, distance_matrix: DistanceMatrix, path: List[int]
    ) -> Tuple[float, float]:
        """특정 path의 비용 계산 (duration, distance)"""
        totals = self._accumulate_path_totals(path, distance_matrix)
        if totals is None:
            return float("inf"), float("inf")
        return totals[0], totals[1]

    def _extract_coordinates(
        self, poi_list: List[POICoordinate]
    ) -> List[Tuple[float, float]]:
        """Extract coordinates from POI list."""
        return [(poi.longitude, poi.latitude) for poi in poi_list]

    async def optimize_routes(
        self,
        poi_list: List[POICoordinate],
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> Dict:
        """
        Optimize route and return results directly (no external API call).

        Args:
            poi_list: List of POIs to optimize
            start_index: Start point index
            end_index: End point index

        Returns:
            Optimization results in dictionary format
        """
        optimization_result = await self.optimize_route(
            poi_list, start_index, end_index
        )

        result = {
            "optimized_poi_order": optimization_result.ids,
            "routes": [route.model_dump() for route in optimization_result.routes],
            "total_duration": optimization_result.total_duration,
            "total_distance": optimization_result.total_distance,
        }

        return result
