# 경로 최적화 테스트 가이드

## 📋 테스트 구조

이 프로젝트는 **두 가지 유형의 테스트**를 제공합니다:

### 1. 단위 테스트 (Mock 기반)
- **API 호출 없음** - 빠르고 안정적
- Mock 데이터로 로직만 테스트
- 네트워크 연결 불필요
- **8개의 테스트 케이스**

### 2. 통합 테스트 (실제 API)
- **실제 카카오 모빌리티 API 호출**
- 실제 좌표로 경로 최적화 검증
- API 키 필요
- **2개의 테스트 케이스**

## 🚀 테스트 실행 방법

### 방법 1: 스크립트 사용 (추천)

```bash
# 대화형 테스트 실행
bash scripts/run_optimization_tests.sh
```

### 방법 2: pytest 직접 사용

#### Mock 테스트만 실행 (빠름, API 키 불필요)
```bash
uv run pytest test/test_route_optimization.py -v -m "not integration"
```

#### 통합 테스트만 실행 (느림, API 키 필요)
```bash
uv run pytest test/test_route_optimization.py -v -m integration
```

#### 모든 테스트 실행
```bash
uv run pytest test/test_route_optimization.py -v
```

#### 로그 출력 포함
```bash
uv run pytest test/test_route_optimization.py -v -s --log-cli-level=INFO
```

## 📝 테스트 케이스 목록

### 단위 테스트 (Mock)

1. **test_optimize_route_with_3_pois**
   - 3개 POI 최적화 기본 테스트
   - 결과 구조 검증

2. **test_optimize_route_with_fixed_start**
   - 시작 지점 고정 테스트
   - 첫 번째 POI가 고정되는지 확인

3. **test_optimize_route_with_fixed_start_and_end**
   - 시작과 종료 지점 모두 고정 (왕복)
   - 호텔에서 출발해서 호텔로 돌아오는 시나리오

4. **test_optimize_empty_poi_list**
   - 빈 리스트 처리 테스트
   - 에러 없이 빈 결과 반환 확인

5. **test_optimize_single_poi**
   - 단일 POI 처리 테스트
   - 1개만 있을 때 정상 작동 확인

6. **test_tsp_brute_force_algorithm**
   - TSP 완전 탐색 알고리즘 테스트 (5개 POI)
   - 8개 이하일 때 최적해 보장 확인

7. **test_tsp_greedy_algorithm**
   - TSP Greedy 알고리즘 테스트 (10개 POI)
   - 9개 이상일 때 근사해 제공 확인

8. **test_calculate_path_cost**
   - 경로 비용 계산 로직 테스트
   - 시간과 거리 합산 검증

### 통합 테스트 (실제 API)

1. **test_real_api_optimize_route**
   - 서울 강남 지역 3개 장소 최적화
   - 실제 도로 기반 경로 계산

2. **test_real_api_distance_matrix**
   - 거리 매트릭스 생성 테스트
   - 비동기 병렬 API 호출 검증

## ✅ 테스트 결과 예시

### Mock 테스트 (0.17초)
```
test_optimize_route_with_3_pois PASSED                  [ 12%]
test_optimize_route_with_fixed_start PASSED             [ 25%]
test_optimize_route_with_fixed_start_and_end PASSED     [ 37%]
test_optimize_empty_poi_list PASSED                     [ 50%]
test_optimize_single_poi PASSED                         [ 62%]
test_tsp_brute_force_algorithm PASSED                   [ 75%]
test_tsp_greedy_algorithm PASSED                        [ 87%]
test_calculate_path_cost PASSED                         [100%]

======================= 8 passed in 0.17s =======================
```

### 통합 테스트 (실제 API 호출)
```
test_real_api_optimize_route PASSED

🌐 실제 API 테스트 결과:
   최적 경로: ['bongeunsa', 'coex', 'gangnam']
   총 시간: 902초 (15.0분)
   총 거리: 4552m (4.55km)
```

## 🔧 테스트 환경 설정

### 필수 패키지
```bash
uv add pytest pytest-asyncio
```

### 환경 변수 (.env)
통합 테스트를 실행하려면:
```bash
KAKAO_MOBILITY_API_KEY=your-api-key-here
```

## 📊 테스트 커버리지

### 테스트하는 기능

✅ 경로 최적화 알고리즘 (TSP)
- 완전 탐색 (8개 이하)
- Greedy 알고리즘 (9개 이상)

✅ 시작/종료 지점 고정
- 시작만 고정
- 시작 + 종료 고정 (왕복)

✅ 엣지 케이스
- 빈 리스트
- 단일 POI
- 대량 POI (10개 이상)

✅ 카카오 모빌리티 API 연동
- 거리 매트릭스 생성
- 비동기 병렬 호출
- 에러 처리

## 🐛 디버깅

### 테스트 실패 시 확인 사항

1. **Import 에러**
   - `conftest.py`가 있는지 확인
   - `pytest.ini`의 pythonpath 설정 확인

2. **API 호출 실패**
   - `.env`에 `KAKAO_MOBILITY_API_KEY` 설정 확인
   - API 키 유효성 확인
   - 네트워크 연결 확인

3. **비동기 테스트 에러**
   - `pytest-asyncio` 설치 확인
   - `pytest.ini`의 asyncio_mode 설정 확인

## 📚 추가 정보

### pytest 마커

- `@pytest.mark.asyncio` - 비동기 테스트
- `@pytest.mark.integration` - 통합 테스트 (실제 API 호출)

### 특정 테스트만 실행

```bash
# 특정 테스트 함수만 실행
uv run pytest test/test_route_optimization.py::test_optimize_route_with_3_pois -v

# 패턴 매칭
uv run pytest test/test_route_optimization.py -k "fixed" -v
```

### 테스트 실패 시 자세한 정보 보기

```bash
uv run pytest test/test_route_optimization.py -v --tb=long
```

## 🎯 CI/CD 통합

GitHub Actions 등에서 사용할 수 있는 명령어:

```yaml
# Mock 테스트만 (빠름, API 키 불필요)
- name: Run unit tests
  run: uv run pytest test/test_route_optimization.py -v -m "not integration"

# 통합 테스트 (API 키 필요, GitHub Secrets 사용)
- name: Run integration tests
  run: uv run pytest test/test_route_optimization.py -v -m integration
  env:
    KAKAO_MOBILITY_API_KEY: ${{ secrets.KAKAO_MOBILITY_API_KEY }}
```
