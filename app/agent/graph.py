"""
LangGraph 기반 AI 에이전트 그래프 구성 (표준 패턴)
- 라우터: 사용자 의도 분류 (NEW_SEARCH, REFINEMENT, CONVERSATION)
- 에이전트: 도구 호출 및 응답 생성
"""

import threading
from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.schemas.chat import IntentClassifier
from app.common.logger import logger
from app.agent.prompts import build_agent_prompt

# 전역 에이전트 체인 (캐싱)
_agent_chain = None
_agent_chain_lock = threading.Lock()


# =========================
# 1. 상태 정의
# =========================
class AgentState(TypedDict, total=False):
    """LangGraph 표준 상태 관리"""

    # 메시지 히스토리 (LangGraph 표준)
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # 추가 메타데이터
    session_id: str
    intent: Literal["NEW_SEARCH", "REFINEMENT", "CONVERSATION", "FOLLOW_UP"] | None


# =========================
# 2. 라우터 프롬프트
# =========================
router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a routing assistant. Classify the user's intent.\n\n"
                "**CRITICAL RULE: Check the last AI message first!**\n"
                "- If the last AI message is a QUESTION, the user's response is ALWAYS 'REFINEMENT'\n"
                "- Questions end with '?' or ask for clarification (어디, 무엇, 어떤, etc.)\n\n"
                "**Key Guidelines:**\n\n"
                "1. 'REFINEMENT': User is answering AI's question or adding missing info\n"
                "   - Examples:\n"
                "     * AI: '어떤 지역의 양식 식당을 찾으시는 건가요?' → User: '부산이 좋을 것 같아'\n"
                "     * AI: '어디요?' → User: '해운대'\n"
                "     * AI asked for category → User: '맛집', '카페'\n\n"
                "2. 'NEW_SEARCH': Completely new search with location AND category\n"
                "   - Must have BOTH location AND category in ONE message\n"
                "   - Examples: '서울 카페', '부산 호텔', '강남 맛집'\n"
                "   - NOT examples: '부산' (no category), '카페' (no location)\n\n"
                "3. 'CONVERSATION': Follow-up about search results already shown\n"
                "   - Examples: '거기 어떻게 가?', 'tell me more', '영업시간은?'\n\n"
                "**Decision Process:**\n"
                "1. Is the last AI message a question? → REFINEMENT\n"
                "2. Does user message have location + category? → NEW_SEARCH\n"
                "3. Is user asking about previous results? → CONVERSATION\n"
                "4. Otherwise → REFINEMENT"
            ),
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# =========================
# 라우터 체인
# =========================
router_chain = router_prompt | global_llm.with_structured_output(IntentClassifier)


# =========================
# 3. 노드 함수들
# =========================
def router_node(state: AgentState) -> AgentState:
    """의도 분류 노드"""
    logger.info("[router_node] Starting intent classification")

    messages = state.get("messages", [])
    logger.info(f"[router_node] Messages count: {len(messages)}")

    # 최근 10개 메시지만 사용
    recent_messages = messages[-10:] if len(messages) > 10 else messages

    # 의도 분류
    classification = router_chain.invoke({"messages": recent_messages})
    classification = IntentClassifier.model_validate(classification)

    intent = classification.intent
    logger.info(f"[router_node] Classified intent: {intent}")

    return {
        "intent": intent,
    }


def get_last_human_message(messages: Sequence[BaseMessage]) -> HumanMessage:
    """히스토리에서 마지막 HumanMessage만 추출"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg

    return HumanMessage(content="")


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

    logger.info(f"[agent_node] Using {len(history_to_use)} messages (intent={intent})")
    logger.info(
        f"[agent_node] Message types: {[type(m).__name__ for m in history_to_use]}"
    )

    # 에이전트 실행
    response: BaseMessage = agent_chain.invoke(
        {
            "chat_history": history_to_use,
            "session_id": state.get("session_id"),
        }
    )
    # AIMessage를 messages에 추가
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """도구 호출 여부 판단"""
    messages = state.get("messages", [])
    logger.info(f"[should_continue] Messages count: {len(messages)}")
    if not messages:
        return END

    last_message = messages[-1]
    logger.info("=================================================")
    logger.info(f"[should_continue] Last message: {last_message}")
    logger.info("=================================================")

    if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", []):
        return "tools"

    logger.info("[should_continue] Ending")
    return END


# =========================
# 4. 그래프 구성
# =========================
def create_agent_graph():
    """LangGraph 생성"""
    workflow = StateGraph(AgentState)

    # 도구 노드 (표준 패턴: messages_key="messages")
    tools = create_nest_tools()
    tool_node = ToolNode(tools, messages_key="messages")  #

    # 노드 추가
    workflow.add_node("router", router_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # 엣지 설정
    workflow.set_entry_point("router")
    workflow.add_edge("router", "agent")
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# 전역 그래프 인스턴스
agent_graph = create_agent_graph()
