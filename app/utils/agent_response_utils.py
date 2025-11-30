"""
Agent 응답 추출 및 파싱 유틸리티
LangGraph AgentState에서 최종 응답을 추출하고 파싱하는 함수들을 제공
"""

import json
from langchain_core.messages import AIMessage
from app.agent.state import AgentState


def extract_final_response(final_state: AgentState) -> str:
    """
    AgentState에서 마지막 AI 응답 추출
    Tool call이 없는 마지막 AIMessage를 찾아서 텍스트로 반환.
    """
    messages = final_state.get("messages", [])

    # Tool call이 없는 마지막 AIMessage 찾기
    ai_message_without_tool_call = next(
        (
            m
            for m in reversed(messages)
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", [])
        ),
        None,
    )

    if ai_message_without_tool_call is None:
        return "응답을 생성하지 못했습니다."

    value = getattr(ai_message_without_tool_call, "content", "")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
