# MateTrip AI

AI 기반 여행 계획 및 추천 시스템

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [API 엔드포인트](#api-엔드포인트)
- [데이터베이스 스키마](#데이터베이스-스키마)
- [환경 변수 설정](#환경-변수-설정)
- [배포](#배포)

## 프로젝트 소개

**MateTrip AI**는 AWS Bedrock과 LangGraph를 활용한 지능형 여행 계획 및 추천 플랫폼입니다. 사용자와의 대화를 통해 맞춤형 여행지를 추천하고, 최적화된 경로를 생성하며, 협업 기반 여행 일정을 관리할 수 있습니다.

<img width="2376" height="3360" alt="POST V  2 - A1(small) (1)" src="https://github.com/user-attachments/assets/610ca8b3-90d6-44f9-9329-38eb1431241b" />


### 핵심 가치

- **AI 대화형 에이전트**: Claude 4.5 Haiku를 활용한 자연스러운 대화형 여행 컨설팅
- **개인화 추천**: 벡터 임베딩과 사용자 행동 데이터 기반 맞춤형 장소 추천
- **경로 최적화**: Google OR-Tools를 활용한 TSP 기반 최적 여행 경로 생성
- **실시간 협업**: 다중 사용자 워크스페이스에서 함께 여행 계획 수립

## 주요 기능

### 1. AI 대화형 여행 에이전트

- **LangGraph 기반 상태 관리**: 복잡한 대화 흐름을 효율적으로 관리
- **인텐트 분류**: NEW_SEARCH, REFINEMENT, CONVERSATION, FOLLOW_UP 자동 분류
- **컨텍스트 인식**: 대화 기록을 바탕으로 맥락에 맞는 응답 생성
- **도구 통합**: 장소 추천, 워크스페이스 관리, POI 분석, 경로 최적화 도구 활용

**엔드포인트**: `POST /chat/v2` (LangGraph 기반, 권장)

### 2. 장소 추천 시스템

#### 추천 전략

1. **주변 장소 추천** (`recommend_nearby_places`)

   - Kakao Local API를 통한 지오코딩
   - PostGIS 공간 쿼리 (ST_DWithin)
   - 카테고리 필터링 (음식, 숙박, 레포츠, 자연, 인문)
   - 반경 기반 검색 (기본 5km)

2. **지역별 인기 장소** (`recommend_popular_places_in_region`)

   - 사용자 행동 데이터 기반 인기도 산출
   - POI_MARK, POI_SCHEDULE 이벤트 집계
   - 지역별 상호작용 횟수 정렬

3. **협업 필터링** (`recommend_places_by_all_users`)

   - 워크스페이스 참여자 전체 선호도 반영
   - pgvector 코사인 유사도 검색
   - 프로필 + 행동 임베딩 결합

4. **장소 대체 추천** (`replace_places`)
   - 컨텍스트 인식 대안 제안
   - 이전 추천 장소 제외
   - 카테고리/위치 일관성 유지

#### 데이터 수집 파이프라인

```
한국관광공사 API → 네이버 검색 (리뷰 URL) → Crawl4AI (콘텐츠 크롤링)
→ 리뷰 필터링 (광고 제거) → Bedrock LLM (태그/요약 생성) → 임베딩 생성 → DB 저장
```

**특징**:

- 자동화된 데이터 수집 및 처리
- AI 기반 리뷰 요약 및 태그 생성
- 1024차원 벡터 임베딩으로 의미론적 검색 지원

### 3. 경로 최적화

- **TSP 알고리즘**: Google OR-Tools Guided Local Search
- **실시간 경로 계산**: Kakao Mobility API로 거리/시간 매트릭스 생성
- **제약 조건 지원**: 고정 시작/종료 지점, 순환/비순환 경로
- **병렬 처리**: 여러 경로 구간 동시 계산

**엔드포인트**: `POST /optimization/route`

### 4. 사용자 행동 추적 및 개인화

#### 행동 이벤트 유형

- `POI_MARK`: 장소 북마크
- `POI_SCHEDULE`: 일정에 추가
- `POI_UNMARK`: 북마크 해제
- `POI_UNSCHEDULE`: 일정에서 제거

#### 행동 임베딩

- 장소 임베딩의 가중 평균 계산
- 스케줄링 이벤트에 더 높은 가중치 부여
- RabbitMQ를 통한 비동기 집계
- `user_behavior_embeddings` 테이블에 저장

#### 통합 흐름

```
사용자 행동 이벤트 → RabbitMQ Queue → Consumer 처리
→ 선호도 벡터 업데이트 → 개인화 추천에 활용
```

### 5. Backend 연동 - AI 에이전트 통합

MateTrip AI는 NestJS 백엔드(`matetrip-backend`)와 긴밀하게 통합되어 AI 기반 여행 계획 기능을 제공합니다.

#### AI 서버가 Backend에 제공하는 기능

**1. 대화형 AI 에이전트 (`POST /chat/v2`)**

- Backend(NestJS)의 Chat Gateway에서 `@AI` 멘션 감지 시 호출
- 사용자 의도 분석 및 적절한 도구 실행 (장소 추천, 경로 최적화 등)
- `tool_data` 포함 응답으로 Frontend 액션 트리거
  - 예: 장소 추천 시 `recommended_places` 데이터를 담아 반환.
  - Frontend가 이를 받아 지도에 마커 표시 또는 리스트 렌더링

**2. AI 에이전트 도구 (Tools)**
AI 에이전트가 사용자 요청에 따라 자동으로 선택하여 실행하는 도구들입니다:

**(1) 장소 추천 도구 (`place_tool.py`)**

- `recommend_nearby_places`: 특정 위치 주변 장소 추천
  - 예: "강남역 주변 맛집", "제주공항 근처 숙소"
  - Kakao Local API로 좌표 변환 → PostGIS 공간 쿼리
- `recommend_popular_places_in_region`: 광역 지역 인기 장소
  - 예: "제주도 인기 장소", "부산 핫플"
  - 사용자 행동 데이터(POI_MARK, POI_SCHEDULE) 기반 인기도 산출
- `replace_places`: 추천 장소 대체
  - 예: "1번이랑 3번 빼고 다른 거로 바꿔줘"
  - 기존 추천 제외 후 새로운 장소 제안

**(2) 워크스페이스 도구 (`workspace_tool.py`)**

- `recommend_places_by_all_users`: 협업 필터링 추천
  - 워크스페이스 참여자 전체의 프로필 + 행동 임베딩 결합
  - Backend API 호출: `GET /workspace/{workspace_id}/recommendations`
- `add_schedule_by_place`: 장소를 일정에 추가
  - 예: "1번 장소 1일차에 넣어줘", "~ 2일차 일정에 넣어줘"
  - Backend API 호출: `POST /workspace/schedule/add-by-place`
- `find_place_id_by_name`: 장소 이름으로 ID 조회
  - Backend API 호출: `GET /places/search?name={place_name}`
- `get_place_reviews`: 장소 리뷰 조회
  - Backend API 호출: `GET /place-user-reviews/place/{place_id}`

**(3) POI 분석 도구 (`poi_tool.py`)**

- `recommend_next_poi`: 일정 분석 및 부족 카테고리 추천
  - 예: "다음에 뭘 추가하면 좋을까?", "일정이 괜찮은지 확인해줘"
  - 숙박 시설 부족 여부 체크 (N박 = N개 숙소 필요)
  - 식사 장소 부족 여부 체크 (하루 2~3끼 기준)
  - 카테고리 다양성 분석 후 부족한 카테고리 장소 추천

**(4) 여행 코스 생성 도구 (`route_tool.py`)**

- `create_travel_route`: 경유지 기반 여행 코스 생성
  - 예: "제주도 연동에서 시작해서 해녀촌을 경유하고 김영해수욕장을 거치는 코스"
  - 각 경유지마다 근처 장소 추천 (반경/카테고리 지정 가능)
  - N박 M일 형식으로 일정 구성

**3. 경로 최적화 (`POST /optimization/route`)**

- Backend에서 POI 리스트와 함께 요청
- TSP 알고리즘으로 최적 경로 계산 후 순서 반환
- Backend의 `PoiGateway.broadcastPoiReorder()`를 통해 결과를 WebSocket으로 브로드캐스트
- 모든 협업 참여자에게 실시간 경로 업데이트

#### Backend가 AI 서버에 제공하는 기능

**1. 사용자 행동 데이터 수집 (RabbitMQ)**

- POI Gateway에서 사용자 행동 이벤트 발생 시 RabbitMQ Queue로 전송
  - `POI_MARK`: 장소 북마크
  - `POI_SCHEDULE`: 일정에 추가
  - `POI_UNMARK`: 북마크 해제
  - `POI_UNSCHEDULE`: 일정에서 제거
- AI 서버의 Consumer가 이벤트 수신 → 사용자 행동 임베딩 업데이트
- 업데이트된 임베딩은 개인화 추천에 즉시 반영

**2. 워크스페이스 및 사용자 컨텍스트**

- AI 에이전트가 추천 시 필요한 정보:
  - 워크스페이스 참여자 목록 및 프로필
  - 사용자 선호도 (여행 스타일, 성향, MBTI)
  - 기존 일정 및 POI 목록
- Backend DB에서 관리되며 AI 서버가 필요 시 조회

**3. WebSocket을 통한 실시간 통신**

- Chat Gateway: AI 응답을 워크스페이스 참여자 전체에게 실시간 브로드캐스트
- POI Gateway: AI가 추천한 장소를 자동으로 POI로 추가 시 실시간 동기화

#### 통합 아키텍처 흐름

```
[사용자] → [Frontend] → [Backend Chat Gateway]
   ↓ (@AI 멘션)
[Backend] → [AI Server /chat/v2] → [LangGraph Agent]
   ↓ (도구 실행)
[장소 추천 도구] → [PostgreSQL 벡터 검색] → [추천 결과]
   ↓
[AI 응답 + tool_data] → [Backend] → [WebSocket] → [모든 참여자 Frontend]
   ↓
[Frontend] 지도에 추천 장소 표시 + POI 북마크 옵션 제공
   ↓
[사용자 POI_MARK] → [Backend POI Gateway] → [RabbitMQ]
   ↓
[AI Server Consumer] → [행동 임베딩 업데이트] → [다음 추천 개선]
```

이러한 양방향 연동을 통해 AI 서버는 지속적으로 학습하며, 사용자에게 점점 더 정확한 추천을 제공합니다.

## 기술 스택

### 백엔드 프레임워크

- **FastAPI** (v0.121.0+): 고성능 비동기 웹 프레임워크
- **Python 3.13**: 최신 Python 런타임
- **uvicorn**: ASGI 서버

### AI & 머신러닝

- **AWS Bedrock**: AI 인프라
  - **Claude 4.5 Haiku** (`global.anthropic.claude-haiku-4-5-20251001-v1:0`): LLM
  - **Amazon Titan Embeddings v2**: 1024차원 벡터 임베딩
- **LangChain** (v1.0.5+): AI 에이전트 프레임워크
  - `langchain-aws`: Bedrock 통합
  - `langchain-community`: 커뮤니티 도구
  - `langchain-core`: 핵심 추상화
- **LangGraph**: 복잡한 에이전트 워크플로우를 위한 상태 그래프 프레임워크
- **pgvector**: PostgreSQL 벡터 유사도 검색

### 데이터베이스 & 스토리지

- **PostgreSQL** (with pgvector extension): 메인 데이터베이스
- **SQLAlchemy** (v2.0.44): 비동기 ORM
- **GeoAlchemy2**: 지리공간 데이터 지원
- **PostGIS**: 공간 쿼리 (Geography type)

### 데이터 수집 & 크롤링

- **Crawl4AI** (v0.7.6): 현대적인 웹 스크래핑 프레임워크
- **BeautifulSoup4**: HTML 파싱
- **Selenium**: 브라우저 자동화
- **httpx**: 비동기 HTTP 클라이언트

### 경로 최적화

- **OR-Tools** (v9.14.6206): Google의 최적화 라이브러리 (TSP)

### 메시지 큐

- **RabbitMQ** (via pika v1.3.2): 비동기 작업 처리
  - 프로필 임베딩 큐
  - 행동 임베딩 큐

### 외부 API

- **Kakao Mobility API**: 실시간 경로 및 거리 매트릭스
- **Naver Search API**: 리뷰 URL 발견
- **Korea Tour API**: 공식 관광 데이터
- **Kakao Local API**: 지오코딩 및 장소 검색

### 배포

- **Docker**: 컨테이너화
- **GitHub Actions**: CI/CD
- **AWS**: 클라우드 인프라
  - EC2: 컴퓨팅
  - RabbitMQ (AWS MQ): 메시지 브로커
  - RDS PostgreSQL: 데이터베이스
  - S3: 환경 설정 저장소

## 프로젝트 구조

```
matetrip-ai/
├── app/
│   ├── agent/                    # LangGraph AI 에이전트 구현
│   │   ├── nodes/                # 에이전트 실행 노드
│   │   │   ├── router_node.py    # 인텐트 분류
│   │   │   ├── agent_node.py     # 메인 에이전트 실행
│   │   │   └── post_processors/  # 도구별 후처리
│   │   ├── graph.py              # LangGraph 상태 그래프 정의
│   │   ├── state.py              # 에이전트 상태 스키마
│   │   ├── builder.py            # 에이전트 체인 빌더 v1
│   │   └── builder2.py           # 에이전트 체인 빌더 v2(최종)
│   │
│   ├── routes/                   # FastAPI 엔드포인트
│   │   ├── chat.py               # Lanchaing 기반 채팅 (이전)
│   │   ├── chat_v2.py            # LangGraph 기반 채팅 (메인)
│   │   ├── route.py              # 경로 최적화
│   │   └── planner.py            # 여행 일정 생성
│   │
│   ├── tools/                    # LangChain 도구
│   │   ├── place_tool.py         # 장소 추천 도구
│   │   ├── workspace_tool.py     # 워크스페이스 관리
│   │   ├── poi_tool.py           # POI 도구
│   │   └── route_tool.py         # 경로 최적화 도구
│   │
│   ├── service/                  # 비즈니스 로직 레이어
│   │   ├── crawling/             # 데이터 수집 서비스
│   │   │   ├── tour_api_service.py      # 한국관광공사 API
│   │   │   ├── naver_search_service.py  # 네이버 리뷰 URL 검색
│   │   │   ├── crawl_service.py         # Crawl4AI 크롤링
│   │   │   ├── review_service.py        # 리뷰 처리
│   │   │   ├── review_filter_service.py # 광고 필터링
│   │   │   └── bedrock_llm_service.py   # 태그/요약 생성
│   │   ├── place_service.py              # 장소 관리
│   │   ├── place_embedding_service.py    # 장소 벡터 임베딩
│   │   ├── bedrock_embedding_service.py  # Bedrock 임베딩 클라이언트
│   │   ├── route_optimization_service.py # TSP 최적화
│   │   ├── kakao_mobility_service.py     # 경로/거리 API
│   │   ├── behavior_service.py           # 사용자 행동 추적
│   │   ├── agent_service.py              # 에이전트 실행 로직
│   │   └── poi_analysis_service.py       # POI 분석
│   │
│   ├── repository/               # 데이터 액세스 레이어
│   │   ├── place_repository.py   # 장소 CRUD & 공간 쿼리
│   │   ├── recommendation_repository.py # 벡터 유사도 검색
│   │   └── behavior_repository.py # 사용자 행동 데이터
│   │
│   ├── models/                   # SQLAlchemy ORM 모델
│   │   ├── place.py              # 장소 테이블
│   │   ├── workspace.py          # 워크스페이스 (여행 계획)
│   │   ├── plan_day.py           # 일별 일정
│   │   ├── user.py & profile.py  # 사용자 데이터
│   │   ├── review.py             # 장소 리뷰
│   │   └── user_behavior.py      # 행동 이벤트 & 임베딩
│   │
│   ├── schemas/                  # Pydantic DTO
│   │   ├── place.py              # 장소 요청/응답
│   │   ├── routes.py             # 경로 최적화 스키마
│   │   ├── chat.py               # 채팅 메시지
│   │   ├── plan.py               # 여행 계획
│   │   ├── behavior.py           # 사용자 행동
│   │   └── tool_response.py      # 도구 출력 스키마
│   │
│   ├── infra/                    # 인프라 레이어
│   │   ├── consumer.py           # RabbitMQ 컨슈머
│   │   ├── messaging_handler.py  # 메시지 처리
│   │   └── *_notification.py     # 백엔드 알림 핸들러
│   │
│   ├── core/                     # 핵심 설정
│   │   ├── llm.py                # 글로벌 LLM 인스턴스
│   │   ├── memory.py             # 채팅 히스토리 관리
│   │   └── constants.py          # 앱 상수
│   │
│   ├── utils/                    # 유틸리티 함수
│   │   ├── embedding_utils.py    # 벡터 연산
│   │   ├── geocoding.py          # 주소 → 좌표 변환
│   │   ├── place_normalizer.py   # 장소 데이터 정규화
│   │   └── backend_notifier.py   # 백엔드 알림
│   │
│   ├── common/                   # 공통 컴포넌트
│   │   ├── config.py             # Pydantic 설정
│   │   ├── logger.py             # Loguru 설정
│   │   └── category_mapping.py   # 카테고리 정규화
│   │
│   ├── enums/                    # 열거형 타입
│   │   ├── place.py              # 장소 관련 enum
│   │   ├── travel.py             # 여행 선호도
│   │   └── user_behavior.py      # 행동 이벤트 타입
│   │
│   ├── data/                     # 정적 데이터
│   │   └── tour_categories.py    # 관광 API 카테고리 매핑
│   │
│   └── database/                 # 데이터베이스 설정
│       ├── database.py           # 비동기 세션 팩토리
│       └── init_db.py            # DB 초기화
│
├── scripts/                      # 데이터 처리 스크립트
│   ├── collect_places_tour.py    # 관광공사 API 수집
│   ├── process_existing_places*.py # 배치 리뷰 처리
│   └── fix_null_regions.py       # 데이터 정리
│
├── test/                         # 테스트 스위트
│   └── test_route_optimization.py
│
├── main.py                       # FastAPI 애플리케이션 진입점
├── schema.sql                    # 데이터베이스 스키마
├── entrypoint.sh                 # Docker 컨테이너 시작 스크립트
├── Dockerfile                    # 멀티스테이지 빌드
├── docker-compose.yml            # 로컬 PostgreSQL + pgvector
├── pyproject.toml                # uv 프로젝트 설정
└── .github/workflows/            # CI/CD 파이프라인
    └── deploy-ai-new.yml         # 배포 자동화
```

## 설치 및 실행

### 사전 요구사항

- Python 3.13+
- PostgreSQL with pgvector extension
- Docker & Docker Compose (선택사항)
- uv 패키지 매니저

### 1. uv 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 프로젝트 클론 및 의존성 설치

```bash
git clone <repository-url>
cd matetrip-ai
uv sync
```

### 3. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성하고 필요한 환경 변수를 설정합니다. ([환경 변수 설정](#환경-변수-설정) 섹션 참조)

### 4. 데이터베이스 설정

> **참고**: 프로젝트에 포함된 `docker-compose.yml`은 로컬 개발 환경용 임시 설정 파일입니다. 프로덕션 환경에서는 **AWS RDS PostgreSQL을 사용**합니다.

#### 로컬 개발용 (Docker Compose)

```bash
docker-compose up -d
```

#### 프로덕션 환경

AWS RDS PostgreSQL (pgvector, PostGIS extension 활성화 필요)

### 5. 애플리케이션 실행

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

> **참고**: 애플리케이션 실행 시 백그라운드에서 자동으로 RabbitMQ Consumer와 장소 처리 스크립트가 함께 실행됩니다. (`entrypoint.sh` 참조)

### 6. 데이터 수집 스크립트 실행 (선택사항)

```bash
# 한국관광공사 API에서 장소 수집
uv run python scripts/collect_places_tour.py

# 기존 장소에 대한 리뷰 처리 (병렬, 배치 크기: 5)
uv run python scripts/process_existing_places_parallel.py --batch-size 5
```

### 7. API 문서 확인

브라우저에서 `http://localhost:8000/docs` 접속

## API 엔드포인트

### 채팅 & 에이전트

- `POST /chat/v2` - LangGraph 기반 대화형 에이전트 (메인)
- `POST /chat` - LanChain 기반 클래식 에이전트 (이전)
- `GET /chat/v2/health` - 헬스 체크

### 경로 최적화

- `POST /optimization/route` - POI 경로 최적화 (TSP)

### 루트

- `GET /` - API 상태 확인
- `GET /chat/v2/health` - 헬스 체크

## 데이터베이스 스키마

자세한 스키마는 `schema.sql` 파일을 참조하세요.

### 주요 테이블

- **places**: 벡터 임베딩을 포함한 장소 정보 (PostGIS Geography 타입, VECTOR(1024))
- **place_review**: 장소 리뷰 데이터
- **workspace**: 여행 계획 워크스페이스
- **plan_day**: 일별 여행 일정
- **poi**: 관심 지점 (MARKED 또는 SCHEDULED 상태)
- **user_behavior_events**: 사용자 행동 이벤트 (POI_MARK, POI_SCHEDULE 등)
- **user_behavior_embeddings**: 집계된 사용자 선호도 벡터
- **profile**: 사용자 프로필 및 여행 선호도 (VECTOR(1024))

### 필수 확장

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- UUID 생성
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector
CREATE EXTENSION IF NOT EXISTS postgis;    -- 공간 연산
```

## 환경 변수 설정

`.env` 파일 예시:

```bash
# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
BEDROCK_LLM_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0

# Database
DB_HOST=localhost # AWS라면 AWS
DB_PORT=5432
DB_USER=matetrip
DB_PASSWORD=your_password
DB_NAME=postgres

# External APIs
TOUR_API_KEY=your_tour_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
KAKAO_REST_API_KEY=your_kakao_rest_api_key
KAKAO_MOBILITY_API_KEY=your_kakao_mobility_api_key

# RabbitMQ
AWS_RABBITMQ_URL=amqps://user:pass@host:5671
RABBITMQ_PROFILE_QUEUE=profile_embedding_queue
RABBITMQ_BEHAVIOR_QUEUE=behavior_embedding_queue

# Backend Integration
NESTJS_SERVER_URL=http://localhost:3000
REACT_URL=http://localhost:3001
AI_SERVER_API_KEY=your_ai_server_api_key

# Optional
LOG_LEVEL=INFO
```

## 배포

### GitHub Actions CI/CD

- **트리거**: `dev` 브랜치에 push
- **워크플로우**: `.github/workflows/deploy-ai-new.yml`
- Self-hosted runner (EC2)에서 자동 배포

### 주요 서비스

애플리케이션 실행 시 다음 서비스가 함께 실행됩니다:

- FastAPI 서버 (포트 8000)
- RabbitMQ Consumer (사용자 행동 임베딩 처리)
- 장소 데이터 처리 스크립트 (백그라운드)

## 아키텍처 특징

### 1. LangGraph 상태 관리

- 도구별 전용 후처리 노드
- 중앙화된 라우팅 로직 (`TOOL_POSTPROCESSING_ROUTES`)
- MemorySaver 체크포인터로 세션 지속성 보장

### 2. 사용자 의도 인식 컨텍스트 윈도우

- `NEW_SEARCH`: 마지막 사용자 메시지만 전달
- `REFINEMENT`/`CONVERSATION`: 전체 히스토리 (최대 10개)
- Bedrock 메시지 포맷 검증

### 3. 벡터 검색 최적화

- pgvector 코사인 유사도 연산자 (`<=>`)
- IVFFlat 인덱스로 서브리니어 검색
- 벡터 비교 전 카테고리/지역으로 사전 필터링

### 4. 공간 쿼리

- PostGIS Geography 타입 (SRID 4326)
- ST_DWithin으로 효율적인 반경 검색
- Geography 컬럼에 GiST 인덱스

### 5. 병렬 처리

- 세마포어로 동시성 제어 (최대 5개) Crawl4AI
- 배치 임베딩 생성
- 백그라운드 RabbitMQ 컨슈머

### 6. 에러 처리 및 복원력

- 웹 스크래핑 시 지수 백오프 재시도
- Rate Limiting 대응 3회 재시도 + 지터
- TSP 실패 시 순차 정렬로 폴백
- 모든 계층에서 빈 결과 처리

## 라이선스

Copyright © 2025 MateTrip Team. All rights reserved.

---

**개발 팀**: MateTrip AI Team
**최종 업데이트**: 2025-12-02
