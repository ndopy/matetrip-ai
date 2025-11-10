# Matetrip AI - 빠른 시작 가이드

> 전국 데이터를 일주일 안에 수집하는 가이드입니다.

## 🎯 목표

- **수집 대상**: 전국 228개 시/군/구
- **수집 항목**: 관광명소, 음식점 (약 20,000개 장소)
- **기간**: 7일
- **비용**: 로컬 무료 / AWS 약 $30

---

## 📋 사전 준비

### 1. API 키 확인

`.env` 파일에 다음 키가 설정되어 있는지 확인하세요:

```bash
KAKAO_REST_API_KEY=your_kakao_rest_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
OPENAI_API_KEY=your_openai_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

### 2. 데이터베이스 준비

```bash
# PostgreSQL에 schema.sql 실행
psql -h localhost -U postgres -d mateTrip -f schema.sql
```

### 3. 패키지 설치 확인

```bash
# 의존성 설치
uv sync
```

---

## 🚀 방법 1: 로컬에서 실행 (가장 간단)

### Step 1: 테스트 (서울 1개 구)

```bash
# 서울 강남구만 테스트
uv run python scripts/cli.py collect --region 서울 --categories tourism
```

### Step 2: 장소만 수집 (Day 0)

```bash
# 전국 장소 수집 (리뷰 제외)
# 12-18시간 소요 (밤새 실행)
uv run python scripts/cli.py collect

# 또는 특정 지역만
uv run python scripts/cli.py collect --region 경기
```

### Step 3: 리뷰 배치 처리 (Day 1-7)

매일 아침 또는 저녁에 실행:

```bash
# Day 1: 배치 0 (전체의 0/7~1/7)
uv run python scripts/process_reviews_batch.py --batch 0 --total-batches 7

# Day 2: 배치 1
uv run python scripts/process_reviews_batch.py --batch 1 --total-batches 7

# Day 3: 배치 2
uv run python scripts/process_reviews_batch.py --batch 2 --total-batches 7

# ...

# Day 7: 배치 6
uv run python scripts/process_reviews_batch.py --batch 6 --total-batches 7
```

각 배치당 6-10시간 소요

---

## ☁️ 방법 2: AWS에서 실행 (권장)

장기간 실행이 필요하므로 AWS 권장

### 사전 준비 (한 번만)

1. **RDS PostgreSQL 생성**
2. **Secrets Manager 설정**
3. **Docker 이미지 푸시**

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./aws/deploy.sh
```

자세한 설정: [`aws/AWS_SETUP_GUIDE.md`](aws/AWS_SETUP_GUIDE.md)

### 실행 방법

**Day 0**: 장소 수집

```bash
# ECS Task 실행
aws ecs run-task \
    --cluster matetrip-cluster \
    --task-definition matetrip-collect-places:1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

**Day 1-7**: 리뷰 배치 처리

EventBridge로 자동화하거나 매일 수동 실행

전체 가이드: [`aws/ONE_WEEK_DEPLOYMENT_GUIDE.md`](aws/ONE_WEEK_DEPLOYMENT_GUIDE.md)

---

## 📊 진행 상황 확인

```sql
-- DB 접속 후

-- 전체 장소 수
SELECT COUNT(*) FROM places;

-- 리뷰가 있는 장소 수
SELECT COUNT(DISTINCT place_id) FROM place_review;

-- 리뷰가 없는 장소 수
SELECT COUNT(*) FROM places p
LEFT JOIN place_review r ON p.id = r.place_id
WHERE r.id IS NULL;

-- 지역별 현황
SELECT
    SUBSTRING(address, 1, 2) as region,
    COUNT(*) as total_places,
    COUNT(DISTINCT r.place_id) as places_with_reviews
FROM places p
LEFT JOIN place_review r ON p.id = r.place_id
GROUP BY SUBSTRING(address, 1, 2)
ORDER BY total_places DESC;
```

---

## 🛠️ 주요 CLI 명령어

### 장소 수집

```bash
# 전국 수집 (리뷰 제외)
python scripts/cli.py collect

# 특정 지역만
python scripts/cli.py collect --region 서울

# 특정 카테고리만
python scripts/cli.py collect --categories food

# 여러 카테고리
python scripts/cli.py collect --categories food tourism cafe

# 네이버 API 제한 설정
python scripts/cli.py collect --with-reviews --max-naver-calls 10000
```

### 리뷰 배치 처리

```bash
# 배치 0 처리
python scripts/process_reviews_batch.py --batch 0 --total-batches 7

# 특정 지역만
python scripts/process_reviews_batch.py --batch 0 --total-batches 7 --region 서울
```

---

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

---

## 📂 주요 파일

- **`scripts/cli.py`** - CLI 도구
- **`scripts/collect_places.py`** - 장소 수집 로직
- **`scripts/process_reviews_batch.py`** - 리뷰 배치 처리
- **`app/data/korea_regions.py`** - 전국 228개 시/군/구 좌표
- **`aws/ONE_WEEK_DEPLOYMENT_GUIDE.md`** - 일주일 수집 전략 (⭐필독)
- **`aws/AWS_SETUP_GUIDE.md`** - AWS 상세 설정

---

## ⚠️ 주의사항

### 네이버 API 제한

- **하루 25,000건 제한**
- 안전하게 20,000건으로 설정
- 제한 도달 시 자동 중단

### 실행 시간

- **장소 수집**: 12-18시간
- **리뷰 배치**: 하루 6-10시간
- 장기간 실행 → AWS 권장

### 비용

- **로컬**: 무료 (전기세만)
- **AWS**: 약 $30 (일주일)

---

## 🎉 다음 단계

1. 소규모 테스트로 시작
2. 로컬 또는 AWS 선택
3. [`aws/ONE_WEEK_DEPLOYMENT_GUIDE.md`](aws/ONE_WEEK_DEPLOYMENT_GUIDE.md) 참조
4. 문제 발생 시 CloudWatch Logs 확인

화이팅! 🚀
