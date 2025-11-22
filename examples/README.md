# LangGraph 기반 채팅 API 사용 가이드

## 개요

기존 `/chat` 엔드포인트와 새로운 `/chat/v2` 엔드포인트의 차이점:

| 항목 | `/chat` (기존) | `/chat/v2` (LangGraph) |
|------|----------------|------------------------|
| 구현 방식 | AgentExecutor | LangGraph StateGraph |
| 파일 위치 | `app/routes/chat.py` | `app/routes/chat_v2.py` |
| 라우터 | 수동 실행 후 분기 | 그래프 노드로 자동 실행 |
| 히스토리 관리 | 수동 필터링 | 상태 기반 자동 관리 |
| 도구 호출 | AgentExecutor 내부 처리 | ToolNode로 명시적 처리 |

## 새로운 엔드포인트

### POST `/chat/v2`

LangGraph 기반 채팅 API

**Request:**
```json
{
  "query": "서울 강남구 카페 추천해줘",
  "session_id": "user-session-123"
}
```

**Response:**
```json
{
  "response": "강남구의 인기 카페를 추천해드립니다...",
  "tool_data": []
}
```

### GET `/chat/v2/health`

헬스체크 엔드포인트

**Response:**
```json
{
  "status": "healthy",
  "version": "v2-langgraph",
  "graph_nodes": ["router", "agent", "tools"]
}
```

## LangGraph 아키텍처

### 1. StateGraph 구조

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌─────────┐
│ ROUTER  │ ─── 사용자 의도 분류 (NEW_SEARCH/REFINEMENT/CONVERSATION)
└────┬────┘
     │
     ▼
┌─────────┐
│  AGENT  │ ─── LLM 호출 및 도구 사용 결정
└────┬────┘
     │
     ▼
  ┌──┴──┐
  │ 조건 │
  └──┬──┘
     │
     ├─── 도구 호출 필요? ──▶ ┌───────┐
     │                        │ TOOLS │
     │                        └───┬───┘
     │                            │
     │                            ▼
     │                         (다시 AGENT로)
     │
     └─── 최종 응답? ──▶ END
```

### 2. 상태 정의 (AgentState)

```python
class AgentState(TypedDict):
    input: str                    # 사용자 입력
    session_id: str               # 세션 ID
    chat_history: list[BaseMessage]  # 전체 대화 기록
    intent: Literal["NEW_SEARCH", "REFINEMENT", "CONVERSATION"] | None
    filtered_history: list[BaseMessage]  # 에이전트에 전달할 필터링된 히스토리
    output: str | None            # 최종 응답
    intermediate_steps: list      # 중간 단계 (도구 호출 기록)
```

### 3. 노드 설명

#### Router Node
- **역할**: 사용자 의도 분류
- **입력**: `input`, `chat_history`
- **출력**: `intent`, `filtered_history`
- **로직**:
  - `NEW_SEARCH`: 과거 기억 제거 (filtered_history = [])
  - `REFINEMENT` / `CONVERSATION`: 전체 히스토리 유지

#### Agent Node
- **역할**: 도구 호출 및 응답 생성
- **입력**: `input`, `filtered_history`, `session_id`
- **출력**: `output` (최종 응답) 또는 `intermediate_steps` (도구 호출)
- **로직**:
  - LLM에 도구 바인딩
  - 도구 호출이 필요하면 intermediate_steps에 기록
  - 최종 응답이면 output에 저장

#### Tools Node
- **역할**: 실제 도구 실행
- **관리**: LangGraph의 `ToolNode`가 자동 처리
- **흐름**: 도구 실행 후 다시 Agent Node로

### 4. 의도 분류 기준

#### NEW_SEARCH
- 완전히 새롭고 독립적인 검색
- 위치와 카테고리가 모두 명확히 명시됨
- 예시: "서울 강남구 카페", "부산 해운대 맛집"

#### REFINEMENT
- 이전 불완전한 쿼리를 완성하거나 명확히 함
- AI의 역질문에 대한 답변
- 단일 키워드 응답 (맛집, 카페, 핫플 등)
- 예시:
  - AI: "어디요?" → User: "해운대"
  - AI: "뭘 찾으세요?" → User: "맛집"

#### CONVERSATION
- 이전 답변에 대한 후속 질문
- 캐주얼한 대화
- 예시: "거기 어떻게 가?", "영업시간이 어떻게 돼?"

## 사용 예시

### Python 스크립트 실행

```bash
# 서버 실행 (다른 터미널에서)
python main.py

