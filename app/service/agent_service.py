import json
import re

from app.schemas.chat import ChatRequest, ToolCallData
from app.core.constants import TOOL_ACTION_MAP

def safe_json_load(text: str):
    """
    도구 결과가 JSON 문자열이면 객체로 변환하고,
    아니면(일반 텍스트면) 그대로 반환하는 헬퍼 함수
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text

# <thinking> 태그 제거 함수
def remove_thinking_tags(text: str) -> str:
    # <thinking>으로 시작해서 </thinking>으로 끝나는 모든 내용 제거
    return re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL).strip()

def get_agent_response(agent, request: ChatRequest, history: list) -> dict:
    """
    사용자 쿼리와 세션 ID를 받아,
    대화형 응답과 구조화된 도구 데이터를 함께 반환
    """
    # agent.invoke()는 모든 실행 정보를 담은 dict를 반환
    result = agent.invoke(
        { 
            "input": request.query,
            "chat_history": history,
            "session_id": request.session_id
        },
    )

    print(result)

    # 4. 결과 파싱
    # 4-1. AI 답변 텍스트
    ai_message = remove_thinking_tags(result["output"])

    # 4-2. 도구 사용 기록 추출
    # steps 구조 : [(AgentAction, Observation), (AgentAction, Observation), ...]
    steps = result.get("intermediate_steps", [])

    tool_data_list = []

    for action, observation in steps:
        # observation이 보통 문자열로 되어있어 JSON이면 파싱해서 넣음
        parsed_output = safe_json_load(observation)

        # 매핑된 액션 리스트 가져오기 (없으면 빈 리스트)
        actions = TOOL_ACTION_MAP.get(action.tool, [])

        tool_data_list.append(
            ToolCallData(
                tool_name=action.tool,
                tool_output=parsed_output,
                frontend_actions=actions
            )
        )

    # 3. API 엔드포인트에서 사용할 수 있도록 딕셔너리로 반환
    return {
        "response": ai_message,
        "tool_data": tool_data_list
    }