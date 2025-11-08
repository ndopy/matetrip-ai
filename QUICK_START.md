# 빠른 시작 가이드

## 1. API 키 확인

`.env` 파일에 다음 키가 설정되어 있는지 확인하세요:

```bash
KAKAO_REST_API_KEY=your_kakao_rest_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
OPENAI_API_KEY=your_openai_api_key
```

## 2. 데이터베이스 마이그레이션

```sql
-- PostgreSQL에 연결 후 실행
ALTER TABLE places ADD COLUMN image_url text NULL;
```

## 3. 패키지 설치 확인

```bash
# APScheduler가 설치되어 있어야 함
uv add apscheduler
```

## 4. 데이터 수집 테스트

### 소규모 테스트 (권장)

먼저 한 구만 테스트해보세요:

```bash
# app/data/seoul_districts.py 파일을 열어서 강남구만 남기고 나머지 주석 처리
# 그 후 실행:
uv run python scripts/cli.py collect --categories tourism --with-reviews
```

### 전체 수집 (장소만)

```bash
# 리뷰 처리 없이 장소만 빠르게 수집
uv run python scripts/cli.py collect
```

### 전체 수집 (리뷰 포함)

```bash
# 장소 + 이미지 + 리뷰 + 임베딩 + 요약/태그 전부 처리
# ⚠️ 시간이 오래 걸립니다 (수 시간)
uv run python scripts/cli.py collect --with-reviews
```

## 5. 스케줄러 실행

```bash
# 백그라운드 실행
mkdir -p logs
nohup uv run python scripts/cli.py schedule > logs/scheduler.log 2>&1 &

# 로그 확인
tail -f logs/scheduler.log
```

## 주요 명령어 정리

```bash
# 도움말
uv run python scripts/cli.py --help

# 관광명소만 수집
uv run python scripts/cli.py collect --categories tourism

# 음식점만 수집
uv run python scripts/cli.py collect --categories food

# 여러 카테고리 동시 수집
uv run python scripts/cli.py collect --categories food tourism cafe

# 리뷰 처리 포함
uv run python scripts/cli.py collect --categories food --with-reviews

# 스케줄러 실행 (매주 월요일 오전 2시)
uv run python scripts/cli.py schedule
```

## 트러블슈팅

### 문제: ModuleNotFoundError

```bash
# Python 경로 확인
echo $PYTHONPATH

# 프로젝트 루트에서 실행하는지 확인
pwd
# /root/matetrip-ai 여야 함
```

### 문제: API 키 오류

```bash
# .env 파일 확인
cat .env | grep KAKAO
cat .env | grep NAVER
cat .env | grep OPENAI
```

### 문제: DB 연결 오류

```bash
# DB 연결 확인
cat .env | grep DB_
# PostgreSQL 서비스 확인
docker-compose ps
```

## 다음 단계

- 자세한 내용은 [DATA_COLLECTION_GUIDE.md](docs/DATA_COLLECTION_GUIDE.md) 참조
- 커스터마이징이 필요하면 해당 문서의 "커스터마이징" 섹션 확인
