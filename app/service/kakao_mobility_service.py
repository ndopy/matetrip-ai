import httpx
import asyncio
from typing import List, Dict, Optional, Tuple
from app.common.config import kakaoMobilityConfig


class KakaoMobilityService:
    """카카오 모빌리티 API를 사용한 경로 조회 서비스"""

    def __init__(self):
        self.api_key = kakaoMobilityConfig.KAKAO_MOBILITY_API_KEY
        self.directions_url = kakaoMobilityConfig.KAKAO_MOBILITY_DIRECTIONS_URL

    async def get_route_info(
        self,
        origin_lng: float,
        origin_lat: float,
        destination_lng: float,
        destination_lat: float,
        priority: str = "RECOMMEND",
    ) -> Optional[Dict]:
        """
        두 지점 간의 경로 정보를 조회합니다.

        Args:
            origin_lng: 출발지 경도
            origin_lat: 출발지 위도
            destination_lng: 도착지 경도
            destination_lat: 도착지 위도
            priority: 경로 우선순위 (RECOMMEND, TIME, DISTANCE)

        Returns:
            경로 정보 딕셔너리 (duration: 소요시간(초), distance: 거리(미터))
        """
        headers = {
            "Authorization": f"KakaoAK {self.api_key}",
            "Content-Type": "application/json",
        }

        params = {
            "origin": f"{origin_lng},{origin_lat}",
            "destination": f"{destination_lng},{destination_lat}",
            "priority": priority,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.directions_url, headers=headers, params=params, timeout=10.0
                )

                if response.status_code != 200:
                    print(
                        f"Kakao Mobility API Error: {response.status_code} - {response.text}"
                    )
                    return None

                data = response.json()

                # 첫 번째 경로의 요약 정보 추출
                if data.get("routes") and len(data["routes"]) > 0:
                    summary = data["routes"][0]["summary"]
                    return {
                        "duration": summary["duration"],  # 소요시간(초)
                        "distance": summary["distance"],  # 거리(미터)
                        "origin": {"lng": origin_lng, "lat": origin_lat},
                        "destination": {"lng": destination_lng, "lat": destination_lat},
                    }

                return None

        except Exception as e:
            print(f"Kakao Mobility API Exception: {e}")
            return None

    async def get_distance_matrix(
        self, coordinates: List[Tuple[float, float]], priority: str = "RECOMMEND"
    ) -> List[List[Optional[Dict]]]:
        """
        여러 좌표 간의 거리/시간 매트릭스를 생성합니다.

        Args:
            coordinates: [(경도, 위도), ...] 형식의 좌표 리스트
            priority: 경로 우선순위

        Returns:
            N×N 매트릭스 (각 셀은 {"duration": 초, "distance": 미터} 또는 None)
        """
        n = len(coordinates)
        matrix = [[None for _ in range(n)] for _ in range(n)]

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

        # 모든 API 호출 병렬 실행
        results = await asyncio.gather(*tasks)

        # 결과를 매트릭스에 채우기
        for i, j, route_info in results:
            matrix[i][j] = route_info

        return matrix

    async def _get_route_with_indices(
        self,
        i: int,
        j: int,
        origin_lng: float,
        origin_lat: float,
        destination_lng: float,
        destination_lat: float,
        priority: str,
    ) -> Tuple[int, int, Optional[Dict]]:
        """
        인덱스와 함께 경로 정보를 반환하는 헬퍼 함수
        """
        route_info = await self.get_route_info(
            origin_lng, origin_lat, destination_lng, destination_lat, priority
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
            duration_row = [cell.get("duration") if cell else None for cell in row]
            duration_matrix.append(duration_row)

        return duration_matrix
