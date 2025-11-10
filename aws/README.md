# AWS 배포 파일

이 디렉토리에는 Matetrip AI를 AWS에 배포하기 위한 모든 파일이 포함되어 있습니다.

## 📁 파일 목록

- **`AWS_SETUP_GUIDE.md`** - 전체 AWS 설정 가이드 (단계별 상세 설명)
- **`deploy.sh`** - Docker 이미지 빌드 및 ECR 푸시 스크립트
- **`ecs-task-definition.json`** - ECS Fargate Task Definition
- **`iam-task-role-policy.json`** - ECS Task Role IAM Policy (Bedrock 접근용)

## 🚀 빠른 시작

### 1. Docker 이미지 빌드 및 푸시

```bash
# AWS Account ID 설정
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 배포 스크립트 실행
./aws/deploy.sh
```

### 2. AWS 설정

자세한 설정 방법은 [`AWS_SETUP_GUIDE.md`](./AWS_SETUP_GUIDE.md)를 참조하세요.

주요 단계:
1. RDS PostgreSQL 설정
2. ECR Repository 생성
3. Secrets Manager 설정
4. IAM Roles 생성
5. ECS Task Definition 등록
6. EventBridge 스케줄 설정

## 🔐 보안

- API Keys와 DB 자격 증명은 Secrets Manager에 저장
- `.env` 파일은 Docker 이미지에 포함되지 않음 (`.dockerignore`)
- Task Role로 AWS 리소스 접근 제어

## 💡 도움말

문제가 발생하면:
1. CloudWatch Logs 확인: `/ecs/matetrip-place-collector`
2. ECS Task 상태 확인
3. IAM Role 권한 확인
4. VPC 보안 그룹 설정 확인
