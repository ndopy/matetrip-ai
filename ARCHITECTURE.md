# MateTrip AI Agent Architecture

## 개요

이 프로젝트는 **3계층 아키텍처 + 후처리 노드 분리 패턴**을 사용하여 LangGraph 기반 AI 에이전트를 구현합니다.

## 핵심 원칙

1. **Service는 순수 비즈니스 로직** - LangChain/LangGraph에 대해 전혀 모름
2. **Tool은 얇은 어댑터** - Service 호출 + ToolResult 포장만 담당
3. **Node는 상태 관리** - Tool 결과를 받아서 State 업데이트

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph Flow                          │
│                                                               │
│  Router → Agent → [should_continue] → Tools                  │
│                                          ↓                    │
│                                  [route_after_tools]          │
│                                          ↓                    │
│           ┌──────────────────────────────┼─────────────┐     │
│           ↓                              ↓             ↓     │
│  handle_replace_places    handle_place_recommendation  │     │
│           ↓                              ↓      handle_travel│
│         Agent ←──────────────────────── Agent    ↓     │
│                                                 Agent   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     3-Layer Architecture                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Service Layer (순수 비즈니스 로직)                │    │
│  │    - PlaceService.find_replacement_places()         │    │
│  │    - PlaceService.get_nearby_place()                │    │
│  │    - PlaceService.get_popular_places_in_region()    │    │
│  │    → Returns: List[DTO] (순수 데이터)                │    │
│  │    → LangGraph를 전혀 모름                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                            ↑                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 2. Tool Layer (LLM 어댑터)                           │    │
│  │    - @tool recommend_nearby_places()                │    │
│  │    - @tool recommend_popular_places_in_region()     │    │
│  │    - @tool replace_places()                         │    │
│  │    → Service 호출 후 ToolResult로 포장               │    │
│  │    → 메타데이터 추가 (replaced_place_ids 등)         │    │
│  └─────────────────────────────────────────────────────┘    │
│                            ↓                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 3. Node Layer (상태 관리)                            │    │
│  │    - handle_replace_places_node()                   │    │
│  │    - handle_place_recommendation_node()             │    │
│  │    - handle_travel_route_node()                     │    │
│  │    → ToolResult 언래핑 후 State 업데이트             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 계층별 책임

### Layer 1: Service (순수 비즈니스 로직)

**위치**: `app/service/place_service.py`

**책임**:
- DB 조회 및 비즈니스 로직 처리
- 순수 데이터 (DTO) 반환
- LangChain, LangGraph, ToolResult에 대해 전혀 모름

**재사용성**: REST API, CLI, 테스트 코드 등 어디서든 사용 가능

**DTO 캡슐화 원칙**: 파라미터가 3개 이상이면 DTO로 캡슐화

**예시**:
```python
class PlaceService:
    def find_replacement_places(
        self, request: ReplacePlaceRequest
    ) -> List[NearbyPlaceResponse]:
        """
        순수 비즈니스 로직 - ToolResult 모름

        파라미터 6개 → DTO 1개로 캡슐화 ✅
        - latitude, longitude, replace_count, excluded_place_ids,
          category, radius_km
        → ReplacePlaceRequest DTO
        """
        places = self.repository.find_places_within_radius(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km,
            category=request.category,
            limit=request.replace_count,
            excluded_place_ids=request.excluded_place_ids,
        )
        return [NearbyPlaceResponse.from_entity(p) for p in places]
```

**DTO 정의** (`app/schemas/place.py`):
```python
class ReplacePlaceRequest(BaseModel):
    """장소 교체 요청 DTO (3개 이상 파라미터 캡슐화)"""

    latitude: float
    longitude: float
    replace_count: int
    excluded_place_ids: List[str]
    category: Optional[str] = None
    radius_km: float = 5.0

    @classmethod
    def create(cls, *, latitude, longitude, ...) -> "ReplacePlaceRequest":
        """팩토리 메서드"""
        return cls(...)
```

