#!/bin/bash

# Matetrip AI - AWS ECR 배포 스크립트
# 사용법: ./aws/deploy.sh

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 환경 변수 확인
echo -e "${GREEN}=== Matetrip AI 배포 시작 ===${NC}"

# 필수 환경 변수 체크
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}ERROR: AWS_ACCOUNT_ID 환경 변수가 설정되지 않았습니다.${NC}"
    echo "예: export AWS_ACCOUNT_ID=123456789012"
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo -e "${YELLOW}AWS_REGION이 설정되지 않아 기본값(ap-northeast-2)을 사용합니다.${NC}"
    AWS_REGION="ap-northeast-2"
fi

# 변수 설정
ECR_REPOSITORY="matetrip-ai"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_NAME="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo -e "${GREEN}설정 정보:${NC}"
echo "  AWS Account ID: ${AWS_ACCOUNT_ID}"
echo "  AWS Region: ${AWS_REGION}"
echo "  ECR Repository: ${ECR_REPOSITORY}"
echo "  Image Tag: ${IMAGE_TAG}"
echo "  Full Image Name: ${FULL_IMAGE_NAME}"
echo ""

# 1. Docker 이미지 빌드
echo -e "${GREEN}[1/4] Docker 이미지 빌드 중...${NC}"
docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker 이미지 빌드 완료${NC}"
else
    echo -e "${RED}✗ Docker 이미지 빌드 실패${NC}"
    exit 1
fi

# 2. ECR 로그인
echo -e "${GREEN}[2/4] ECR 로그인 중...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ ECR 로그인 완료${NC}"
else
    echo -e "${RED}✗ ECR 로그인 실패${NC}"
    exit 1
fi

# 3. 이미지 태그
echo -e "${GREEN}[3/4] 이미지 태그 지정 중...${NC}"
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${FULL_IMAGE_NAME}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 이미지 태그 지정 완료${NC}"
else
    echo -e "${RED}✗ 이미지 태그 지정 실패${NC}"
    exit 1
fi

# 4. ECR에 푸시
echo -e "${GREEN}[4/4] ECR에 이미지 푸시 중...${NC}"
docker push ${FULL_IMAGE_NAME}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ ECR에 이미지 푸시 완료${NC}"
else
    echo -e "${RED}✗ ECR에 이미지 푸시 실패${NC}"
    exit 1
fi

# 완료 메시지
echo ""
echo -e "${GREEN}=== 배포 완료! ===${NC}"
echo -e "이미지: ${FULL_IMAGE_NAME}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo "1. ECS Task Definition에서 이미지 URL 확인"
echo "2. ECS Task를 수동으로 실행하거나 EventBridge로 스케줄 설정"
echo ""
