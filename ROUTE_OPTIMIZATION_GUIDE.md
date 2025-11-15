# 경로 최적화 API 가이드

카카오 모빌리티 API를 사용한 POI 경로 최적화 시스템입니다.

## 📋 개요

이 시스템은 다음과 같은 기능을 제공합니다:

1. **카카오 모빌리티 API 연동**: 실제 도로 기반 경로 시간/거리 계산
2. **TSP 알고리즘**: 외판원 문제(Traveling Salesman Problem) 해결로 최적 경로 계산
3. **NestJS 연동**: 최적화된 결과를 WebSocket으로 실시간 브로드캐스트

## 🔧 환경 설정

### 1. 카카오 모빌리티 API 키 발급

1. [Kakao Developers](https://developers.kakao.com/)에서 애플리케이션 생성
2. "제품 설정 > Kakao 모빌리티" 메뉴에서 API 활성화
3. REST API 키 복사

### 2. .env 파일 설정

`.env` 파일에 다음 환경 변수를 추가하세요:

```bash
# Kakao Mobility API Configuration
KAKAO_MOBILITY_API_KEY=your-kakao-mobility-api-key-here

# NestJS Backend Server (POI 최적화 브로드캐스트용)
NESTJS_SERVER_URL=http://localhost:3000
NESTJS_API_KEY=your-nestjs-api-key-here
```

## 🚀 사용 방법

### API 엔드포인트

#### 1. 경로 최적화만 수행 (브로드캐스트 없음)

**POST** `/optimization/route`

**Request Body:**

```json
{
  "poi_list": [
    {
      "id": "poi-uuid-1",
      "longitude": 127.0276,
      "latitude": 37.4979
    },
    {
      "id": "poi-uuid-2",
      "longitude": 127.03,
      "latitude": 37.5
    },
    {
      "id": "poi-uuid-3",
      "longitude": 127.025,
      "latitude": 37.495
    }
  ],
  "start_index": 0, // 선택: 시작 지점 고정 (0번 인덱스)
  "end_index": null // 선택: 종료 지점 고정
}
```

**Response:**

```json
{
  "optimized_poi_order": [
    {
      "id": "poi-uuid-1",
      "longitude": 127.0276,
      "latitude": 37.4979,
      "order": 0
    },
    {
      "id": "poi-uuid-3",
      "longitude": 127.025,
      "latitude": 37.495,
      "order": 1
    },
    {
      "id": "poi-uuid-2",
      "longitude": 127.03,
      "latitude": 37.5,
      "order": 2
    }
  ],
  "total_duration": 1234, // 총 소요시간(초)
  "total_distance": 12345 // 총 거리(미터)
}
```

#### 2. 경로 최적화 + NestJS 브로드캐스트

**POST** `/optimization/route/broadcast`

**Request Body:**

```json
{
  "workspace_id": "workspace-uuid-123",
  "plan_day_id": "plan-day-uuid-456",
  "poi_list": [
    {
      "id": "poi-uuid-1",
      "longitude": 127.0276,
      "latitude": 37.4979
    },
    {
      "id": "poi-uuid-2",
      "longitude": 127.03,
      "latitude": 37.5
    }
  ],
  "start_index": null,
  "end_index": null
}
```

**Response:**

```json
{
  "success": true,
  "optimized_poi_order": [...],
  "total_duration": 1234,
  "total_distance": 12345,
  "nestjs_response": {
    "success": true,
    "message": "POI order optimized and broadcasted successfully"
  }
}
```

## 📝 Python 클라이언트 예제

### 간단한 경로 최적화

```python
import httpx
import asyncio

async def optimize_route():
    """간단한 경로 최적화 예제"""
    url = "http://localhost:8000/optimization/route"

    payload = {
        "poi_list": [
            {"id": "poi-1", "longitude": 127.0276, "latitude": 37.4979},
            {"id": "poi-2", "longitude": 127.0300, "latitude": 37.5000},
            {"id": "poi-3", "longitude": 127.0250, "latitude": 37.4950},
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30.0)
        result = response.json()

        print("✅ 최적화 완료!")
        print(f"총 소요시간: {result['total_duration']}초")
        print(f"총 거리: {result['total_distance']}미터")
        print(f"최적 순서: {[poi['id'] for poi in result['optimized_poi_order']]}")

        return result

# 실행
asyncio.run(optimize_route())
```

### 시작/종료 지점 고정

```python
async def optimize_route_with_fixed_points():
    """시작과 종료 지점을 고정한 경로 최적화"""
    url = "http://localhost:8000/optimization/route"

    payload = {
        "poi_list": [
            {"id": "hotel", "longitude": 127.0276, "latitude": 37.4979},      # 0번 인덱스
            {"id": "restaurant", "longitude": 127.0300, "latitude": 37.5000}, # 1번 인덱스
            {"id": "museum", "longitude": 127.0250, "latitude": 37.4950},     # 2번 인덱스
            {"id": "cafe", "longitude": 127.0280, "latitude": 37.4960},       # 3번 인덱스
        ],
        "start_index": 0,  # 호텔에서 시작 (고정)
        "end_index": 0     # 호텔로 돌아옴 (고정)
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30.0)
        result = response.json()

        print("✅ 최적화 완료!")
        print(f"경로: {' → '.join([poi['id'] for poi in result['optimized_poi_order']])}")

        return result

# 실행
asyncio.run(optimize_route_with_fixed_points())
```

### 최적화 + NestJS 브로드캐스트

```python
async def optimize_and_broadcast():
    """경로 최적화 후 NestJS로 실시간 브로드캐스트"""
    url = "http://localhost:8000/optimization/route/broadcast"

    payload = {
        "workspace_id": "workspace-uuid-123",
        "plan_day_id": "plan-day-uuid-456",
        "poi_list": [
            {"id": "poi-1", "longitude": 127.0276, "latitude": 37.4979},
            {"id": "poi-2", "longitude": 127.0300, "latitude": 37.5000},
            {"id": "poi-3", "longitude": 127.0250, "latitude": 37.4950},
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30.0)
        result = response.json()

        if result['success']:
            print("✅ 최적화 및 브로드캐스트 성공!")
            print(f"WebSocket으로 모든 클라이언트에게 전송 완료")
        else:
            print(f"❌ 브로드캐스트 실패: {result.get('error')}")

        return result

# 실행
asyncio.run(optimize_and_broadcast())
```

## 🧠 알고리즘 설명

### TSP (Traveling Salesman Problem)

외판원 문제는 여러 도시를 모두 방문하고 돌아오는 최단 경로를 찾는 최적화 문제입니다.

**구현 방식:**

1. **소규모 (8개 이하)**: 완전 탐색 (Brute Force)

   - 모든 순열을 탐색하여 최적해 보장
   - 시간 복잡도: O(n!)

2. **대규모 (9개 이상)**: 탐욕 알고리즘 (Greedy)
   - 현재 위치에서 가장 가까운 미방문 지점 선택
   - 시간 복잡도: O(n²)
   - 근사해 제공 (최적해 보장 안 됨)

### 카카오 모빌리티 API

- **거리 매트릭스 생성**: N개 POI에 대해 N×N 매트릭스 생성
- **비동기 병렬 호출**: `asyncio.gather()`로 모든 API 호출 동시 실행
- **실제 도로 기반**: 직선 거리가 아닌 실제 길찾기 결과 사용

## 🔍 주요 클래스

### `KakaoMobilityService`

```python
# 두 지점 간 경로 조회
route_info = await service.get_route_info(
    origin_lng=127.0, origin_lat=37.5,
    destination_lng=127.1, destination_lat=37.6
)

# 거리 매트릭스 생성 (모든 좌표 쌍)
matrix = await service.get_distance_matrix(
    coordinates=[(127.0, 37.5), (127.1, 37.6), (127.2, 37.7)]
)
```

### `RouteOptimizationService`

```python
# 경로 최적화
result = await service.optimize_route(
    poi_list=[...],
    start_index=0,  # 선택
    end_index=None  # 선택
)

# 최적화 + 브로드캐스트
result = await service.optimize_and_broadcast_to_nestjs(
    workspace_id="...",
    plan_day_id="...",
    poi_list=[...]
)
```

## 📊 성능

- **8개 POI 이하**: 완전 탐색으로 최적해 보장 (~1초 이내)
- **9-20개 POI**: Greedy 알고리즘으로 근사해 제공 (~2-5초)
- **20개 이상**: API 호출 제한으로 시간 소요 증가 (배치 처리 권장)

## ⚠️ 주의사항

### API 호출 제한

- 카카오 모빌리티 API에는 호출 제한이 있습니다
- N개 POI는 N×(N-1)번의 API 호출 필요
- 예: 10개 POI = 90번 호출
- 대량 데이터는 캐싱 또는 배치 처리 고려

### 좌표 형식

- **경도(longitude)**: 127.0xxx (동서 방향, x축)
- **위도(latitude)**: 37.5xxx (남북 방향, y축)
- 카카오 API는 WGS84 좌표계 사용

### 에러 처리

- API 실패 시 `None` 반환
- 경로가 존재하지 않으면 최적화 불가능
- 네트워크 타임아웃: 기본 10초

## 🧪 테스트

```bash
# FastAPI 서버 실행
uv run python main.py

# 다른 터미널에서 테스트
curl -X POST "http://localhost:8000/optimization/route" \
  -H "Content-Type: application/json" \
  -d '{
    "poi_list": [
      {"id": "poi-1", "longitude": 127.0276, "latitude": 37.4979},
      {"id": "poi-2", "longitude": 127.0300, "latitude": 37.5000}
    ]
  }'
```

## 📚 참고 문서

- [카카오 모빌리티 API 문서](https://developers.kakaomobility.com/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [TSP 알고리즘 설명](https://en.wikipedia.org/wiki/Travelling_salesman_problem)
