# Matetrip AI - AWS 배포 및 스케줄링 가이드

이 가이드는 Matetrip AI 장소 수집 파이프라인을 AWS ECS Fargate에 배포하고 EventBridge로 스케줄링하는 방법을 설명합니다.

## 📋 목차

1. [사전 준비사항](#1-사전-준비사항)
2. [RDS PostgreSQL 설정](#2-rds-postgresql-설정)
3. [ECR Repository 생성](#3-ecr-repository-생성)
4. [Secrets Manager 설정](#4-secrets-manager-설정)
5. [IAM Role 생성](#5-iam-role-생성)
6. [Docker 이미지 빌드 및 푸시](#6-docker-이미지-빌드-및-푸시)
7. [VPC 및 보안 그룹 설정](#7-vpc-및-보안-그룹-설정)
8. [ECS Cluster 생성](#8-ecs-cluster-생성)
9. [ECS Task Definition 등록](#9-ecs-task-definition-등록)
10. [CloudWatch Logs 설정](#10-cloudwatch-logs-설정)
11. [EventBridge 스케줄 설정](#11-eventbridge-스케줄-설정)
12. [테스트 및 모니터링](#12-테스트-및-모니터링)

---

## 1. 사전 준비사항

### 필요한 것들

- AWS 계정
- AWS CLI 설치 및 구성
- Docker 설치
- 로컬에서 정상 작동하는 파이프라인 코드

### AWS CLI 설정

```bash
# AWS CLI 설치 확인
aws --version

# AWS 자격 증명 설정
aws configure
# AWS Access Key ID, Secret Access Key, Region(ap-northeast-2) 입력
```

---

## 2. RDS PostgreSQL 설정

### 2.1 RDS 인스턴스 생성

1. AWS Console → RDS → Databases → Create database
2. 설정:

   - **Engine**: PostgreSQL 15 이상
   - **Templates**: Free tier or Dev/Test
   - **DB instance identifier**: `matetrip-db`
   - **Master username**: `postgres`
   - **Master password**: 안전한 비밀번호 입력
   - **DB instance class**: db.t3.micro (최소 사양) 또는 db.t4g.medium (권장)
   - **Storage**: 20GB (General Purpose SSD)
   - **VPC**: 기본 VPC 사용 (또는 새로 생성)
   - **Public access**: No (보안상)
   - **VPC security group**: 새로 생성 (예: `matetrip-db-sg`)
   - **Database name**: `mateTrip`

3. Create database 클릭

### 2.2 보안 그룹 수정

1. RDS 인스턴스의 보안 그룹(`matetrip-db-sg`) 클릭
2. Inbound rules → Edit inbound rules
3. Add rule:
   - **Type**: PostgreSQL
   - **Port**: 5432
   - **Source**: ECS 태스크가 사용할 보안 그룹 (나중에 생성)
   - **Description**: `ECS tasks access`

### 2.3 데이터베이스 초기화

RDS 엔드포인트에 접속하여 schema.sql 실행:

```bash
# 로컬에서 RDS로 접속 (VPN 또는 Bastion Host 필요)
psql -h your-rds-endpoint.ap-northeast-2.rds.amazonaws.com \
     -U postgres -d mateTrip -f schema.sql
```

---

## 3. ECR Repository 생성

### 3.1 ECR Repository 생성

```bash
# ECR Repository 생성
aws ecr create-repository \
    --repository-name matetrip-ai \
    --region ap-northeast-2

# 출력 예시:
# {
#     "repository": {
#         "repositoryUri": "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/matetrip-ai"
#     }
# }
```

Repository URI를 메모해두세요!

---

## 4. Secrets Manager 설정

민감한 정보를 안전하게 저장합니다.

### 4.1 데이터베이스 자격 증명 저장

```bash
aws secretsmanager create-secret \
    --name matetrip/db \
    --description "Matetrip Database Credentials" \
    --secret-string '{
      "DB_HOST":"your-rds-endpoint.ap-northeast-2.rds.amazonaws.com",
      "DB_PORT":"5432",
      "DB_USER":"postgres",
      "DB_PASSWORD":"your-db-password",
      "DB_NAME":"mateTrip"
    }' \
    --region ap-northeast-2
```

### 4.2 API Keys 저장

```bash
aws secretsmanager create-secret \
    --name matetrip/api-keys \
    --description "Matetrip API Keys" \
    --secret-string '{
      "OPENAI_API_KEY":"your-openai-key",
      "NAVER_CLIENT_ID":"your-naver-client-id",
      "NAVER_CLIENT_SECRET":"your-naver-secret",
      "KAKAO_REST_API_KEY":"your-kakao-key",
      "SERVICE_KEY":"your-service-key"
    }' \
    --region ap-northeast-2
```

### 4.3 Secret ARN 확인

```bash
# DB Secret ARN
aws secretsmanager describe-secret --secret-id matetrip/db --region ap-northeast-2

# API Keys Secret ARN
aws secretsmanager describe-secret --secret-id matetrip/api-keys --region ap-northeast-2
```

ARN을 메모해두세요 (ECS Task Definition에서 사용)

---

## 5. IAM Role 생성

### 5.1 ECS Task Execution Role 생성

이 Role은 ECR에서 이미지를 가져오고 CloudWatch Logs에 로그를 쓰고 Secrets Manager에서 시크릿을 읽습니다.

1. AWS Console → IAM → Roles → Create role
2. **Trusted entity type**: AWS service
3. **Use case**: Elastic Container Service → Elastic Container Service Task
4. **Permissions**:
   - `AmazonECSTaskExecutionRolePolicy` (AWS 관리형 정책)
   - 추가 인라인 정책 (Secrets Manager 접근):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": [
        "arn:aws:secretsmanager:ap-northeast-2:YOUR_ACCOUNT_ID:secret:matetrip/*"
      ]
    }
  ]
}
```

5. **Role name**: `ecsTaskExecutionRole`
6. Create role

### 5.2 ECS Task Role 생성

이 Role은 태스크가 AWS Bedrock에 접근하도록 허용합니다.

1. AWS Console → IAM → Roles → Create role
2. **Trusted entity type**: AWS service
3. **Use case**: Elastic Container Service → Elastic Container Service Task
4. **Permissions**: 인라인 정책 추가

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:ap-northeast-2::foundation-model/amazon.titan-embed-text-v2:0",
        "arn:aws:bedrock:ap-northeast-2::foundation-model/*"
      ]
    }
  ]
}
```

5. **Role name**: `ecsTaskRole`
6. Create role

### 5.3 Bedrock 모델 접근 활성화

AWS Bedrock 콘솔에서:

1. Bedrock → Model access
2. **amazon.titan-embed-text-v2:0** 모델 활성화
3. Request access (필요시)

---

## 6. Docker 이미지 빌드 및 푸시

### 6.1 환경 변수 설정

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=ap-northeast-2
export IMAGE_TAG=latest
```

### 6.2 배포 스크립트 실행

```bash
# 프로젝트 루트에서 실행
./aws/deploy.sh
```

이 스크립트는 자동으로:

1. Docker 이미지 빌드
2. ECR 로그인
3. 이미지 태그 지정
4. ECR에 푸시

---

## 7. VPC 및 보안 그룹 설정

### 7.1 ECS Tasks용 보안 그룹 생성

1. AWS Console → EC2 → Security Groups → Create security group
2. 설정:

   - **Name**: `matetrip-ecs-tasks-sg`
   - **Description**: Security group for ECS tasks
   - **VPC**: RDS와 동일한 VPC
   - **Outbound rules**: All traffic (기본값 유지)
   - **Inbound rules**: 필요 없음 (외부에서 접속 안 함)

3. Create security group

### 7.2 RDS 보안 그룹 업데이트

1. RDS 보안 그룹(`matetrip-db-sg`) 편집
2. Inbound rules 추가:
   - **Type**: PostgreSQL
   - **Port**: 5432
   - **Source**: `matetrip-ecs-tasks-sg` 선택
   - **Description**: ECS tasks access

---

## 8. ECS Cluster 생성

### 8.1 Cluster 생성

```bash
aws ecs create-cluster \
    --cluster-name matetrip-cluster \
    --region ap-northeast-2
```

또는 AWS Console:

1. ECS → Clusters → Create cluster
2. **Cluster name**: `matetrip-cluster`
3. **Infrastructure**: AWS Fargate (serverless)
4. Create

---

## 9. ECS Task Definition 등록

### 9.1 Task Definition JSON 수정

`aws/ecs-task-definition.json` 파일을 열어 다음 값들을 실제 값으로 변경:

- `YOUR_ACCOUNT_ID` → 실제 AWS Account ID
- `executionRoleArn` → ecsTaskExecutionRole의 ARN
- `taskRoleArn` → ecsTaskRole의 ARN
- ECR 이미지 URL
- Secrets Manager ARN들

### 9.2 Task Definition 등록

```bash
aws ecs register-task-definition \
    --cli-input-json file://aws/ecs-task-definition.json \
    --region ap-northeast-2
```

---

## 10. CloudWatch Logs 설정

### 10.1 Log Group 생성

```bash
aws logs create-log-group \
    --log-group-name /ecs/matetrip-place-collector \
    --region ap-northeast-2
```

### 10.2 Log Retention 설정 (선택)

```bash
aws logs put-retention-policy \
    --log-group-name /ecs/matetrip-place-collector \
    --retention-in-days 7 \
    --region ap-northeast-2
```

---

## 11. EventBridge 스케줄 설정

### 11.1 EventBridge Scheduler Role 생성

1. IAM → Roles → Create role
2. **Trusted entity**: Custom trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "scheduler.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

3. **Permissions**: 인라인 정책 추가

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ecs:RunTask"],
      "Resource": [
        "arn:aws:ecs:ap-northeast-2:YOUR_ACCOUNT_ID:task-definition/matetrip-place-collector:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["iam:PassRole"],
      "Resource": [
        "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
        "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskRole"
      ]
    }
  ]
}
```

4. **Role name**: `EventBridgeSchedulerRole`

### 11.2 EventBridge 스케줄 생성

#### 옵션 A: AWS Console 사용

1. EventBridge → Schedules → Create schedule
2. **Schedule name**: `matetrip-weekly-collection`
3. **Schedule pattern**:
   - **Recurring**: Cron-based schedule
   - **Cron expression**: `0 2 ? * MON *` (매주 월요일 오전 2시 UTC)
   - 또는 한국 시간 기준: `0 17 ? * SUN *` (일요일 오후 5시 UTC = 월요일 오전 2시 KST)
4. **Flexible time window**: Off
5. **Target**: AWS ECS
   - **Cluster**: `matetrip-cluster`
   - **Task definition family**: `matetrip-place-collector`
   - **Launch type**: Fargate
   - **Platform version**: LATEST
   - **Subnets**: RDS와 같은 VPC의 private subnet 선택
   - **Security groups**: `matetrip-ecs-tasks-sg`
   - **Auto-assign public IP**: ENABLED (인터넷 접근 필요시)
6. **Execution role**: `EventBridgeSchedulerRole`
7. Create schedule

#### 옵션 B: AWS CLI 사용

```bash
aws scheduler create-schedule \
    --name matetrip-weekly-collection \
    --schedule-expression "cron(0 17 ? * SUN *)" \
    --flexible-time-window Mode=OFF \
    --target '{
      "Arn": "arn:aws:ecs:ap-northeast-2:YOUR_ACCOUNT_ID:cluster/matetrip-cluster",
      "RoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/EventBridgeSchedulerRole",
      "EcsParameters": {
        "TaskDefinitionArn": "arn:aws:ecs:ap-northeast-2:YOUR_ACCOUNT_ID:task-definition/matetrip-place-collector:1",
        "LaunchType": "FARGATE",
        "NetworkConfiguration": {
          "awsvpcConfiguration": {
            "Subnets": ["subnet-xxxxx", "subnet-yyyyy"],
            "SecurityGroups": ["sg-xxxxx"],
            "AssignPublicIp": "ENABLED"
          }
        }
      }
    }' \
    --region ap-northeast-2
```

### 11.3 스케줄 예시

- **매일 오전 2시**: `cron(0 17 ? * * *)` (UTC 기준)
- **매주 월요일 오전 2시**: `cron(0 17 ? * SUN *)`
- **매월 1일 오전 2시**: `cron(0 17 1 * ? *)`
- **매시간**: `rate(1 hour)`

---

## 12. 테스트 및 모니터링

### 12.1 수동 테스트

먼저 수동으로 태스크를 실행해서 정상 작동하는지 확인:

```bash
aws ecs run-task \
    --cluster matetrip-cluster \
    --task-definition matetrip-place-collector:1 \
    --launch-type FARGATE \
aws ecs run-task \
    --cluster matetrip-cluster \
    --task-definition matetrip-place-collector:1 \
    --launch-type FARGATE \
    --network-configuration 'awsvpcConfiguration={subnets=[subnet-xxxxx,subnet-yyyyy],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}' \
    --region ap-northeast-2
    }" \
    --region ap-northeast-2
```

### 12.2 CloudWatch Logs 확인

1. CloudWatch → Log groups → `/ecs/matetrip-place-collector`
2. 최신 로그 스트림 확인
3. 에러 로그 확인

### 12.3 모니터링 대시보드 (선택)

CloudWatch에서 다음 메트릭 모니터링:

- ECS Task 실행 상태
- Task CPU/메모리 사용량
- 로그에서 에러 패턴 탐지

### 12.4 알림 설정 (선택)

CloudWatch Alarms + SNS를 사용해 실패 시 알림:

```bash
# SNS Topic 생성
aws sns create-topic --name matetrip-alerts --region ap-northeast-2

# 이메일 구독
aws sns subscribe \
    --topic-arn arn:aws:sns:ap-northeast-2:YOUR_ACCOUNT_ID:matetrip-alerts \
    --protocol email \
    --notification-endpoint your-email@example.com
```

---

## 🎯 요약 체크리스트

배포 전 확인 사항:

- [ ] RDS PostgreSQL 인스턴스 생성 및 schema.sql 실행
- [ ] ECR Repository 생성
- [ ] Secrets Manager에 DB 및 API 키 저장
- [ ] IAM Roles 생성 (ecsTaskExecutionRole, ecsTaskRole, EventBridgeSchedulerRole)
- [ ] Bedrock 모델 접근 활성화
- [ ] VPC 보안 그룹 설정
- [ ] Docker 이미지 빌드 및 ECR 푸시
- [ ] ECS Cluster 생성
- [ ] ECS Task Definition 등록
- [ ] CloudWatch Logs 그룹 생성
- [ ] EventBridge 스케줄 생성
- [ ] 수동 테스트 실행 및 로그 확인

---

## 🚨 트러블슈팅

### Task가 시작되지 않는 경우

1. CloudWatch Logs 확인
2. Task Definition의 환경 변수 및 Secrets 확인
3. IAM Role 권한 확인
4. 보안 그룹 및 네트워크 설정 확인

### DB 연결 실패

1. RDS 보안 그룹에서 ECS 보안 그룹 허용 확인
2. RDS 엔드포인트 주소 확인
3. Secrets Manager의 DB 자격 증명 확인
4. VPC 내 private subnet 사용 확인

### Bedrock 접근 실패

1. ecsTaskRole에 Bedrock 권한 확인
2. Bedrock 모델 접근 활성화 확인
3. Region 일치 확인 (ap-northeast-2)

---

## 💰 비용 예상 (월 기준)

- **RDS db.t3.micro**: ~$15
- **ECS Fargate (주 1회, 1시간 실행)**: ~$2
- **ECR 저장소**: ~$1
- **Secrets Manager**: ~$1
- **CloudWatch Logs**: ~$1

**총 예상 비용**: ~$20/월

---

## 📞 문의

문제가 발생하면 CloudWatch Logs를 먼저 확인하고, 필요시 AWS Support에 문의하세요.
