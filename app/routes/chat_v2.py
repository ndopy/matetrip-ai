"""
LangGraph 기반 채팅 엔드포인트 (v2)
기존 chat.py와 독립적으로 동작하는 새로운 API
"""

import time
import json
from typing import cast
from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from app.agent.graph import agent_graph, AgentState
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallData
from app.core.constants import TOOL_ACTION_MAP
from app.common.logger import logger
from app.service.agent_service import remove_thinking_tags
from app.utils.agent_message_utils import (
    get_messages_after_last_human,
)
from app.utils.agent_response_utils import extract_final_response

router = APIRouter(prefix="/chat/v2", tags=["chat-v2"])


def safe_json_load(text: str):
    """JSON 문자열이면 객체로 변환, 아니면 그대로 반환"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def extract_tool_data_from_graph_state(final_state: dict) -> list[ToolCallData]:
    """
    LangGraph의 final_state.messages에서 ToolMessage를 찾아
    ToolCallData 리스트로 변환

    마지막 HumanMessage 이후의 ToolMessage만 처리하여
    이전 세션의 도구 호출이 중복되지 않도록 합니다.
    """
    tool_data_list = []
    messages = final_state.get("messages", [])

    # 마지막 HumanMessage 이후의 메시지만 처리
    messages_after_human = get_messages_after_last_human(messages)
    if not messages_after_human:
        return []

    for message in messages_after_human:
        # ToolMessage인지 확인 (LangGraph가 도구 실행 후 추가)
        if hasattr(message, "type") and message.type == "tool":
            tool_name = getattr(message, "name", "unknown_tool")
            tool_output = getattr(message, "content", "")

            # JSON 파싱 시도
            parsed_output = safe_json_load(tool_output)

            # 매핑된 액션 가져오기
            actions = TOOL_ACTION_MAP.get(tool_name, [])

            tool_call_data = ToolCallData(
                tool_name=tool_name,
                tool_output=parsed_output,
                frontend_actions=actions,
            )

            # 모든 도구 호출을 리스트에 추가
            tool_data_list.append(tool_call_data)

    return tool_data_list


@router.post("", response_model=ChatResponse)
async def ask_agent_langgraph(request: ChatRequest) -> ChatResponse:
    """
    LangGraph 기반 AI 에이전트 엔드포인트

    기존 chat.py와 달리 LangGraph의 StateGraph를 사용하여
    라우팅과 에이전트 실행을 자동으로 처리합니다.
    """
    try:
        logger.debug(f"[LangGraph] Processing query: {request.query[:50]}...")

        # 1. LangGraph 실행을 위한 초기 상태 구성
        # 체크포인터가 thread_id로 이전 상태를 자동으로 불러오므로 새 메시지만 추가
        user_message = HumanMessage(content=request.query)

        initial_state: AgentState = {
            "messages": [user_message],
            "session_id": request.session_id,
            "intent": None,
        }

        # 2. LangGraph 실행 (체크포인터 사용)
        # thread_id를 session_id로 사용하여 세션별 상태 유지
        config: RunnableConfig = {"configurable": {"thread_id": request.session_id}}

        t0 = time.perf_counter()
        # ainvoke를 사용하여 async 노드 지원
        final_state = await agent_graph.ainvoke(initial_state, config)
        t1 = time.perf_counter()
        logger.info(f"[LangGraph_invoke완료] Execution time: {t1 - t0:.4f} seconds")

        # 3. 응답 추출 및 전처리
        output = extract_final_response(cast(AgentState, final_state))
        output = remove_thinking_tags(output)

        logger.info(f"[LangGraph] Final output: {output[:70]}...")

        # 4. 도구 사용 기록 추출
        tool_data_list = extract_tool_data_from_graph_state(final_state)
        logger.info(f"[LangGraph] Tools used: {len(tool_data_list)}")

        # 5. ChatResponse 형식으로 반환
        # 대화 히스토리는 체크포인터가 자동으로 관리
        return ChatResponse(
            response=output,
            tool_data=tool_data_list,
        )

    except Exception as e:
        logger.error(f"[LangGraph] Error: {str(e)}", exc_info=True)
        return ChatResponse(
            response="요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            tool_data=[],
        )


@router.get("/health")
async def health_check():
    """LangGraph 엔드포인트 헬스체크"""
    return {
        "status": "healthy",
        "version": "v2-langgraph",
        "graph_nodes": ["router", "agent", "tools"],
    }
