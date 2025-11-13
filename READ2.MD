# MateTtrip Backend

## 필요한 패키지

- class-validator
- class-transformer
- typeorm
- @nestjs/typeorm
- pg
- @nestjs/config
- dotenv
- typeorm-model-generator

## 배포 가이드 (ECS Fargate)

### 사전 준비 사항

#### 1. AWS 인프라 설정

이미 구축되어 있어야 하는 리소스:

- ECR Repository
- ECS Cluster (Fargate)
- Application Load Balancer + Target Group
- VPC 및 Subnets (Private/Public)
- Security Groups
- RDS PostgreSQL 인스턴스
- ElastiCache Redis (또는 Redis 서버)

#### 2. CloudWatch Log Group 생성

```bash
aws logs create-log-group --log-group-name /ecs/matetrip-back
```

#### 3. GitHub Secrets 설정

GitHub 리포지토리의 Settings > Secrets and variables > Actions에서 다음 secrets 추가:

**AWS 인증용** (필수):

- `AWS_ACCESS_KEY_ID`: AWS IAM 사용자의 Access Key (배포용)
- `AWS_SECRET_ACCESS_KEY`: AWS IAM 사용자의 Secret Key (배포용)

**애플리케이션 환경변수**:

- `DATABASE_URL`: PostgreSQL 연결 URL (예: postgresql://user:pass@host:5432/db)
- `REDIS_HOST`: Redis 호스트 주소
- `REDIS_PORT`: Redis 포트 (기본: 6379)
- `JWT_SECRET`: JWT 토큰 시크릿 키
- `AWS_ACCESS_KEY_ID_APP`: 애플리케이션용 AWS Access Key (S3, Bedrock 등)
- `AWS_SECRET_ACCESS_KEY_APP`: 애플리케이션용 AWS Secret Key
- `OPENVIDU_SECRET`: OpenVidu 시크릿
- `OPENVIDU_URL`: OpenVidu 서버 URL

> **주의**: `AWS_ACCESS_KEY_ID`는 배포용, `AWS_ACCESS_KEY_ID_APP`는 애플리케이션용입니다. 다른 IAM 사용자를 사용하는 것을 권장합니다.

**배포용 IAM 사용자 필요 권한**:

- ECR: Push/Pull 권한
- ECS: UpdateService, RegisterTaskDefinition 권한
- IAM: PassRole 권한
- STS: GetCallerIdentity 권한

#### 4. IAM Role 생성 (선택사항)

필요한 경우 ecsTaskExecutionRole, ecsTaskRole을 생성하세요. 이미 존재하는 경우 스킵 가능합니다.

#### 5. GitHub Actions Workflow 설정

`.github/workflows/deploy-ecs.yml` 파일에서 다음 값들을 확인/수정:

```yaml
env:
  AWS_REGION: ap-northeast-2 # 실제 리전
  ECR_REPOSITORY: matetrip-back # ECR 리포지토리 이름
  ECS_SERVICE: matetrip-back-service # ECS 서비스 이름
  ECS_CLUSTER: matetrip-cluster # ECS 클러스터 이름
```

그리고 트리거 브랜치를 확인:

```yaml
on:
  push:
    branches:
      - main # 배포할 브랜치 이름
```

> **참고**: Task Definition의 환경변수는 GitHub Actions에서 자동으로 치환되므로 별도 수정이 필요 없습니다.

### 배포 프로세스

#### 자동 배포

1. 지정된 브랜치(기본: main)에 코드를 푸시
2. GitHub Actions가 자동으로 실행됨:
   - Docker 이미지 빌드
   - ECR에 푸시
   - GitHub Secrets에서 환경변수 주입
   - ECS Task Definition 업데이트
   - ECS Service 업데이트 (Rolling Update)
   - 헬스체크 확인 및 안정화 대기

#### 수동 배포

GitHub Actions 페이지에서 "Deploy to ECS Fargate" workflow를 선택하고 "Run workflow" 버튼 클릭

### Health Check 엔드포인트

애플리케이션에 health check 엔드포인트가 필요합니다.
Task Definition에서 `/health` 경로를 사용하도록 설정되어 있으므로,
NestJS에 다음과 같은 엔드포인트를 추가하세요:

```typescript
// src/health/health.controller.ts
import { Controller, Get } from "@nestjs/common";

@Controller("health")
export class HealthController {
  @Get()
  check() {
    return { status: "ok", timestamp: new Date().toISOString() };
  }
}
```

### 모니터링

#### CloudWatch Logs

- Log Group: `/ecs/matetrip-back`
- 애플리케이션 로그 확인 가능

#### ECS 콘솔

- 서비스 상태 및 배포 진행 상황 확인
- 작업(Task) 상태 모니터링
- 컨테이너 CPU/메모리 사용량 확인

### 롤백

문제 발생 시 이전 Task Definition으로 롤백:

```bash
aws ecs update-service \
  --cluster matetrip-cluster \
  --service matetrip-back-service \
  --task-definition matetrip-back:PREVIOUS_REVISION
```

### 로컬 테스트

배포 전 로컬에서 Docker 이미지 테스트:

```bash
# 이미지 빌드
docker build -t matetrip-back:test .

# 컨테이너 실행 (환경 변수 필요)
docker run -p 3000:3000 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_HOST="localhost" \
  -e REDIS_PORT="6379" \
  matetrip-back:test
```

### 문제 해결

#### 배포가 실패하는 경우

1. CloudWatch Logs에서 애플리케이션 로그 확인
2. ECS 콘솔에서 작업이 중지된 이유 확인
3. Security Group 설정 확인 (ALB → ECS, ECS → RDS/Redis)
4. GitHub Secrets가 모두 올바르게 설정되었는지 확인
5. GitHub Actions 로그에서 환경변수 치환 단계 확인

#### 헬스체크 실패

1. 애플리케이션이 올바른 포트(3000)에서 실행되는지 확인
2. `/health` 엔드포인트가 구현되어 있는지 확인
3. Security Group에서 ALB → ECS 통신이 허용되는지 확인

---

## AI POI Optimization API

Python AI 서버에서 최적화된 POI 순서를 WebSocket으로 브로드캐스트하는 API입니다.

### 환경 변수 설정

`.env` 파일에 다음 변수를 추가하세요 (선택사항, 보안 강화를 위해 권장):

```bash
AI_SERVER_API_KEY=your-secret-api-key-here
```

### API 엔드포인트

**POST** `/workspace/poi/optimize`

**Request Body:**

```json
{
  "workspaceId": "uuid-of-workspace",
  "planDayId": "uuid-of-plan-day",
  "poiIds": ["poi-id-1", "poi-id-2", "poi-id-3"],
  "apiKey": "your-secret-api-key-here" // 선택사항
}
```

**Response:**

```json
{
  "success": true,
  "message": "POI order optimized and broadcasted successfully"
}
```

### Python AI 서버 사용 예시

```python
import requests

# NestJS 서버 URL
NESTJS_SERVER_URL = "http://localhost:3000"  # 실제 서버 주소로 변경
API_KEY = "your-secret-api-key-here"  # .env의 AI_SERVER_API_KEY와 동일

def optimize_and_broadcast_pois(workspace_id: str, plan_day_id: str, optimized_poi_ids: list[str]):
    """
    AI가 최적화한 POI 순서를 NestJS 서버로 전송하여 WebSocket 브로드캐스트

    Args:
        workspace_id: 워크스페이스 ID
        plan_day_id: 일정 day ID
        optimized_poi_ids: AI가 최적화한 POI ID 리스트 (순서대로)
    """
    url = f"{NESTJS_SERVER_URL}/workspace/poi/optimize"

    payload = {
        "workspaceId": workspace_id,
        "planDayId": plan_day_id,
        "poiIds": optimized_poi_ids,
        "apiKey": API_KEY  # 선택사항: 보안을 위해 설정한 경우 포함
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        print(f"✅ POI 최적화 브로드캐스트 성공: {result}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ POI 최적화 브로드캐스트 실패: {e}")
        raise

# 사용 예시
if __name__ == "__main__":
    # AI가 계산한 최적화된 POI 순서
    optimized_order = [
        "poi-uuid-3",  # 첫 번째 방문
        "poi-uuid-1",  # 두 번째 방문
        "poi-uuid-5",  # 세 번째 방문
        "poi-uuid-2",  # 네 번째 방문
    ]

    optimize_and_broadcast_pois(
        workspace_id="workspace-uuid-123",
        plan_day_id="plan-day-uuid-456",
        optimized_poi_ids=optimized_order
    )
```

### Langchain Agent 통합 예시

```python
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

def optimize_poi_order_tool(input_str: str) -> str:
    """
    Langchain Tool로 사용할 수 있는 POI 최적화 함수

    Args:
        input_str: "workspace_id|plan_day_id|poi_id_1,poi_id_2,poi_id_3" 형식
    """
    try:
        parts = input_str.split("|")
        workspace_id = parts[0]
        plan_day_id = parts[1]
        poi_ids = parts[2].split(",")

        # 실제 AI 최적화 로직 (예: TSP 알고리즘, 거리 최소화 등)
        # 여기서는 예시로 단순히 역순으로 정렬
        optimized_poi_ids = list(reversed(poi_ids))

        # NestJS 서버로 브로드캐스트
        result = optimize_and_broadcast_pois(workspace_id, plan_day_id, optimized_poi_ids)

        return f"POI 최적화 완료. 새로운 순서: {' -> '.join(optimized_poi_ids)}"

    except Exception as e:
        return f"POI 최적화 실패: {str(e)}"

# Langchain Tool 정의
optimize_tool = Tool(
    name="OptimizePOIOrder",
    func=optimize_poi_order_tool,
    description="특정 plan_day의 POI 순서를 최적화하고 WebSocket으로 브로드캐스트합니다. "
                "입력 형식: 'workspace_id|plan_day_id|poi_id_1,poi_id_2,poi_id_3'"
)

# Agent에 Tool 추가
llm = ChatOpenAI(temperature=0)
tools = [optimize_tool]  # 다른 tool들과 함께 사용 가능

# Agent 실행
# agent = create_react_agent(llm, tools, prompt_template)
# agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
```

### 동작 방식

1. **Python AI 서버**가 사용자 채팅에서 "장소 최적화 해줘" 요청을 받음
2. AI가 해당 `plan_day_id`의 POI들을 최적화 (예: TSP 알고리즘)
3. 최적화된 순서를 **NestJS API (`/workspace/poi/optimize`)**로 POST 요청
4. **NestJS**가 Redis 업데이트 + **WebSocket으로 모든 클라이언트에 브로드캐스트**
5. 실시간으로 연결된 모든 사용자가 최적화된 순서를 즉시 확인
