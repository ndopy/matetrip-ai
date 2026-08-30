<h1 align="center">MateTrip AI</h1>

<p align="center">
  AI 기반 실시간 협업 여행 플래너 & 추천 엔진<br/>
  <b>LangGraph · Google Gemini · PostGIS · pgvector · OR-Tools · RabbitMQ</b>
</p>

<p align="center">
  <img width="800" alt="MateTrip AI Poster" src="https://github.com/user-attachments/assets/610ca8b3-90d6-44f9-9329-38eb1431241b" />
</p>

---

## ✨ Introduction

**MateTrip AI**는 여행 계획에 필요한 복잡한 기능들을 하나의 AI 백엔드로 통합한 **여행 특화 AI 오케스트레이션 서버**입니다.

LangGraph 기반 대화형 에이전트부터 장소 처리·경로 최적화·행동 임베딩까지모든 기능이 FastAPI 기반 서비스로 구성되어 있으며, NestJS 기반 MateTrip 메인 서비스와 연동되어 채팅 한 줄로 여행 일정을 그릴 수 있도록 설계되었습니다.

---

## 🗂 ERD Overview   
<a href="https://www.erdcloud.com/d/vZioi9856wurCMtAq" target="_blank" rel="noopener noreferrer">
  ERD 링크
</a>
<img width="1359" height="735" alt="cropped_erd" src="https://github.com/user-attachments/assets/631312a3-4df8-461a-90ac-65701ec795ac" />

---

## 📌 주요 기능 (Highlights)

- 🤖 **LangGraph 기반 대화형 여행 에이전트**
  - Google Gemini + LangGraph로 인텐트 분류, 도구 선택, 상태 관리
  - `NEW_SEARCH / REFINEMENT / CONVERSATION / FOLLOW_UP` 자동 분류


- 👥 **실시간 협업 여행 플래너 연동**
  - NestJS Backend와 연동해 워크스페이스 일정/POI를 조작하는 도구 제공
  - AI가 추천한 장소를 바로 일정에 추가하고 WebSocket으로 동기화

- 🔄 **지속 학습형 사용자 행동 피드백**
  - RabbitMQ Queue로 행동 이벤트 수집
  - Consumer가 사용자 행동 임베딩을 지속 업데이트 → 다음 추천에 반영

- 🗺️ **경로 최적화 (TSP)**
  - Kakao Mobility Distance Matrix + Google OR-Tools
  - 고정 출발/도착지, 순환/비순환 경로 지원
  - 실패 시 단순 순차 폴백 전략 내장


---

## 🧠 시스템 개요

MateTrip AI는 “**AI 전용 백엔드 마이크로서비스**” 역할을 합니다.

```text
[사용자] 
   ↓ (채팅, @AI 멘션)
[Frontend] ──> [NestJS Backend Chat Gateway]
   ↓ (HTTP)
[MateTrip AI /chat/v2] ──> [LangGraph Agent]
   ↓ (도구 실행)
[PostgreSQL + PostGIS + pgvector] / [외부 API들]
   ↓
[AI 응답 + tool_data] ──> [Backend] ──> [WebSocket] ──> [모든 참여자 화면 반영]

[사용자 행동] ─> [Backend POI Gateway] ─> [RabbitMQ] ─> [AI Consumer] ─> [행동 임베딩 업데이트]
```





### 핵심 가치

- **AI 대화형 에이전트**: Google Gemini를 활용한 자연스러운 대화형 여행 컨설팅
- **실시간 협업**: 다중 사용자 워크스페이스에서 함께 여행 계획 수립
- **경로 최적화**: Google OR-Tools를 활용한 TSP 기반 최적 여행 경로 생성
- **지속 학습형 사용자 행동 피드백**: 사용자 행동을 기반으로 취향을 학습해 이후 추천 시스템에서 활용할 개인화 데이터 기반을 생성

## 🧩 기능 상세

### 🤖 1. AI 대화형 여행 에이전트 (POST /chat/v2)

- **LangGraph 상태 그래프**
  - `router_node` : 인텐트 분류 (NEW_SEARCH / REFINEMENT / …)
  - `agent_node` : LLM 호출 및 도구 선택
  - `tool_node` : LangChain Tool 실행
  - 각 도구별 전용 `Post Processor`를 두어 tool_data를 깔끔하게 가공

- **컨텍스트 전략**
  - NEW_SEARCH: 마지막 사용자 메시지만 전달
  - REFINEMENT / CONVERSATION: 최근 히스토리 최대 10개까지 전달
  - LLM 포맷에 맞춰 메시지 변환 및 안전성 검증

**엔드포인트**: `POST /chat/v2` (LangGraph 기반, 권장)

### 🛠 2. AI 에이전트 도구 (Tools)

AI 에이전트가 사용자 요청에 따라 자동으로 선택하여 실행하는 도구들입니다:

**1‍⃣ 장소 추천 도구 (`place_tool.py`)**
<img width="811" height="562" alt="image" src="https://github.com/user-attachments/assets/9c672e43-8d63-4f75-a4df-f9dfcd09e644" />

