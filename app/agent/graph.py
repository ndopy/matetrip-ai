"""
LangGraph 기반 AI 에이전트 그래프 구성 (표준 패턴)
- 라우터: 사용자 의도 분류 (NEW_SEARCH, REFINEMENT, CONVERSATION)
- 에이전트: 도구 호출 및 응답 생성
"""

from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.schemas.chat import IntentClassifier
from app.common.logger import logger
from app.agent.prompts import build_agent_prompt


# =========================
# 1. 상태 정의 (표준 패턴)
# =========================
class AgentState(TypedDict, total=False):
    """LangGraph 표준 상태 관리"""

    # 메시지 히스토리 (LangGraph 표준)
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # 추가 메타데이터
    session_id: str
    intent: Literal["NEW_SEARCH", "REFINEMENT", "CONVERSATION"] | None


# =========================
# 2. 라우터 프롬프트
# =========================
router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a routing assistant. Classify the user's intent.\n\n"
                "**Key Guidelines:**\n\n"
                "1. 'NEW_SEARCH': Completely new search with location AND category\n"
                "   - Examples: '서울 카페', '부산 호텔'\n\n"
                "2. 'REFINEMENT': Completing or clarifying previous incomplete query\n"
                "   - Examples: AI asked '어디요?' → User: '해운대'\n"
                "   - Single keywords like '맛집', '카페' after a question\n\n"
                "3. 'CONVERSATION': Follow-up about previous answer\n"
                "   - Examples: '거기 어떻게 가?', 'tell me more'\n\n"
                "**Rules:**\n"
                "- If AI just asked a question, classify next input as 'REFINEMENT'\n"
                "- Only 'NEW_SEARCH' if user provides COMPLETE new query"
            ),
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

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


# 전역 에이전트 체인 (캐싱)
_agent_chain = None


def get_agent_chain():
    """에이전트 체인 생성 (한 번만)"""
    global _agent_chain
    if _agent_chain is not None:
        return _agent_chain

    tools = create_nest_tools()
    prompt = build_agent_prompt()
    llm_with_tools = global_llm.bind_tools(tools)

    _agent_chain = prompt | llm_with_tools
    return _agent_chain


def agent_node(state: AgentState) -> AgentState:
    """에이전트 실행 노드 (표준 패턴)"""
    logger.info("[agent_node] Starting agent execution")

    agent_chain = get_agent_chain()
    messages = state.get("messages", [])
    intent = state.get("intent")

    # NEW_SEARCH인 경우: 마지막 HumanMessage만 사용
    # 그 외: 최근 히스토리 유지 (최대 20개)
    if intent == "NEW_SEARCH":
        # 마지막 HumanMessage만 찾기
        history_to_use = []
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                history_to_use = [msg]
                break
    else:
        # 최근 20개 메시지 사용
        history_to_use = messages[-20:] if len(messages) > 20 else messages

    logger.info(f"[agent_node] Using {len(history_to_use)} messages (intent={intent})")
    logger.info(
        f"[agent_node] Message types: {[type(m).__name__ for m in history_to_use]}"
    )

    # 에이전트 실행
    response = agent_chain.invoke(
        {
            "chat_history": history_to_use,
            "session_id": state.get("session_id"),
        }
    )

    logger.info(f"[agent_node] Response type: {type(response).__name__}")
    if hasattr(response, "tool_calls"):
        logger.info(f"[agent_node] Tool calls: {len(response.tool_calls)}")

    # AIMessage를 messages에 추가
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """도구 호출 여부 판단"""
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]

    if isinstance(last_message, AIMessage):
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(
                f"[should_continue] Calling tools: {len(last_message.tool_calls)}"
            )
            return "tools"

    logger.info("[should_continue] Ending")
    return END


# =========================
# 4. 그래프 구성
# =========================
def create_agent_graph():
    """LangGraph 생성 (표준 패턴)"""
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
