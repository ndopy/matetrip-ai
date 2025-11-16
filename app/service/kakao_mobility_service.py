import logging
import httpx
import asyncio
import time
from typing import List, Optional, Tuple
from app.common.config import kakaoMobilityConfig
from app.schemas.routes import Coordinate, RouteSummary

logger = logging.getLogger(__name__)


class KakaoMobilityService:
    """카카오 모빌리티 API를 사용한 경로 조회 서비스"""

    def __init__(self):
        self.api_key = kakaoMobilityConfig.KAKAO_MOBILITY_API_KEY
        self.directions_url = kakaoMobilityConfig.KAKAO_MOBILITY_DIRECTIONS_URL

    # 참고 : https://developers.kakaomobility.com/docs/navi-api/waypoints/#response
    async def get_route_info(
        self,
        origin_longitude: float,
        origin_latitude: float,
        destination_longitude: float,
        destination_latitude: float,
        waypoints: List[Tuple[float, float]] = [],
        priority: str = "RECOMMEND",
    ) -> Optional[RouteSummary]:
        """
        두 지점 간의 경로 정보를 조회합니다.

        Args:
            origin_lng: 출발지 경도
            origin_lat: 출발지 위도
            destination_lng: 도착지 경도
            destination_lat: 도착지 위도
            waypoints: 경유지 좌표 리스트 [(경도, 위도), ...]
            priority: 경로 우선순위 (RECOMMEND, TIME, DISTANCE)

        Returns:
            경로 요약 객체 (duration: 소요시간(초), distance: 거리(미터))
        """
        headers = {
            "Authorization": f"KakaoAK {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "origin": {"x": str(origin_longitude), "y": str(origin_latitude)},
            "destination": {
                "x": str(destination_longitude),
                "y": str(destination_latitude),
            },
            "priority": priority,
        }

        if waypoints:
            payload["waypoints"] = [
                {"x": str(lon), "y": str(lat)} for lon, lat in waypoints
            ]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.directions_url, headers=headers, json=payload
                )

                if response.status_code != 200:
                    logger.error(
                        f"Kakao Mobility API Error: {response.status_code} - {response.text}"
                    )
                    return None

                data = response.json()

                # 첫 번째 경로의 요약 정보 추출
                if data.get("routes") and len(data["routes"]) > 0:
                    summary = data["routes"][0]["summary"]
                    return RouteSummary(
                        duration=summary["duration"],
                        distance=summary["distance"],
                        origin=Coordinate(
                            longitude=origin_longitude, latitude=origin_latitude
                        ),
                        destination=Coordinate(
                            longitude=destination_longitude,
                            latitude=destination_latitude,
                        ),
                    )

                return None

        except Exception as e:
            print(f"Kakao Mobility API Exception: {e}")
            return None

    async def get_distance_matrix(
        self, coordinates: List[Tuple[float, float]], priority: str = "RECOMMEND"
    ) -> List[List[Optional[RouteSummary]]]:
        """
        여러 좌표 간의 거리/시간 매트릭스를 생성합니다.

        Args:
            coordinates: [(경도, 위도), ...] 형식의 좌표 리스트
            priority: 경로 우선순위

        Returns:
            NxN 매트릭스 (각 셀은 RouteSummary 또는 None)
        """
        print(
            f"[get_distance_matrix] Starting to build distance matrix for {len(coordinates)} POIs..."
        )
        start_time = time.time()
        n = len(coordinates)
        matrix: List[List[Optional[RouteSummary]]] = [
            [None for _ in range(n)] for _ in range(n)
        ]

        # 비동기로 모든 경로 조회 (대각선 제외)
        tasks = []
        for i in range(n):
            for j in range(n):
                if i != j:  # 같은 지점은 제외
                    tasks.append(
                        self._get_route_with_indices(
                            i,
                            j,
                            coordinates[i][0],
                            coordinates[i][1],
                            coordinates[j][0],
                            coordinates[j][1],
                            priority,
                        )
                    )

        # 모든 API 호출 병렬 실행 (하나라도 실패하면 예외 전파)
        try:
            results = await asyncio.gather(*tasks)
        except Exception as exc:
            logger.exception(f"Kakao Mobility matrix task 실패: {exc}")
            raise

        end_time = time.time()
        print(
            f"[get_distance_matrix] All Kakao API calls finished in {end_time - start_time:.2f} seconds."
        )
        # 결과를 매트릭스에 채우기
        for i, j, route_info in results:
            matrix[i][j] = route_info

        return matrix

    async def _get_route_with_indices(
        self,
        i: int,
        j: int,
        origin_longitude: float,
        origin_latitude: float,
        destination_longitude: float,
        destination_latitude: float,
        priority: str,
    ) -> Tuple[int, int, Optional[RouteSummary]]:
        """
        인덱스와 함께 경로 정보를 반환하는 헬퍼 함수
        """
        route_info = await self.get_route_info(
            origin_longitude,
            origin_latitude,
            destination_longitude,
            destination_latitude,
            [],  # waypoints가 없는 경우 빈 리스트 전달
            priority,
        )
        return (i, j, route_info)

    async def get_duration_matrix_only(
        self, coordinates: List[Tuple[float, float]], priority: str = "RECOMMEND"
    ) -> List[List[Optional[float]]]:
        """
        거리 매트릭스에서 소요시간만 추출한 간단한 매트릭스 반환

        Args:
            coordinates: [(경도, 위도), ...] 형식의 좌표 리스트
            priority: 경로 우선순위

        Returns:
            N×N 매트릭스 (각 셀은 소요시간(초) 또는 None)
        """
        distance_matrix = await self.get_distance_matrix(coordinates, priority)

        duration_matrix = []
        for row in distance_matrix:
            duration_row = [cell.duration if cell else None for cell in row]
            duration_matrix.append(duration_row)

        return duration_matrix