- `recommend_nearby_places`: 특정 위치 주변 장소 추천
  - 예: "강남역 주변 맛집", "제주공항 근처 숙소"
  - Kakao Local API로 좌표 변환 → PostGIS 공간 쿼리
- `recommend_popular_places_in_region`: 광역 지역 인기 장소
  - 예: "제주도 인기 장소", "부산 핫플"
  - 사용자 행동 데이터(POI_MARK, POI_SCHEDULE) 기반 인기도 산출
- `replace_places`: 추천 장소 대체
  - 예: "1번이랑 3번 빼고 다른 거로 바꿔줘"
  - 기존 추천 제외 후 새로운 장소 제안

**2‍⃣ 워크스페이스 도구 (`workspace_tool.py`)**
<img width="1827" height="930" alt="image" src="https://github.com/user-attachments/assets/cd5b0113-ddf0-4a26-925d-07e621499095" />

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

**3‍⃣ 일정 분석 도구 (`poi_tool.py`)**
<img width="803" height="443" alt="image" src="https://github.com/user-attachments/assets/b4cc0671-fa53-493a-9f2a-734e51f96fda" />

- `recommend_next_poi`: 일정 분석 및 부족 카테고리 추천
  - 예: "다음에 뭘 추가하면 좋을까?", "일정이 괜찮은지 확인해줘"
  - 숙박 시설 부족 여부 체크 (N박 = N개 숙소 필요)
  - 식사 장소 부족 여부 체크 (하루 2~3끼 기준)
  - 카테고리 다양성 분석 후 부족한 카테고리 장소 추천

**4‍⃣ 여행 코스 생성 도구 (`route_tool.py`)**
<img width="812" height="438" alt="image" src="https://github.com/user-attachments/assets/b11a1108-5a6b-416b-9b00-5b75ad4d3163" />

- `create_travel_route`: 경유지 기반 여행 코스 생성
  - 각 경유지마다 근처 장소 추천 (반경/카테고리 지정 가능)
  - 코스 생성 시 자동으로 일정으로 등록 : 기존 등록된 일정은 제외하도록 설계 
  - N박 M일 형식으로 일정 구성
  - 예: "제주도 연동에서 시작해서 해녀촌을 경유하고 김영해수욕장을 거치는 코스"


### 🧭 3. 경로 최적화
**엔드포인트**: `POST /optimization/route`

- Kakao Mobility API로 POI 간 거리·시간 매트릭스 생성
- Google OR-Tools의 Guided Local Search로 TSP 최적화
- 고정 출발지/도착지, 순환/비순환, 일부 경유지 고정 등 제약 조합 가능

### 🎯 4. 사용자 행동 추적 및 개인화

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

MateTrip AI는 NestJS 백엔드(`matetrip-backend`)와 긴밀하게 통합되어 채팅, 일정, POI, 워크스페이스 단위 기능을 AI로 제어합니다.

### 통합 아키텍처 흐름

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

## 🧱 기술 스택

### ⚙️ 언어, 프레임워크

- **FastAPI** (v0.121.0+): 고성능 비동기 웹 프레임워크
- **Python 3.13**: 최신 Python 런타임
- **uvicorn**: ASGI 서버

### 🤖 AI & 머신러닝

- **Google Gemini**: AI 인프라 (팀 프로젝트 종료 후 AWS 크레딧 만료로 Bedrock에서 교체, 아래 "AWS 의존성 제거" 참고)
  - **`gemini-3.6-flash`**: LLM
  - **`gemini-embedding-001`**: 768차원 벡터 임베딩 (프로필용)
- **Amazon Titan Embeddings v2** (레거시): `places`/`place_review`의 장소 임베딩(1024차원)은 개발 당시 Titan으로 미리 계산해 DB에 저장해둔 값을 그대로 재사용 중이며, 더 이상 실시간으로 호출하지 않습니다.
- **LangChain** (v1.0.5+): AI 에이전트 프레임워크
  - `langchain-google-genai`, `langchain-community`, `langchain-core`
- **LangGraph**: 상태 기반 에이전트 워크플로우
- **pgvector**: PostgreSQL 벡터 유사도 검색

### 🗄 데이터베이스 & 스토리지

- **PostgreSQL** (with pgvector extension): 메인 데이터베이스
- **SQLAlchemy** (v2.0.44): 비동기 ORM
- **GeoAlchemy2**: 지리공간 데이터 지원
- **PostGIS**: 공간 쿼리 (Geography type)

### 🌐 데이터 수집 & 크롤링

- **Crawl4AI**
- **BeautifulSoup4**
- **Selenium**
- **httpx**

### 경로 최적화
- **OR-Tools** (v9.14.6206): Google의 최적화 라이브러리 (TSP)

### 메시지 큐

- **RabbitMQ** (via pika v1.3.2): 비동기 작업 처리
  - 프로필 임베딩 큐
  - 행동 임베딩 큐

### 외부 API

