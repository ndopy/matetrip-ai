# 일주일 전국 데이터 수집 전략

네이버 API 제한(하루 25,000건)을 고려하여 일주일 안에 전국 데이터를 안전하게 수집하는 가이드입니다.

## 📊 수집 전략 개요

### 2단계 수집 방식

**1단계 (Day 0)**: 장소만 빠르게 수집 (리뷰 제외)
- 전국 약 228개 시/군/구 × 2개 카테고리 × 45개 장소 = 약 20,500개 장소
- 예상 시간: 12-18시간
- API 사용: 카카오 Local API만 (네이버 API 사용 안 함)

**2단계 (Day 1-7)**: 리뷰를 7개 배치로 나눠서 처리
- 각 배치당 약 3,000개 장소 처리
- 장소당 네이버 API 평균 5회 호출 = 하루 15,000건 (안전 여유)
- 네이버 API 제한 20,000건으로 설정 (실제 제한 25,000건)

---

## 🚀 Day 0: 장소 수집 (리뷰 제외)

### 목표
전국 모든 장소 데이터를 DB에 저장 (제목, 주소, 좌표, 카테고리)

### 실행 방법

#### 옵션 A: 로컬에서 실행 (권장)
밤사이 컴퓨터를 켜두고 실행

```bash
# 전국 장소 수집 (리뷰 제외)
uv run python scripts/cli.py collect

# 또는 특정 지역만 먼저 테스트
uv run python scripts/cli.py collect --region 서울
```

#### 옵션 B: AWS ECS에서 실행

1. **Docker 이미지 푸시**
```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
./aws/deploy.sh
```

2. **CloudWatch Log Group 생성**
```bash
aws logs create-log-group \
    --log-group-name /ecs/matetrip-collect-places \
    --region ap-northeast-2
```

3. **ECS Task Definition 등록**
```bash
# YOUR_ACCOUNT_ID를 실제 값으로 수정 후
aws ecs register-task-definition \
    --cli-input-json file://aws/ecs-task-collect-places.json \
    --region ap-northeast-2
```

4. **수동으로 Task 실행**
```bash
aws ecs run-task \
    --cluster matetrip-cluster \
    --task-definition matetrip-collect-places:1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={
      subnets=[subnet-xxxxx,subnet-yyyyy],
      securityGroups=[sg-xxxxx],
      assignPublicIp=ENABLED
    }" \
    --region ap-northeast-2
```

5. **CloudWatch에서 진행 상황 모니터링**

### 예상 결과
- 수집된 장소: 약 20,000개
- 소요 시간: 12-18시간
- 비용: ECS Fargate 약 $3-5

---

## 📅 Day 1-7: 리뷰 배치 처리

### 배치 나누기

전체 장소를 7개 배치로 나눕니다:

| 배치 | 실행 날짜 | 처리 장소 수 | 네이버 API 호출 | 실행 시간 |
|------|-----------|--------------|-----------------|-----------|
| 0 | Day 1 | ~3,000개 | ~15,000건 | 6-10시간 |
| 1 | Day 2 | ~3,000개 | ~15,000건 | 6-10시간 |
| 2 | Day 3 | ~3,000개 | ~15,000건 | 6-10시간 |
| 3 | Day 4 | ~3,000개 | ~15,000건 | 6-10시간 |
| 4 | Day 5 | ~3,000개 | ~15,000건 | 6-10시간 |
| 5 | Day 6 | ~3,000개 | ~15,000건 | 6-10시간 |
| 6 | Day 7 | ~2,500개 | ~12,500건 | 5-8시간 |

### AWS EventBridge 스케줄 설정

#### 1. CloudWatch Log Group 생성

```bash
aws logs create-log-group \
    --log-group-name /ecs/matetrip-process-reviews \
    --region ap-northeast-2
```

#### 2. ECS Task Definition 등록

```bash
# YOUR_ACCOUNT_ID를 실제 값으로 수정
aws ecs register-task-definition \
    --cli-input-json file://aws/ecs-task-process-reviews.json \
    --region ap-northeast-2
```

#### 3. EventBridge 스케줄 생성 (배치 0-6)

각 배치마다 별도의 스케줄을 생성합니다.

**배치 0 스케줄 (Day 1 - 월요일 오전 2시)**

```bash
aws scheduler create-schedule \
    --name matetrip-reviews-batch-0 \
    --schedule-expression "at(2025-01-13T17:00:00)" \
    --flexible-time-window Mode=OFF \
    --target '{
      "Arn": "arn:aws:ecs:ap-northeast-2:YOUR_ACCOUNT_ID:cluster/matetrip-cluster",
      "RoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/EventBridgeSchedulerRole",
      "EcsParameters": {
        "TaskDefinitionArn": "arn:aws:ecs:ap-northeast-2:YOUR_ACCOUNT_ID:task-definition/matetrip-process-reviews:1",
        "LaunchType": "FARGATE",
        "NetworkConfiguration": {
          "awsvpcConfiguration": {
            "Subnets": ["subnet-xxxxx", "subnet-yyyyy"],
            "SecurityGroups": ["sg-xxxxx"],
            "AssignPublicIp": "ENABLED"
          }
        },
        "PlatformVersion": "LATEST"
      },
      "Input": "{\"containerOverrides\": [{\"name\": \"matetrip-review-processor\", \"environment\": [{\"name\": \"BATCH_INDEX\", \"value\": \"0\"}]}]}"
    }' \
    --region ap-northeast-2
```

