# 장소 데이터 수집 가이드

카카오 Local API를 활용한 자동 데이터 수집 시스템 사용 가이드입니다.

## 개요

이 시스템은 다음 작업을 자동화합니다:

1. **카카오 Local API**로 서울 25개 구의 장소 데이터 수집
2. **네이버 이미지 검색 API**로 장소 대표 이미지 가져오기
3. **네이버 블로그 검색 API**로 리뷰 URL 수집
4. **Crawl4AI**로 리뷰 크롤링
5. **OpenAI GPT**로 리뷰 요약 및 태그 생성
6. **로컬 임베딩 모델**로 벡터 임베딩 생성

## 설정

### 1. API 키 설정

`.env` 파일에 다음 키가 설정되어 있는지 확인하세요:

```bash
# Kakao Local API
KAKAO_REST_API_KEY=your_kakao_rest_api_key

# Naver Search API
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
```

### 2. 데이터베이스 마이그레이션

새로운 `image_url` 필드를 추가하려면:

```sql
ALTER TABLE places ADD COLUMN image_url text NULL;
```

## 사용 방법

### CLI 명령어

#### 1. 데이터 수집 (리뷰 처리 포함)

```bash
# uv 사용
uv run python scripts/cli.py collect --with-reviews

# 또는 직접 실행
python scripts/cli.py collect --with-reviews
```

#### 2. 데이터 수집 (장소만, 리뷰 제외)

```bash
uv run python scripts/cli.py collect
```

#### 3. 특정 카테고리만 수집

```bash
# 관광명소만
uv run python scripts/cli.py collect --categories tourism --with-reviews

# 음식점만
uv run python scripts/cli.py collect --categories food --with-reviews

# 카페 + 음식점
uv run python scripts/cli.py collect --categories cafe food --with-reviews
```

#### 4. 스케줄러 실행 (매주 월요일 오전 2시)

```bash
# 포그라운드 실행
uv run python scripts/cli.py schedule

# 백그라운드 실행 (nohup 사용)
nohup uv run python scripts/cli.py schedule > logs/scheduler.log 2>&1 &
```

### 직접 스크립트 실행

#### 단순 수집 스크립트

```bash
# 기본 수집 (관광명소 + 음식점, 리뷰 처리 포함)
uv run python scripts/collect_places.py
```

#### 스케줄러

```bash
# 스케줄러 실행
uv run python scripts/scheduler.py
```

## 수집 범위

### 기본 설정

- **지역**: 서울 25개 구
- **카테고리**: 관광명소(AT4) + 음식점(FD6)
- **주기**: 매주 월요일 오전 2시
- **검색 반경**: 각 구 중심으로부터 5km
- **페이지 제한**: 구당 카테고리당 3페이지 (최대 45개 장소)

### 카테고리 코드

- `FD6`: 음식점 (한식, 중식, 일식, 카페 등)
- `AT4`: 관광명소
- `CE7`: 카페
- `AD5`: 숙박 (호텔, 모텔, 펜션)
- `CT1`: 문화시설

## 데이터 처리 플로우

```
1. 카카오 API로 장소 검색
   ↓
2. 중복 체크 (title + address)
   ↓
3. DB에 장소 저장
   ↓
4. 네이버 이미지 검색으로 대표 이미지 URL 추가
   ↓
5. 네이버 블로그 검색으로 리뷰 URL 수집
   ↓
6. Crawl4AI로 리뷰 크롤링
   ↓
7. 로컬 임베딩 모델로 리뷰 벡터화
   ↓
8. OpenAI GPT로 태그 및 요약 생성
   ↓
9. 모든 데이터 DB에 커밋
```

## 커스터마이징

### 수집 지역 변경

`app/data/seoul_districts.py`에서 지역 좌표를 수정하세요:

```python
SEOUL_DISTRICTS = [
    {"name": "강남구", "longitude": 127.0495556, "latitude": 37.514575},
    # ... 다른 구 추가
]
```

### 스케줄 변경

`scripts/scheduler.py`의 CronTrigger 설정을 수정하세요:

```python
# 매일 오전 3시
scheduler.add_job(
    scheduled_collection,
    CronTrigger(hour=3, minute=0),
    ...
)

# 매주 수요일 오후 9시
scheduler.add_job(
    scheduled_collection,
    CronTrigger(day_of_week="wed", hour=21, minute=0),
    ...
)
```

### 검색 반경 및 페이지 수 조정

`scripts/collect_places.py`의 `collect_and_process()` 메서드에서:

```python
kakao_places = self.kakao_service.search_places_by_category(
    category_code=category_code,
    x=district["longitude"],
    y=district["latitude"],
    radius=10000,  # 10km로 확대
    max_pages=5,   # 5페이지로 증가 (75개)
)
```

## 주의사항

### API 호출 제한

- **카카오 Local API**: 일일 300,000건
- **네이버 블로그 검색**: 일일 25,000건
- **네이버 이미지 검색**: 일일 25,000건
- **OpenAI GPT**: 사용량 기반 과금

### 권장사항

1. **처음에는 소규모로 테스트**
   ```bash
   # 한 구만 테스트하려면 seoul_districts.py에서 일시적으로 다른 구 주석 처리
   ```

2. **리뷰 처리는 선택적으로**
   - 장소 수집만: `collect` (리뷰 처리 OFF)
   - 전체 처리: `collect --with-reviews` (시간 오래 걸림)

3. **로그 모니터링**
   ```bash
   # 실시간 로그 확인
   tail -f logs/scheduler.log
   ```

## 트러블슈팅

### Q: "API 키 오류"가 발생해요

`.env` 파일의 API 키를 확인하세요. 특히 KAKAO_REST_API_KEY는 카카오 개발자 콘솔에서 발급받아야 합니다.

### Q: 중복 데이터가 계속 수집돼요

중복 체크는 `title + address` 기준입니다. 카카오 API에서 동일 장소가 다른 주소로 반환되면 중복될 수 있습니다.

### Q: 스케줄러가 종료돼요

백그라운드 실행 시 `nohup`을 사용하거나, systemd 서비스로 등록하세요.

### Q: 리뷰 처리가 너무 느려요

장소당 리뷰 크롤링, 임베딩, GPT 호출이 포함되어 시간이 오래 걸립니다.
- `--with-reviews` 플래그를 제거하고 장소만 먼저 수집
- 나중에 별도로 리뷰 처리 스크립트 실행

## 비용 예측

### 서울 전역 (관광명소 + 음식점) 1회 수집 기준

- **카카오 API**: 무료 (25개 구 × 2 카테고리 × 45개 = ~2,250건)
- **네이버 API**: 무료 (장소당 1회 이미지 + 블로그 검색)
- **OpenAI GPT-4o-mini**: 장소당 약 $0.01 (2,250개 = ~$22.5)
- **로컬 임베딩**: 무료 (자체 서버)

### 주간 실행 시 월 비용

- 주 1회 × 4주 = 월 약 $90
- 중복 제거로 실제 비용은 더 낮음 (신규 장소만 처리)
