"""
경로 최적화 서비스 단위 테스트

테스트 실행:
    pytest test/test_route_optimization.py -v

Mock 테스트만 실행:
    pytest test/test_route_optimization.py -v -m "not integration"

통합 테스트만 실행 (실제 API 호출):
    pytest test/test_route_optimization.py -v -m integration
"""

import logging
import pytest
from unittest.mock import AsyncMock, patch
from typing import List, Optional

from app.schemas.routes import Coordinate, POICoordinate, RouteSummary
from app.service.route_optimization_service import RouteOptimizationService
from app.service.kakao_mobility_service import KakaoMobilityService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def build_poi_coordinates(data: List[dict]) -> List[POICoordinate]:
    """Pydantic POI 객체 리스트 생성 헬퍼."""
    return [POICoordinate(**entry) for entry in data]


# ============================================================================
# Mock 데이터 기반 단위 테스트 (API 호출 없음)
# ============================================================================


def create_mock_distance_matrix(n: int) -> List[List[Optional[RouteSummary]]]:
    """
    테스트용 거리 매트릭스 생성

    Args:
        n: POI 개수

    Returns:
        N×N 거리 매트릭스 (대각선은 None)
    """
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(None)  # 같은 지점은 None
            else:
                # 거리와 시간은 인덱스 차이에 비례하도록 설정
                distance = abs(i - j) * 1000  # 미터
                duration = abs(i - j) * 300  # 초 (5분)
                origin = Coordinate(
                    longitude=127.0 + i * 0.01, latitude=37.5 + i * 0.01
                )
                destination = Coordinate(
                    longitude=127.0 + j * 0.01, latitude=37.5 + j * 0.01
                )
                row.append(
                    RouteSummary(
                        duration=duration,
                        distance=distance,
                        origin=origin,
                        destination=destination,
                    )
                )
        matrix.append(row)
    return matrix


@pytest.mark.asyncio
async def test_optimize_route_with_3_pois():
    """3개 POI 최적화 테스트"""
    # Given: 3개의 POI 데이터
    poi_list = build_poi_coordinates(
        [
            {"id": "poi-a", "longitude": 127.0, "latitude": 37.5},
            {"id": "poi-b", "longitude": 127.01, "latitude": 37.51},
            {"id": "poi-c", "longitude": 127.02, "latitude": 37.52},
        ]
    )

    # Mock distance matrix (3x3)
    mock_matrix = create_mock_distance_matrix(3)

    # When: RouteOptimizationService의 optimize_route 호출 (mock 사용)
    service = RouteOptimizationService()

    with patch.object(
        service.mobility_service,
        "get_distance_matrix",
        new_callable=AsyncMock,
        return_value=mock_matrix,
    ):
        result = await service.optimize_route(poi_list)

    # Then: 결과 검증
    assert len(result.ids) == 3
    assert set(result.ids) == {poi.id for poi in poi_list}
    assert result.total_duration > 0
    assert result.total_distance > 0
    assert len(result.routes) == len(result.ids) - 1

    for route in result.routes:
        assert route.duration > 0
        assert route.distance > 0

    logger.info(f"✅ 3개 POI 최적화 결과: {result.ids}")
    logger.info(
        f"   총 시간: {result.total_duration}초, 총 거리: {result.total_distance}m"
    )


@pytest.mark.asyncio
async def test_optimize_route_with_fixed_start():
    """시작 지점 고정 최적화 테스트"""
    # Given: 4개의 POI, 0번을 시작 지점으로 고정
    poi_list = build_poi_coordinates(
        [
            {"id": "start", "longitude": 127.0, "latitude": 37.5},
            {"id": "poi-1", "longitude": 127.01, "latitude": 37.51},
            {"id": "poi-2", "longitude": 127.02, "latitude": 37.52},
            {"id": "poi-3", "longitude": 127.03, "latitude": 37.53},
        ]
    )

    mock_matrix = create_mock_distance_matrix(4)

    # When: 시작 지점을 0번으로 고정
    service = RouteOptimizationService()

    with patch.object(
        service.mobility_service,
        "get_distance_matrix",
        new_callable=AsyncMock,
        return_value=mock_matrix,
    ):
        result = await service.optimize_route(poi_list, start_index=0)

    # Then: 첫 번째 POI가 "start"인지 확인
    assert result.ids[0] == "start"
    assert len(result.routes) == len(result.ids) - 1

    logger.info(f"✅ 시작 지점 고정 최적화: {result.ids}")