**배치 1-6 스케줄**

위 명령어를 반복하되, 다음을 변경:
- `--name`: `matetrip-reviews-batch-1`, `matetrip-reviews-batch-2`, ...
- `--schedule-expression`: 날짜를 하루씩 증가 (`2025-01-14T17:00:00`, `2025-01-15T17:00:00`, ...)
- `BATCH_INDEX`: `1`, `2`, `3`, ...

#### 4. 수동 실행 (테스트용)

스케줄 대신 수동으로 바로 실행하려면:

```bash
# 배치 0 실행
aws ecs run-task \
    --cluster matetrip-cluster \
    --task-definition matetrip-process-reviews:1 \
    --launch-type FARGATE \
    --overrides '{
      "containerOverrides": [{
        "name": "matetrip-review-processor",
        "environment": [
          {"name": "BATCH_INDEX", "value": "0"},
          {"name": "TOTAL_BATCHES", "value": "7"}
        ]
      }]
    }' \
    --network-configuration "awsvpcConfiguration={
      subnets=[subnet-xxxxx,subnet-yyyyy],
      securityGroups=[sg-xxxxx],
      assignPublicIp=ENABLED
    }" \
    --region ap-northeast-2

# 배치 1 실행 (다음 날)
# BATCH_INDEX를 1로 변경하여 동일하게 실행
```

---

## 🔄 대체 전략: 간단한 방법

EventBridge 설정이 복잡하다면, **로컬에서 매일 수동 실행**도 가능합니다.

### 매일 아침 실행하는 Cron 스크립트

`run-daily-batch.sh` 파일 생성:

```bash
#!/bin/bash

# 오늘의 배치 인덱스 계산 (0-6)
BATCH_INDEX=$(($(date +%u) - 1))  # 월요일=0, 화요일=1, ...

echo "배치 $BATCH_INDEX 실행 중..."

uv run python scripts/process_reviews_batch.py \
    --batch $BATCH_INDEX \
    --total-batches 7 \
    --max-naver-calls 20000

echo "배치 $BATCH_INDEX 완료!"
```

실행 권한 부여:
```bash
chmod +x run-daily-batch.sh
```

Cron으로 매일 오전 2시에 자동 실행:
```bash
crontab -e

# 다음 줄 추가
0 2 * * * cd /path/to/matetrip-ai && ./run-daily-batch.sh >> /tmp/matetrip-batch.log 2>&1
```

---

## 📊 모니터링 및 확인

### CloudWatch Logs 확인

```bash
# 최근 로그 스트림 목록
aws logs describe-log-streams \
    --log-group-name /ecs/matetrip-process-reviews \
    --order-by LastEventTime \
    --descending \
    --max-items 5 \
    --region ap-northeast-2

# 특정 로그 스트림 내용 확인
aws logs get-log-events \
    --log-group-name /ecs/matetrip-process-reviews \
    --log-stream-name ecs/matetrip-review-processor/TASK_ID \
    --region ap-northeast-2
```

### 진행 상황 확인 SQL

```sql
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

## 💰 예상 비용 (일주일)

| 항목 | 비용 |
|------|------|
| Day 0: 장소 수집 (12-18시간) | $3-5 |
| Day 1-7: 리뷰 배치 (하루 6-10시간 × 7일) | $15-25 |
| RDS db.t3.micro (7일) | $3 |
| ECR 저장소 | $1 |
| CloudWatch Logs | $2 |
| 네이버 API | 무료 (제한 내) |
| **총 예상 비용** | **$24-36** |

---

## 🚨 트러블슈팅

### Task가 시작되지 않는 경우

1. CloudWatch Logs 확인
2. ECS Task의 stopped reason 확인
```bash
aws ecs describe-tasks \
    --cluster matetrip-cluster \
    --tasks TASK_ARN \
    --region ap-northeast-2
```

### 네이버 API 제한 초과

로그에 "API 호출 제한에 도달"이 보이면:
- 정상 동작입니다 (제한 내에서 안전하게 중단)
- 다음 배치가 다음 날 실행됩니다

### DB 연결 실패

- RDS 보안 그룹에서 ECS 보안 그룹 허용 확인
- Secrets Manager의 DB 자격 증명 확인

### 중간에 실패한 배치 재실행

```bash
# 특정 배치만 다시 실행
uv run python scripts/process_reviews_batch.py \
    --batch 3 \
    --total-batches 7
```

---

## ✅ 체크리스트

### Day 0 준비
- [ ] RDS 생성 및 schema.sql 실행
- [ ] Secrets Manager 설정
- [ ] ECR에 이미지 푸시
- [ ] ECS Cluster 생성
- [ ] 보안 그룹 설정
- [ ] 장소 수집 Task 실행

### Day 1-7 준비
- [ ] EventBridge Scheduler Role 생성
- [ ] 리뷰 처리 Task Definition 등록
- [ ] 7개 EventBridge 스케줄 생성 (또는 Cron 설정)
- [ ] CloudWatch Logs 모니터링 설정

### 완료 후
- [ ] 전체 장소 수 확인
- [ ] 리뷰 처리 완료 확인
- [ ] 불필요한 ECS Task 및 스케줄 삭제
- [ ] 최종 데이터 백업

---

## 📞 지원

문제가 발생하면:
1. CloudWatch Logs 먼저 확인
2. `aws/AWS_SETUP_GUIDE.md` 참조
3. GitHub Issues에 문의

일주일 수집 화이팅! 🚀
