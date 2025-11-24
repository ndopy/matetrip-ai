from email import message
from typing import Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from app.agent.utils.agent_utils import get_last_human_message
from app.agent.state import AgentState
from app.core.llm import global_llm
from app.common.logger import logger
from app.agent.prompts import build_agent_prompt
import threading

from app.tools import create_nest_tools


# 전역 에이전트 체인 (캐싱)
_agent_chain = None
_agent_chain_lock = threading.Lock()


# Bedrock 제약 : Bedrock은 히스토리 전체를 볼 때 첫 메시지가 human이 아니면 에러를 냄
# 대화 슬라이스를 HumanMessage부터 시작하도록 자르는 것
def ensure_user_first(messages: Sequence[BaseMessage]):
    for idx, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            return list(messages[:idx])

    last_human = get_last_human_message(messages)
    return [last_human] if last_human else []


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
    logger.info("[agent_node] Starting agent execution")

    agent_chain = get_agent_chain()
    messages = state.get("messages", [])
    intent = state.get("intent")

    has_tool_message = any(isinstance(msg, ToolMessage) for msg in messages)

    history_to_use = []
    # NEW_SEARCH이고 ToolMessage가 없는 경우: 마지막 HumanMessage만 사용
    # 그 외: 최근 히스토리 유지 (최대 10개)
    if intent == "NEW_SEARCH" and not has_tool_message:
        # 첫 실행: 마지막 HumanMessage만 찾기
        history_to_use = [get_last_human_message(messages)]
        logger.info("[agent_node] 첫 실행, using only HumanMessage")
    else:
        # 도구 실행 후 또는 REFINEMENT/CONVERSATION: 최근 히스토리 사용
        history_to_use = messages[-10:] if len(messages) > 10 else messages
        logger.info(
            f"[agent_node] Using recent history (has_tool_message={has_tool_message})"
        )

    # Bedrock 제약때문에 무조건 사용자 메시지로 시작하게 하는 것
    history_to_use = ensure_user_first(history_to_use)
    logger.info(f"[agent_node] Using {len(history_to_use)} messages (intent={intent})")

    # 에이전트 실행
    response: BaseMessage = agent_chain.invoke(
        {
            "chat_history": history_to_use,
            "session_id": state.get("session_id"),
            "excluded_place_ids": state.get(
                "excluded_place_ids", []
            ),  # excluded_place_ids 전달
        }
    )
    # AIMessage를 messages에 추가
    return {"messages": [response]}
