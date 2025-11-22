"""
LangGraph 기반 채팅 엔드포인트 (v2)
기존 chat.py와 독립적으로 동작하는 새로운 API
"""

import time
import json
import re
from typing import cast
from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import agent_graph, AgentState
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallData
from app.core.memory import get_session_history
from app.core.constants import TOOL_ACTION_MAP
from app.common.logger import logger
from langchain_core.chat_history import BaseChatMessageHistory

router = APIRouter(prefix="/chat/v2", tags=["chat-v2"])


def safe_json_load(text: str):
    """JSON 문자열이면 객체로 변환, 아니면 그대로 반환"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def remove_thinking_tags(text: str) -> str:
    """<thinking> 태그 제거"""
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()


def extract_tool_data_from_graph_state(final_state: dict) -> list[ToolCallData]:
    """
    LangGraph의 final_state.messages에서 ToolMessage를 찾아
    ToolCallData 리스트로 변환
    """
    tool_data_list = []

    # messages에서 ToolMessage 찾기
    messages = final_state.get("messages", [])

    for message in messages:
        # ToolMessage인지 확인 (LangGraph가 도구 실행 후 추가)
        if hasattr(message, "type") and message.type == "tool":
            tool_name = getattr(message, "name", "unknown_tool")
            tool_output = getattr(message, "content", "")

            # JSON 파싱 시도
            parsed_output = safe_json_load(tool_output)

            # 매핑된 액션 가져오기
            actions = TOOL_ACTION_MAP.get(tool_name, [])

            tool_data_list.append(
                ToolCallData(
                    tool_name=tool_name,
                    tool_output=parsed_output,
                    frontend_actions=actions,
                )
            )

    return tool_data_list


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


@router.post("", response_model=ChatResponse)
async def ask_agent_langgraph(request: ChatRequest) -> ChatResponse:
    """
    LangGraph 기반 AI 에이전트 엔드포인트

    기존 chat.py와 달리 LangGraph의 StateGraph를 사용하여
    라우팅과 에이전트 실행을 자동으로 처리합니다.
    """
    try:
        # 1. 세션 히스토리 가져오기
        session_history: BaseChatMessageHistory = get_session_history(
            request.session_id
        )
        chat_history = list(session_history.messages)

        logger.info(f"[LangGraph] Processing query: {request.query}")
        logger.info(f"[LangGraph] Chat history length: {len(chat_history)}")

        # 2. LangGraph 실행을 위한 초기 상태 구성
        # 사용자 입력을 HumanMessage로 추가

        user_message = HumanMessage(content=request.query)
        initial_messages = chat_history + [user_message]

        initial_state: AgentState = {
            "messages": initial_messages,
            "session_id": request.session_id,
            "intent": None,
        }

        # 3. LangGraph 실행
        t0 = time.perf_counter()
        final_state = agent_graph.invoke(initial_state)
        t1 = time.perf_counter()
        logger.info(f"[ASK_AGENT] Agent_graph invoke 완료")
        logger.info(f"[LangGraph] Execution time: {t1 - t0:.4f} seconds")
        logger.info(f"[LangGraph] Intent classified as: {final_state.get('intent')}")
        logger.info(
            f"[LangGraph] Messages count: {len(final_state.get('messages', []))}"
        )

        # 4. 응답 추출 및 전처리
        output = extract_final_response(cast(AgentState, final_state))
        output = remove_thinking_tags(output)

        logger.info(f"[LangGraph] Final output: {output[:100]}...")

        # 5. 도구 사용 기록 추출
        tool_data_list = extract_tool_data_from_graph_state(final_state)
        logger.info(f"[LangGraph] Tools used: {len(tool_data_list)}")

        # 6. 대화 히스토리 저장
        session_history.add_user_message(request.query)
        session_history.add_ai_message(output)

        # 7. ChatResponse 형식으로 반환
        return ChatResponse(
            response=output,
            tool_data=tool_data_list,
        )

    except Exception as e:
        logger.error(f"[LangGraph] Error: {str(e)}", exc_info=True)
        return ChatResponse(
            response=f"처리 중 오류가 발생했습니다: {str(e)}", tool_data=[]
        )


@router.get("/health")
async def health_check():
    """LangGraph 엔드포인트 헬스체크"""
    return {
        "status": "healthy",
        "version": "v2-langgraph",
        "graph_nodes": ["router", "agent", "tools"],
    }
