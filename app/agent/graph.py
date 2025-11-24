"""
LangGraph 기반 AI 에이전트 그래프 구성 (표준 패턴)
- 라우터: 사용자 의도 분류 (NEW_SEARCH, REFINEMENT, CONVERSATION)
- 에이전트: 도구 호출 및 응답 생성
"""

from typing import Annotated, List, Literal, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from agent.nodes.agent_node import agent_node
from agent.nodes.router_node import router_node
from app.tools import create_nest_tools
from app.common.logger import logger
from app.schemas.place import SimplePlace


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
    last_recommended_places: List[SimplePlace]


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
# 그래프 구성
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
