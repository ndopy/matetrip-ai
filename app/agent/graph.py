"""
LangGraph 기반 AI 에이전트 그래프 구성 (표준 패턴)
- 라우터: 사용자 의도 분류 (NEW_SEARCH, REFINEMENT, CONVERSATION)
- 에이전트: 도구 호출 및 응답 생성
"""

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.agent.nodes.agent_node import agent_node
from app.agent.nodes.router_node import router_node
from app.agent.nodes.update_state_node import update_state_node
from app.common.logger import logger
from app.agent.state import AgentState
from app.tools import create_nest_tools


# def route_by_intent(state: AgentState) -> str:
#     """router_node 이후 의도에 따라 분기"""
#     intent = state.get("intent")
#     logger.info(f"[route_by_intent] Intent: {intent}")

#     # 모든 경우 agent로 라우팅
#     ## 임시 :
#     return "agent"


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
    """
    LangGraph 생성

    MemorySaver 체크포인터를 사용하여 세션별 상태를 자동으로 저장/복원합니다.
    이를 통해 last_recommended_places 등의 상태가 요청 간에 유지됩니다.
    """
    workflow = StateGraph(AgentState)

    # 도구 노드 (표준 패턴: messages_key="messages")
    tools = create_nest_tools()
    tool_node = ToolNode(tools, messages_key="messages")

    # 노드 추가
    workflow.add_node("router", router_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("update_state", update_state_node)

    # 엣지 설정
    workflow.set_entry_point("router")

    # router -> agent
    workflow.add_edge("router", "agent")

    # agent -> tools or END (도구 호출 여부에 따라 분기)
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )

    # tools -> update_state (도구 실행 후 상태 업데이트)
    workflow.add_edge("tools", "update_state")

    # update_state -> agent (상태 업데이트 후 다시 에이전트로)
    workflow.add_edge("update_state", "agent")

    # MemorySaver 체크포인터 추가
    # 세션별로 상태를 메모리에 저장하여 요청 간 상태 유지
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# 전역 그래프 인스턴스
agent_graph = create_agent_graph()