### Layer 2: Tool (LLM 어댑터)

**위치**: `app/tools/place_tool.py`

**책임**:
- Service 호출
- 결과를 ToolResult로 포장 (LLM이 이해할 수 있는 형태)
- 메타데이터 추가 (replaced_place_ids 등)

**얇은 래퍼**: 비즈니스 로직 없음, 변환만 수행

**예시**:
```python
@tool
def replace_places(replace_target_ids, latitude, longitude, ...):
    """LLM 어댑터 - Service 호출 + ToolResult 포장"""

    # DTO 생성 (3개 이상 파라미터 캡슐화)
    request = ReplacePlaceRequest.create(
        latitude=latitude,
        longitude=longitude,
        replace_count=len(replace_target_ids),
        excluded_place_ids=excluded_place_ids,
        category=mapped_category,
        radius_km=radius_km,
    )

    # Service Layer 호출 (순수 비즈니스 로직)
    place_responses = PlaceService(db).find_replacement_places(request)

    # Tool Layer: ToolResult로 포장 (LLM 어댑터)
    return ToolResult(
        success=True,
        data=PlaceRecommendationData(
            places=[p.model_dump() for p in place_responses],
            replaced_place_ids=replace_target_ids,  # 메타정보
        ),
    ).model_dump()
```

### Layer 3: Node (상태 관리)

**위치**: `app/agent/nodes/`

**책임**:
- ToolResult 파싱
- AgentState 업데이트
- Tool별 전용 노드로 분리

**파일 구조**:
```
app/agent/nodes/
├── handle_replace_places_node.py       # replace_places 전용
├── handle_place_recommendation_node.py # 일반 장소 추천 전용
├── handle_travel_route_node.py         # create_travel_route 전용
└── ...
```

**예시**:
```python
def handle_replace_places_node(state: AgentState) -> AgentState:
    """replace_places Tool 결과를 받아서 상태 업데이트"""

    # 1. ToolResult 파싱
    data = get_last_tool_message(state["messages"]).content["data"]
    replaced_ids = data["replaced_place_ids"]
    new_places = data["places"]

    # 2. 기존 장소에서 제거
    current = state["last_recommended_places"]
    updated = _drop_places_by_ids(current, replaced_ids)

    # 3. 새 장소 추가
    updated.extend(to_simple_places(new_places))

    return {"last_recommended_places": updated}
```

## 그래프 구조 (후처리 노드 분리 패턴)

**위치**: `app/agent/graph.py`

**핵심**: Tool 실행 후 `route_after_tools()`가 Tool별로 적절한 후처리 노드로 라우팅

```python
def route_after_tools(state: AgentState) -> str:
    """Tool 실행 후 어떤 후처리 노드로 보낼지 결정"""
    tool_name = get_last_tool_message(state["messages"]).name

    if tool_name == "replace_places":
        return "handle_replace_places"
    elif tool_name in ["recommend_nearby_places", "recommend_popular_places_in_region"]:
        return "handle_place_recommendation"
    elif tool_name == "create_travel_route":
        return "handle_travel_route"
    else:
        return "agent"  # 상태 변경 없는 Tool

# 그래프 구성
workflow.add_conditional_edges(
    "tools",
    route_after_tools,
    {
        "handle_replace_places": "handle_replace_places",
        "handle_place_recommendation": "handle_place_recommendation",
        "handle_travel_route": "handle_travel_route",
        "agent": "agent",
    },
)
```

## 장점

### 1. 순수성 (Purity)
- **Service**: 프레임워크에 독립적인 순수 Python 코드
- **재사용성**: API, CLI, 테스트 등 어디서든 사용 가능
- **테스트**: 단위 테스트가 쉬움

### 2. 책임 분리 (Separation of Concerns)
- **Service**: "데이터를 어떻게 가져올까?"
- **Tool**: "LLM에게 데이터를 어떻게 전달할까?"
- **Node**: "가져온 데이터로 상태를 어떻게 바꿀까?"

