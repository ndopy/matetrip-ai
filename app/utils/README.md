# Utils Package

LangGraph 에이전트를 위한 유틸리티 함수 모음입니다.

## 📁 구조

```
app/utils/
├── agent_message_utils.py    # LangChain 메시지 조작
├── agent_response_utils.py   # Agent 응답 추출/파싱
├── place_extractor.py         # 장소 정보 추출
├── place_normalizer.py        # 장소 데이터 정규화
└── backend_notifier.py        # 백엔드 알림
```

## 🔧 모듈 설명

### `agent_message_utils.py`

LangChain 메시지 조작 및 AWS Bedrock 제약 처리

**함수:**
- `get_last_human_message()` - 마지막 HumanMessage 추출
- `get_last_tool_message()` - 마지막 ToolMessage 추출
- `get_messages_after_last_human()` - 마지막 HumanMessage 이후 메시지들
- `prepare_messages_for_bedrock()` - Bedrock 제약에 맞게 메시지 준비

**사용 예:**
```python
from app.utils import prepare_messages_for_bedrock

# Bedrock용 메시지 준비 (최대 10개, HumanMessage로 시작)
messages = prepare_messages_for_bedrock(state.get("messages", []))
```

### `agent_response_utils.py`

LangGraph AgentState에서 최종 응답 추출

**함수:**
- `extract_final_response()` - Tool call 없는 마지막 AI 응답 추출

**사용 예:**
```python
from app.utils import extract_final_response

final_text = extract_final_response(agent_state)
```

### `place_extractor.py`

Tool 실행 결과에서 장소 정보 추출

**함수:**
- `extract_simple_places_from_result()` - Tool 결과에서 장소 목록 추출

### `place_normalizer.py`

장소 데이터 정규화 및 변환

**함수:**
- `to_simple_places()` - Place 객체를 SimplePlace로 변환

### `backend_notifier.py`

백엔드 서버로 알림 전송

**함수:**
- `notify_backend_route_created()` - 여행 경로 생성 알림

## 🎯 설계 원칙

1. **단일 책임 원칙**: 각 파일은 하나의 도메인만 담당
2. **명확한 네이밍**: 파일명으로 역할을 즉시 파악 가능
3. **재사용성**: 여러 노드/서비스에서 공통으로 사용
4. **테스트 용이성**: 각 함수가 독립적으로 테스트 가능

## 📦 Import 방법

### 권장: 직접 import
```python
from app.utils.agent_message_utils import prepare_messages_for_bedrock
from app.utils.agent_response_utils import extract_final_response
```

### 대안: 패키지 레벨 import
```python
from app.utils import (
    prepare_messages_for_bedrock,
    extract_final_response,
)
```
