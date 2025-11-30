from langchain_core.messages import BaseMessage, ToolMessage
from app.agent.state import AgentState
from app.core.llm import global_llm
from app.common.logger import logger
from app.utils.agent_message_utils import (
    get_last_human_message,
    prepare_messages_for_bedrock,
)
from app.agent.builder2 import build_agent_prompt
import threading
from app.tools import create_nest_tools


# 전역 에이전트 체인 (캐싱)
_agent_chain = None
_agent_chain_lock = threading.Lock()


def get_agent_chain():
    """에이전트 체인 생성 (한 번만)"""
    global _agent_chain

    with _agent_chain_lock:
        if _agent_chain is None:
            tools = create_nest_tools()
            prompt = build_agent_prompt()
            llm_with_tools = global_llm.bind_tools(tools)

            _agent_chain = prompt | llm_with_tools

    return _agent_chain


def agent_node(state: AgentState) -> AgentState:
    """에이전트 실행 노드"""
    logger.info(f"[agent_node] Starting agent execution")

    agent_chain = get_agent_chain()
    messages = state.get("messages", [])
    intent = state.get("intent")
    logger.info(f"[agent_node] Intent: {intent}")

    has_tool_message = any(isinstance(msg, ToolMessage) for msg in messages)

    # NEW_SEARCH이고 ToolMessage가 없는 경우: 마지막 HumanMessage만 사용
    # 그 외: 최근 히스토리 유지 (최대 10개)
    if intent == "NEW_SEARCH" and not has_tool_message:
        # 첫 실행: 마지막 HumanMessage만 찾기
        history_to_use = [get_last_human_message(messages)]
        logger.info(f"[agent_node] using only HumanMessage")
    else:
        # 도구 실행 후 또는 REFINEMENT/CONVERSATION: 최근 히스토리 사용
        history_to_use = prepare_messages_for_bedrock(messages, max_count=10)

    logger.info(f"[agent_node] Using {len(history_to_use)} messages (intent={intent})")

    # 에이전트 실행
    response: BaseMessage = agent_chain.invoke(
        {
            "chat_history": history_to_use,
            "session_id": state.get("session_id"),
            "excluded_place_ids": state.get("excluded_place_ids", []),
        }
    )
    # AIMessage를 messages에 추가
    return {"messages": [response]}
