import json
from langchain_core.messages import AIMessage
from app.agent.graph import AgentState


def extract_final_response(final_state: AgentState) -> str:
    """마지막 AIMessage(툴콜 없는 것)를 찾아서 텍스트 반환"""
    messages = final_state.get("messages", [])
    # next : 제네레이터의 첫번째 값을 꺼내기
    msg = next(
        (
            m
            for m in reversed(messages)
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", [])
        ),
        None,
    )

    if msg is None:
        return "응답을 생성하지 못했습니다."

    value = getattr(msg, "content", "")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