@pytest.mark.asyncio
async def test_optimize_route_with_fixed_start_and_end():
    """시작과 종료 지점 고정 최적화 테스트 (왕복)"""
    # Given: 5개의 POI, 0번을 시작이자 종료 지점으로 고정
    poi_list = build_poi_coordinates(
        [
            {"id": "hotel", "longitude": 127.0, "latitude": 37.5},
            {"id": "restaurant", "longitude": 127.01, "latitude": 37.51},
            {"id": "museum", "longitude": 127.02, "latitude": 37.52},
            {"id": "cafe", "longitude": 127.03, "latitude": 37.53},
            {"id": "park", "longitude": 127.04, "latitude": 37.54},
        ]
    )

    mock_matrix = create_mock_distance_matrix(5)

    # When: 시작과 종료를 모두 0번으로 고정 (왕복)
    service = RouteOptimizationService()

    with patch.object(
        service.mobility_service,
        "get_distance_matrix",
        new_callable=AsyncMock,
        return_value=mock_matrix,
    ):
        result = await service.optimize_route(poi_list, start_index=0, end_index=0)

    # Then: 첫 번째와 마지막 POI가 모두 "hotel"인지 확인
    assert result.ids[0] == "hotel"
    assert result.ids[-1] == "hotel"

    logger.info(f"✅ 왕복 최적화: {result.ids}")


@pytest.mark.asyncio
async def test_optimize_empty_poi_list():
    """빈 POI 리스트 처리 테스트"""
    # Given: 빈 리스트
    poi_list: List[POICoordinate] = []

    # When
    service = RouteOptimizationService()
    result = await service.optimize_route(poi_list)

    # Then
    assert result.ids == []
    assert result.routes == []
    assert result.total_duration == 0
    assert result.total_distance == 0

    logger.info("✅ 빈 POI 리스트 처리 성공")


@pytest.mark.asyncio
async def test_optimize_single_poi():
    """단일 POI 처리 테스트"""
    # Given: 1개의 POI
    poi_list = build_poi_coordinates(
        [{"id": "only-one", "longitude": 127.0, "latitude": 37.5}]
    )

    # When
    service = RouteOptimizationService()
    mock_matrix = create_mock_distance_matrix(1)

    with patch.object(
        service.mobility_service,
        "get_distance_matrix",
        new_callable=AsyncMock,
        return_value=mock_matrix,
    ):
        result = await service.optimize_route(poi_list)

    # Then
    assert len(result.ids) == 1
    assert result.ids[0] == "only-one"
    assert result.routes == []
    assert result.total_duration == 0
    assert result.total_distance == 0

    logger.info("✅ 단일 POI 처리 성공")


@pytest.mark.asyncio
async def test_tsp_brute_force_algorithm():
    """TSP 완전 탐색 알고리즘 테스트 (8개 이하)"""
    # Given: 5개 POI (완전 탐색 사용)
    n = 5
    poi_list = build_poi_coordinates(
        [
            {
                "id": f"poi-{i}",
                "longitude": 127.0 + i * 0.01,
                "latitude": 37.5 + i * 0.01,
            }
            for i in range(n)
        ]
    )

    mock_matrix = create_mock_distance_matrix(n)

    # When
    service = RouteOptimizationService()

    with patch.object(
        service.mobility_service,
        "get_distance_matrix",
        new_callable=AsyncMock,
        return_value=mock_matrix,
    ):
        result = await service.optimize_route(poi_list)

    # Then: 모든 POI가 포함되어야 함
    result_ids = set(result.ids)
    expected_ids = {poi.id for poi in poi_list}
    assert result_ids == expected_ids

    logger.info(f"TSP 완전 탐색 (5개): {result.ids}")


@pytest.mark.asyncio
async def test_tsp_greedy_algorithm():
    """TSP Greedy 알고리즘 테스트 (9개 이상)"""
    # Given: 10개 POI (Greedy 사용)
    n = 10
    poi_list = build_poi_coordinates(
        [
            {
                "id": f"poi-{i}",
                "longitude": 127.0 + i * 0.01,
                "latitude": 37.5 + i * 0.01,
            }
            for i in range(n)
        ]
    )

    mock_matrix = create_mock_distance_matrix(n)

    # When
    service = RouteOptimizationService()

    with patch.object(
        service.mobility_service,
        "get_distance_matrix",
        new_callable=AsyncMock,
        return_value=mock_matrix,
    ):
        result = await service.optimize_route(poi_list)

    # Then: 모든 POI가 포함되어야 함
    result_ids = set(result.ids)
    expected_ids = {poi.id for poi in poi_list}
    assert result_ids == expected_ids

    logger.info(f"TSP Greedy (10개): {result.ids}")