- **Kakao Mobility API**
- **Naver Search API**
- **Korea Tour API**
- **Kakao Local API**

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
│   │   ├── bedrock_embedding_service.py  # Bedrock 임베딩 클라이언트 (장소 데이터 수집용, 레거시)
│   │   ├── gemini_embedding_service.py   # Gemini 임베딩 클라이언트 (프로필용)
│   │   ├── route_optimization_service.py # TSP 최적화
│   │   ├── kakao_mobility_service.py     # 경로/거리 API
│   │   ├── behavior_service.py           # 사용자 행동 추적
│   │   ├── agent_service.py              # 에이전트 실행 로직
│   │   └── poi_analysis_service.py       # POI 분석
│   │
│   ├── repository/               # 데이터 액세스 레이어
│   │   ├── place_repository.py   # 장소 CRUD & 공간 쿼리
│   │   ├── recommendation_repository.py # 벡터 유사도 검색
│   │   ├── behavior_repository.py # 사용자 행동 데이터
│   │   └── profile_repository.py  # 프로필 조회 & 임베딩 저장
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

### 1. uv 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 프로젝트 클론

```bash
git clone <repository-url>
cd matetrip-ai
```

### 3. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성하고 필요한 환경 변수를 설정합니다. ([환경 변수 설정](#환경-변수-설정) 섹션 참조)

### 4. 데이터베이스 설정

> **참고**: 프로젝트에 포함된 `docker-compose.yml`은 로컬 개발 환경용 임시 설정 파일입니다. 프로덕션 환경에서는 **AWS RDS PostgreSQL을 사용**합니다.

### 5. 애플리케이션 실행

```bash
uv run main.py 
```
uv는 자동으로 의존성도 설치해줍니다.

> **참고**: 애플리케이션 실행 시 백그라운드에서 자동으로 RabbitMQ Consumer와 장소 처리 스크립트가 함께 실행됩니다. (`entrypoint.sh` 참조)

### 6. API 문서 확인

브라우저에서 `http://localhost:8000/docs` 접속

## 🌐 API 엔드포인트

### 💬채팅 & 에이전트

- `POST /chat/v2` - LangGraph 기반 대화형 에이전트 (메인)
- `POST /chat` - LanChain 기반 클래식 에이전트 (이전)
- `GET /chat/v2/health` - 헬스 체크

### 🧭 경로 최적화

- `POST /optimization/route` - POI 경로 최적화 (TSP)

### 기타

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
- **profile**: 사용자 프로필 및 여행 선호도 (VECTOR(768), Gemini 임베딩)

### 필수 확장

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- UUID 생성
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector
CREATE EXTENSION IF NOT EXISTS postgis;    -- 공간 연산
```

## 환경 변수 설정

`.env` 파일 예시:

```bash
# Google Gemini (LLM + 프로필 임베딩, AWS Bedrock 대체)
GOOGLE_API_KEY=your_google_api_key
GEMINI_LLM_MODEL_ID=gemini-3.6-flash
GEMINI_EMBEDDING_MODEL_ID=gemini-embedding-001
GEMINI_EMBEDDING_DIM=768

# AWS Bedrock (레거시, 장소 데이터 수집 스크립트에서만 사용)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# Database (로컬 실행 시 예시: pgvector/pgvector 이미지 + PostGIS 별도 설치 필요)
DB_HOST=localhost
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


## 🔄 AWS 의존성 제거 (2026-08-30)

팀 프로젝트 종료 후 AWS 크레딧이 만료되어, LLM·프로필 임베딩을 무료 대안으로 교체했습니다.

- **LLM(AWS Bedrock Claude → Google Gemini)**: `app/core/llm.py`의 `ChatBedrockConverse`를 `langchain-google-genai`의 `ChatGoogleGenerativeAI`로 교체했습니다.
- **프로필 임베딩(AWS Bedrock Titan → Google Gemini)**: `handle_profile_embedding`(`app/infra/messaging_handler.py`)이 실제로는 로그만 찍는 빈 스텁이었던 걸 발견해, `app/service/gemini_embedding_service.py`를 새로 만들어 제대로 구현했습니다(768차원, `gemini-embedding-001`).
- **장소 데이터**: `places`/`place_review`의 임베딩(1024차원)은 팀 프로젝트 당시 이미 계산해 DB에 저장해둔 값을 그대로 재사용하므로 건드리지 않았습니다.
- **카카오 로컬 API 키 오설정 수정**: `recommend_nearby_places` 도구가 `SuspendedAppException`으로 실패해 조사한 결과, `.env`의 `KAKAO_REST_API_KEY`가 이 앱의 실제 키가 아니라 다른(모빌리티용) 키였던 것으로 확인되어 올바른 키로 교정했습니다.

## 🔗 Related
1. [MateTrip Main Backend Server](https://github.com/NaManMu-10th-team7/matetrip-backend)
2. [MateTrip Front](https://github.com/NaManMu-10th-team7/matetrip-frontend)

## 라이선스

Copyright © 2025 MateTrip Team. All rights reserved.

---

**개발 팀**: jungle-MateTrip 
**최종 업데이트**: 2025-12-02
