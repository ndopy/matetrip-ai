"""
Agent 응답 추출 및 파싱 유틸리티
LangGraph AgentState에서 최종 응답을 추출하고 파싱하는 함수들을 제공
"""

from langchain_core.messages import AIMessage
from app.agent.state import AgentState


def _extract_text_from_content(value) -> str:
    """
    AIMessage.content에서 사용자에게 보여줄 text만 추출.
    Gemini는 content를 [{"type": "text", "text": "...", "extras": {...}}]
    형태의 리스트로 반환할 수 있는데, extras(내부 thought signature 등)를
    그대로 노출하면 안 되므로 각 part의 text 필드만 모아 이어붙인다.
    """
    if isinstance(value, list):
        texts = [
            part.get("text", "")
            for part in value
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "".join(texts).strip()
    if isinstance(value, dict):
        return str(value.get("text", "")).strip()
    return str(value).strip()


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
    text = _extract_text_from_content(value)
    if not text:
        return "응답을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
    return text