### 3. 캡슐화 (Encapsulation)
- **DTO 원칙**: 파라미터 3개 이상이면 DTO로 캡슐화
- **장점**:
  - 파라미터 순서 실수 방지
  - 타입 안정성 향상
  - 검증 로직 중앙화
  - 문서화 자동화 (Pydantic Field)

### 4. 확장성 (Scalability)
- 새 Tool 추가 시:
  1. 필요시 Request DTO 생성 (3개 이상 파라미터)
  2. Service에 순수 로직 추가
  3. Tool에 얇은 래퍼 추가
  4. 필요시 전용 Node 추가
  5. `route_after_tools()`에 라우팅 추가

### 5. 명시성 (Explicitness)
- Tool별 분기가 `route_after_tools()`에 명시적으로 표현
- `if tool_name == ...` 분기문이 여러 곳에 흩어지지 않음

## 예시: replace_places 플로우

```
1. LLM이 replace_places Tool 호출 결정
   ↓
2. Tool Layer (@tool replace_places)
   - ReplacePlaceRequest DTO 생성 (6개 파라미터 캡슐화)
   - Service.find_replacement_places(request) 호출
   - ToolResult로 포장 (replaced_place_ids 메타정보 추가)
   ↓
3. route_after_tools() 라우터
   - tool_name == "replace_places" 확인
   - "handle_replace_places" 노드로 라우팅
   ↓
4. Node Layer (handle_replace_places_node)
   - ToolResult 파싱
   - 기존 장소에서 교체 대상 제거
   - 새 장소 추가
   - AgentState 업데이트
   ↓
5. Agent로 복귀
```

## 기존 구조와의 비교

### Before (❌ 문제점)
```python
# update_state_node.py - 모든 Tool 처리
def update_state_node(state):
    if tool_name == "replace_places":
        # 특수 로직 1
    elif tool_name == "create_travel_route":
        # 특수 로직 2
    else:
        # 일반 처리
```

**문제점**:
- Tool이 늘어날 때마다 `if`문 추가
- 단일 파일에 모든 로직 집중
- Tool이 ToolResult 반환 → 순수하지 않음

### After (✅ 개선)
```python
# Service Layer: 순수 로직
PlaceService.find_replacement_places() → List[DTO]

# Tool Layer: 얇은 어댑터
@tool replace_places() → ToolResult

# Node Layer: 전용 노드
handle_replace_places_node() → AgentState
handle_place_recommendation_node() → AgentState
handle_travel_route_node() → AgentState

# Router
route_after_tools() → "handle_replace_places" | "handle_place_recommendation" | ...
```

**장점**:
- 각 계층이 단일 책임
- Service는 순수 함수 (재사용 가능)
- Tool별로 노드 분리 (확장 용이)

## 핵심 설계 원칙

### 1. 3계층 분리
- **Service**: 순수 비즈니스 로직 (LangGraph 모름)
- **Tool**: LLM 어댑터 (Service → ToolResult)
- **Node**: 상태 관리 (ToolResult → State)

### 2. DTO 캡슐화 규칙
- **3개 이상 파라미터 → DTO로 캡슐화**
- Pydantic BaseModel 사용
- 팩토리 메서드 (`create()`) 제공

### 3. 후처리 노드 분리
- Tool별 전용 Node 생성
- `route_after_tools()` 라우터로 분기
- `if tool_name == ...` 분산 방지

## 결론

이 아키텍처는 **엔터프라이즈급 LangGraph 애플리케이션의 표준 패턴**입니다:

1. ✅ Service는 순수 비즈니스 로직 (DTO로 캡슐화)
2. ✅ Tool은 LLM 어댑터 (얇은 래퍼)
3. ✅ Node는 상태 관리 (Tool별 분리)
4. ✅ 명시적 라우팅 (route_after_tools)
5. ✅ 파라미터 캡슐화 (3개 이상 → DTO)

이를 통해 **유지보수성, 테스트 용이성, 확장성, 타입 안정성**을 모두 확보했습니다.