@pytest.mark.asyncio
async def test_calculate_path_cost():
    """경로 비용 계산 테스트"""
    # Given
    service = RouteOptimizationService()
    mock_matrix = create_mock_distance_matrix(4)

    # When: 0 -> 1 -> 2 -> 3 경로의 비용 계산
    path = [0, 1, 2, 3]
    total_duration, total_distance = service._calculate_path_cost(mock_matrix, path)

    # Then
    # 0->1: 300초, 1000m
    # 1->2: 300초, 1000m
    # 2->3: 300초, 1000m
    # 합계: 900초, 3000m
    assert total_duration == 900
    assert total_distance == 3000

    logger.info(f"✅ 경로 비용 계산: {total_duration}초, {total_distance}m")


# ============================================================================
# 통합 테스트 (실제 카카오 모빌리티 API 호출)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_optimize_route():
    """
    실제 카카오 모빌리티 API를 사용한 통합 테스트

    주의: 이 테스트는 실제 API를 호출하므로:
    - .env에 KAKAO_MOBILITY_API_KEY가 설정되어 있어야 함
    - API 호출 제한이 있으므로 신중하게 실행
    """
    # Given: 서울 강남 지역의 실제 좌표
    poi_list = build_poi_coordinates(
        [
            {"id": "gangnam", "longitude": 127.0276, "latitude": 37.4979},
            {"id": "coex", "longitude": 127.0594, "latitude": 37.5126},
            {"id": "bongeunsa", "longitude": 127.0566, "latitude": 37.5147},
        ]
    )

    # When: 실제 API 호출
    service = RouteOptimizationService()
    result = await service.optimize_route(poi_list)

    # Then
    assert len(result.ids) == 3
    assert result.total_duration > 0
    assert result.total_distance > 0

    logger.info("=" * 60)
    logger.info("🌐 실제 API 테스트 결과:")
    logger.info(f"   최적 경로: {result.ids}")
    logger.info(
        f"   총 시간: {result.total_duration}초 ({result.total_duration/60:.1f}분)"
    )
    logger.info(
        f"   총 거리: {result.total_distance}m ({result.total_distance/1000:.2f}km)"
    )
    logger.info("=" * 60)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_distance_matrix():
    """실제 API로 거리 매트릭스 생성 테스트"""
    # Given: 3개의 실제 좌표
    coordinates = [
        (127.0276, 37.4979),  # 강남역
        (127.0594, 37.5126),  # 코엑스
        (127.0566, 37.5147),  # 봉은사
    ]

    # When
    service = KakaoMobilityService()
    matrix = await service.get_distance_matrix(coordinates)

    # Then
    assert len(matrix) == 3
    assert len(matrix[0]) == 3

    # 대각선은 None이어야 함
    assert matrix[0][0] is None
    assert matrix[1][1] is None
    assert matrix[2][2] is None

    # 나머지는 유효한 값이어야 함
    assert matrix[0][1] is not None
    assert matrix[0][1].duration > 0
    assert matrix[0][1].distance > 0

    logger.info("=" * 60)
    logger.info("🌐 거리 매트릭스 생성 성공:")
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            summary = matrix[i][j]
            if summary:
                logger.info(f"   [{i}→{j}] {summary.duration}초, {summary.distance}m")
    logger.info("=" * 60)


if __name__ == "__main__":
    # pytest 없이 직접 실행
    import asyncio

    print("\n" + "=" * 60)
    print("단위 테스트 실행 (Mock 데이터)")
    print("=" * 60)

    asyncio.run(test_optimize_route_with_3_pois())
    asyncio.run(test_optimize_route_with_fixed_start())
    asyncio.run(test_optimize_route_with_fixed_start_and_end())
    asyncio.run(test_optimize_empty_poi_list())
    asyncio.run(test_optimize_single_poi())
    asyncio.run(test_tsp_brute_force_algorithm())
    asyncio.run(test_tsp_greedy_algorithm())
    asyncio.run(test_calculate_path_cost())

    print("\n" + "=" * 60)
    print("✅ 모든 단위 테스트 통과!")
    print("=" * 60)