# 예시 스크립트 실행
python examples/langgraph_usage.py
```

### cURL 사용

```bash
# 1. 헬스체크
curl http://localhost:8000/chat/v2/health

# 2. 새로운 검색
curl -X POST http://localhost:8000/chat/v2 \
  -H "Content-Type: application/json" \
  -d '{
    "query": "서울 강남구 카페 추천해줘",
    "session_id": "test-session-1"
  }'

# 3. 동일 세션에서 후속 질문
curl -X POST http://localhost:8000/chat/v2 \
  -H "Content-Type: application/json" \
  -d '{
    "query": "거기 영업시간은?",
    "session_id": "test-session-1"
  }'
```

### Postman / Insomnia

1. POST 요청 생성: `http://localhost:8000/chat/v2`
2. Headers:
   - `Content-Type: application/json`
3. Body (raw JSON):
```json
{
  "query": "제주도 핫플 알려줘",
  "session_id": "my-session-123"
}
```

## 기존 API와의 호환성

기존 `/chat` 엔드포인트는 그대로 유지되므로:
- 기존 클라이언트는 영향 없음
- `/chat/v2`는 새로운 기능 테스트 또는 마이그레이션용
- 동일한 세션 ID를 사용하더라도 두 엔드포인트는 별도 메모리 사용

## 디버깅

로그에서 다음 정보를 확인할 수 있습니다:

```
[LangGraph] Processing query: 서울 카페
[LangGraph] Session ID: test-session-1
[LangGraph] Chat history length: 0
[router_node] Starting intent classification
[router_node] Classified intent: NEW_SEARCH
[agent_node] Starting agent execution
[agent_node] Agent response: ...
[LangGraph] Execution time: 2.3456 seconds
[LangGraph] Intent classified as: NEW_SEARCH
```

## 주의사항

1. **세션 관리**: 동일한 `session_id`로 대화를 이어가야 히스토리가 유지됩니다
2. **타임아웃**: 도구 호출이 많으면 응답 시간이 길어질 수 있습니다
3. **메모리**: 긴 대화 히스토리는 메모리와 토큰을 많이 사용합니다 (현재 최근 10개로 제한)
4. **의도 분류**: 라우터의 분류가 정확하지 않으면 프롬프트 튜닝이 필요할 수 있습니다

## 추가 개발 가이드

### 새로운 노드 추가하기

1. `app/agent/graph.py`에 노드 함수 정의:
```python
def my_custom_node(state: AgentState) -> AgentState:
    # 로직 구현
    return {**state, "custom_field": "value"}
```

2. 그래프에 노드 추가:
```python
workflow.add_node("custom", my_custom_node)
```

3. 엣지 연결:
```python
workflow.add_edge("router", "custom")
workflow.add_edge("custom", "agent")
```

### 상태 필드 추가하기

1. `AgentState` 정의 수정:
```python
class AgentState(TypedDict):
    # 기존 필드들...
    custom_data: dict | None  # 새로운 필드
```

2. 초기 상태에 포함:
```python
initial_state: AgentState = {
    # ...
    "custom_data": None,
}
```

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain 도구 바인딩](https://python.langchain.com/docs/how_to/tool_calling/)
- 프로젝트 내부 문서: `app/agent/graph.py`, `app/agent/prompts.py`
