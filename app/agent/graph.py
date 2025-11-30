"""
LangGraph 기반 AI 에이전트 그래프 구성 (후처리 노드 분리 패턴)
- 라우터: 사용자 의도 분류 (NEW_SEARCH, REFINEMENT, CONVERSATION)
- 에이전트: 도구 호출 및 응답 생성
- 후처리 노드: Tool별로 전용 노드가 상태 업데이트 담당
"""

from typing import Hashable

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.agent.nodes.agent_node import agent_node
from app.agent.nodes.router_node import router_node
from app.agent.nodes.post_processors.handle_replace_places_node import (
    handle_replace_places_node,
)
from app.agent.nodes.post_processors.handle_place_recommendation_node import (
    handle_place_recommendation_node,
)
from app.agent.nodes.post_processors.handle_travel_route_node import (
    handle_travel_route_node,
)
from app.agent.nodes.post_processors.handle_workspace_recommendation_node import (
    handle_workspace_recommendation_node,
)
from app.common.logger import logger
from app.agent.state import AgentState
from app.tools import create_nest_tools
from app.utils.agent_message_utils import get_last_tool_message

# Tool -> 후처리 노드 매핑 (중앙 집중 관리)
TOOL_POSTPROCESSING_ROUTES: dict[Hashable, str] = {
    "replace_places": "handle_replace_places",
    "recommend_nearby_places": "handle_place_recommendation",
    "recommend_popular_places_in_region": "handle_place_recommendation",
    "recommend_places_by_all_users": "handle_workspace_recommendation",
    "create_travel_route": "handle_travel_route",
}


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


def route_after_tools(state: AgentState) -> str:
    """
    Tool 실행 후 어떤 후처리 노드로 보낼지 결정
    각 Tool은 전용 후처리 노드가 상태 변경을 담당
    예시
    - replace_places → handle_replace_places
    - recommend_* → handle_place_recommendation
    - create_travel_route → handle_travel_route
    """
    last_tool_message = get_last_tool_message(state.get("messages", []))
    if not last_tool_message:
        logger.warning("[route_after_tools] No tool message found, routing to agent")
        return "agent"

    tool_name = getattr(last_tool_message, "name", "")
    logger.info(f"[route_after_tools] Tool executed: {tool_name}")

    target_node = TOOL_POSTPROCESSING_ROUTES.get(tool_name)
    if not target_node:
        logger.info(f"[route_after_tools] No post-processing needed for {tool_name}")
        return "agent"

    return target_node


# =========================
# 그래프 구성 (후처리 노드 분리 패턴)
# =========================
def create_agent_graph():
    """
    LangGraph 생성 - 후처리 노드 분리 패턴
    구조:
    1. Router → Agent → Tools (도구 실행)
    2. Tools → route_after_tools (라우터)
    3. route_after_tools → 각 Tool별 전용 후처리 노드
       - replace_places → handle_replace_places
       - recommend_* → handle_place_recommendation
       - create_travel_route → handle_travel_route
       - 기타 → agent (바로 복귀)
    4. 후처리 노드 → agent (상태 업데이트 후 복귀)
    """
    workflow = StateGraph(AgentState)

    # 도구 노드 (표준 패턴: messages_key="messages")
    tools = create_nest_tools()
    tool_node = ToolNode(tools, messages_key="messages")

    # 노드 추가
    workflow.add_node("router", router_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("handle_replace_places", handle_replace_places_node)
    workflow.add_node("handle_place_recommendation", handle_place_recommendation_node)
    workflow.add_node("handle_workspace_recommendation", handle_workspace_recommendation_node)
    workflow.add_node("handle_travel_route", handle_travel_route_node)

    # 엣지 설정
    workflow.set_entry_point("router")

    # router -> agent
    workflow.add_edge("router", "agent")

    # agent -> tools or END (도구 호출 여부에 따라 분기)
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )

    # tools -> route_after_tools (Tool별 후처리 노드로 분기)

    postprocess_edges: dict[Hashable, str] = {
        node: node for node in TOOL_POSTPROCESSING_ROUTES.values()
    }
    postprocess_edges["agent"] = "agent"  # 기본 경로
    workflow.add_conditional_edges("tools", route_after_tools, postprocess_edges)

    # 각 후처리 노드 -> agent (상태 업데이트 후 에이전트로 복귀)
    workflow.add_edge("handle_replace_places", "agent")
    workflow.add_edge("handle_place_recommendation", "agent")
    workflow.add_edge("handle_workspace_recommendation", "agent")
    workflow.add_edge("handle_travel_route", "agent")

    # MemorySaver 체크포인터 추가
    # 세션별로 상태를 메모리에 저장하여 요청 간 상태 유지
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# 전역 그래프 인스턴스
agent_graph = create_agent_graph()
