import json
import logging
import re
import time

from app.schemas.chat import ChatRequest, ChatResponse, ToolCallData, InternalToolLog, AgentResponseDTO
from app.core.constants import TOOL_ACTION_MAP


logger = logging.getLogger(__name__)


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
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()


def get_agent_response(agent, request: ChatRequest, history: list) -> AgentResponseDTO:
    """
    사용자 쿼리와 세션 ID를 받아,
    대화형 응답과 구조화된 도구 데이터를 함께 반환
    """
    # agent.invoke()는 모든 실행 정보를 담은 dict를 반환
    t0 = time.perf_counter()
    result = agent.invoke(
        {
            "input": request.query,
            "chat_history": history[-10:],
            "session_id": request.session_id,
        },
    )
    t1 = time.perf_counter()
    print(f"[agent.invoke] {t1 - t0:.4f} seconds")

    # print(result)

    # 4. 결과 파싱
    # 4-1. AI 답변 텍스트
    # result["output"]이 리스트일 경우 처리
    if isinstance(result["output"], list):
        # 'type': 'text'인 요소의 'text' 값만 추출하여 합치기
        ai_message_parts = []
        for item in result["output"]:
            if isinstance(item, dict) and item.get("type") == "text":
                ai_message_parts.append(item.get("text", ""))
        ai_message = " ".join(ai_message_parts).strip()
    else:
        ai_message = result["output"]

    ai_message = remove_thinking_tags(ai_message)

    # 4-2. 도구 사용 기록 추출
    # steps 구조 : [(AgentAction, Observation), (AgentAction, Observation), ...]
    steps = result.get("intermediate_steps", [])

    tool_data_list = []
    internal_logs = []

    for action, observation in steps:
        # observation이 보통 문자열로 되어있어 JSON이면 파싱해서 넣음
        parsed_output = safe_json_load(observation)

        # 매핑된 액션 리스트 가져오기 (없으면 빈 리스트)
        actions = TOOL_ACTION_MAP.get(action.tool, [])

        tool_data_list.append(
            ToolCallData(
                tool_name=action.tool,
                tool_output=parsed_output,
                frontend_actions=actions,
            )
        )

        # (2) 백엔드 저장용 데이터 포장 (ID, Args 포함)
        # 결과값 문자열 변환 미리 수행
        if isinstance(parsed_output, (dict, list)):
            content_str = json.dumps(parsed_output, ensure_ascii=False)
        else:
            content_str = str(parsed_output)

        internal_logs.append(
            InternalToolLog(
                tool_call_id=action.tool_call_id, # ★ 진짜 ID
                tool_name=action.tool,
                tool_args=action.tool_input,      # ★ 진짜 인자
                tool_output_str=content_str
            )
        )

    # 3. API 엔드포인트에서 사용할 수 있도록 최종 DTO 포장
    chat_response = ChatResponse(
        response=ai_message,
        tool_data=tool_data_list,
    )

    return AgentResponseDTO(
        chat_response=chat_response,
        internal_tool_log=internal_logs,
    )
