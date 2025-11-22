"""
LangGraph 기반 AI 에이전트 그래프 구성
- 라우터: 사용자 의도 분류 (NEW_SEARCH, REFINEMENT, CONVERSATION)
- 에이전트: 도구 호출 및 응답 생성
"""

import json
import operator
from typing import Annotated, TypedDict, Literal, cast
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.schemas.chat import IntentClassifier
from app.common.logger import logger
from app.agent.prompts import build_agent_prompt


# =========================
# 1. 상태 정의
# =========================
class AgentState(TypedDict):
    """LangGraph 상태 관리 모델"""

    # 사용자 입력
    input: str
    session_id: str

    # 대화 기록
    chat_history: Annotated[list[BaseMessage], operator.add]

    # 라우터 결과
    intent: Literal["NEW_SEARCH", "REFINEMENT", "CONVERSATION"] | None

    # 에이전트가 사용할 히스토리 (라우터에 의해 필터링됨)
    # - 전체 기록 중 현재 작업에 필요한 것만 추려낸 리스트
    filtered_history: list[BaseMessage]

    # 최종 응답
    output: str | None

    # 도구 호출 기록 (intermediate_steps)
    intermediate_steps: list


# =========================
# 2. 라우터 프롬프트 정의
# =========================
router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a routing assistant. Your job is to classify the user's intent.\n"
                "Based on the <chat_history> and <latest_message>, "
                "you MUST classify the user's intent by outputting the 'IntentClassifier' JSON format.\n\n"
                "**Key Guidelines:**\n\n"
                "1. 'NEW_SEARCH': User asks for a COMPLETELY NEW and INDEPENDENT search\n"
                "   - Examples: 'Seoul cafes' (first query), 'Show me Busan hotels' (after talking about Seoul)\n"
                "   - Must have BOTH location AND category/intent clearly stated\n\n"
                "2. 'REFINEMENT': User is COMPLETING or CLARIFYING previous incomplete query\n"
                "   - Examples:\n"
                "     * AI asked '어디요?' → User: '해운대' (answering location)\n"
                "     * AI asked '뭘 찾으세요?' → User: '맛집' or '핫플' (answering category)\n"
                "     * User: '해운대' → User: '맛집' (completing partial query)\n"
                "   - Single keyword responses (맛집, 카페, 핫플, etc.) are ALMOST ALWAYS REFINEMENT\n"
                "   - Short 1-2 word answers to AI questions are REFINEMENT\n\n"
                "3. 'CONVERSATION': Casual chat or follow-up about previous answer\n"
                "   - Examples: 'how to get there?', 'tell me more', 'what time does it open?'\n\n"
                "**Critical Rules:**\n"
                "- If AI just asked a clarifying question (어디요?, 뭘 찾으세요?, etc.), "
                "classify next user input as 'REFINEMENT'\n"
                "- Single keywords like '맛집', '카페', '핫플', '명소' are REFINEMENT unless it's the first message\n"
                "- Single location names like '부산', '서울', '제주', '해운대' are REFINEMENT if AI asked for location\n"
                "- Only classify as NEW_SEARCH if user provides a COMPLETE new query with different context"
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "<latest_message>{input}</latest_message>"),
    ]
)

# Pydantic 모델을 LLM에 강제하는 라우터 체인
router_chain = router_prompt | global_llm.with_structured_output(IntentClassifier)


# =========================
# 3. 노드 함수 정의
# =========================
def router_node(state: AgentState) -> AgentState:
    """
    사용자 의도를 분류하는 라우터 노드
    """
    logger.info("[router_node] Starting intent classification")

    # 라우터에 전달할 히스토리 (최근 10개)
    chat_history = state.get("chat_history", [])[-10:]

    # 라우터 실행
    classification_result = router_chain.invoke(
        {"input": state["input"], "chat_history": chat_history}
    )
    classification_result = IntentClassifier.model_validate(classification_result)

    intent = classification_result.intent
    logger.info(f"[router_node] Classified intent: {intent}")

    # 의도에 따라 에이전트에 전달할 히스토리 필터링
    if intent == "NEW_SEARCH":
        # 새로운 검색이면 과거 기억 제거
        filtered_history = []
    else:
        # REFINEMENT 또는 CONVERSATION이면 전체 히스토리 유지
        filtered_history = chat_history

    return {**state, "intent": intent, "filtered_history": filtered_history}


_agent_chain = None


def get_agent_chain():
    """
    tools + prompt + llm_with_tools 를 한 번만 구성해서 재사용.
    """
    global _agent_chain
    if _agent_chain is not None:
        return _agent_chain

    # 도구 생성
    tools = create_nest_tools()

    # 에이전트 프롬프트 생성
    prompt = build_agent_prompt()

    # LLM에 도구 바인딩
    llm_with_tools = global_llm.bind_tools(tools)

    # 에이전트 체인 구성
    _agent_chain = prompt | llm_with_tools
    return _agent_chain


def agent_node(state: AgentState) -> AgentState:
    """
    도구를 호출하고 응답을 생성하는 에이전트 노드
    LangGraph의 ToolNode와 통합하여 작동
    """

    logger.info("[agent_node] Starting agent execution")

    agent_chain = get_agent_chain()

    # chat_history를 직접 사용
    # - 처음 실행 시: router가 필터링한 filtered_history를 가져옴 (chat_history에는 아직 없음)
    # - tools 실행 후: chat_history에 AIMessage + ToolMessage가 추가되어 있음
    chat_history = state.get("chat_history", [])
    filtered_history = state.get("filtered_history", [])

    # 기본 히스토리: 이미 있으면 그대로, 없으면 filtered_history를 시작점으로 사용
    # (사용자 입력은 프롬프트의 {input}에 주입되므로 chat_history에 중복 추가하지 않음)
    base_history = chat_history if chat_history else filtered_history
    messages_to_use = base_history

    # 에이전트 실행
    scratchpad = state.get("intermediate_steps", [])
    response = agent_chain.invoke(
        # 여기서 key들은 prompt에 동적으로 전달할 것
        {
            "input": state.get("input", ""),
            "chat_history": messages_to_use,
            "session_id": state.get("session_id"),
            "agent_scratchpad": scratchpad,  # LangGraph에서는 자동으로 관리됨
        }
    )
    response: AIMessage = cast(AIMessage, response)
    logger.info(f"[agent_node] Agent response: {response}")

    tool_calls = getattr(response, "tool_calls", [])

    # tool_calls가 있는지 확인
    if tool_calls:
        # 도구 호출이 필요한 경우
        # chat_history에 AIMessage 추가 (ToolNode가 이를 참조함)
        if base_history:
            new_history = base_history + [response]
        else:
            # 대화가 비어 있으면 현재 사용자 입력부터 시작
            new_history = [HumanMessage(content=state["input"]), response]

        return {
            **state,
            "chat_history": new_history,
            "intermediate_steps": scratchpad + [(response,)],
        }

    # 최종 응답
    value = getattr(response, "content", str(response))
    # value = response.content if hasattr(response, "content") else str(response)

    output = (
        json.dumps(value, ensure_ascii=False)
        if isinstance(value, (dict, list))
        else str(value)
    )
    if base_history:
        new_history = base_history + [response]
    else:
        new_history = [HumanMessage(content=state["input"]), response]

    return {**state, "chat_history": new_history, "output": output}


def should_continue(state: AgentState) -> str:
    """
    에이전트가 도구를 더 호출할지, 종료할지 결정
    """
    # chat_history의 마지막 메시지 확인
    # (agent_node가 AIMessage를 chat_history에 추가함)
    chat_history = state.get("chat_history", [])
    if not chat_history:
        logger.info("[should_continue] No chat history, ending")
        return END

    last_message = chat_history[-1]
    logger.info(f"[should_continue] Last message type: {type(last_message)}")

    # AIMessage이고 tool_calls가 있으면 tools 노드로
    if isinstance(last_message, AIMessage):
        tool_calls = getattr(last_message, "tool_calls", [])
        if tool_calls:
            logger.info(
                f"[should_continue] Found {len(tool_calls)} tool calls, going to tools"
            )
            return "tools"

    logger.info("[should_continue] No tool calls, ending")
    return END


# =========================
# 4. 그래프 구성
# =========================
def create_agent_graph():
    """
    LangGraph 기반 에이전트 그래프 생성
    """
    # StateGraph 초기화
    workflow = StateGraph(AgentState)

    # 도구 노드 생성
    tools = create_nest_tools()
    # ToolNode가 chat_history를 사용하도록 messages_key 설정
    tool_node = ToolNode(tools, messages_key="chat_history")

    # 노드 추가
    workflow.add_node("router", router_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # 엣지 정의
    # 시작 -> 라우터
    workflow.set_entry_point("router")

    # 라우터 -> 에이전트 (항상)
    workflow.add_edge("router", "agent")

    # 에이전트 -> 조건부 분기 (도구 호출 or 종료)
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )

    # 도구 -> 에이전트 (도구 실행 후 다시 에이전트로)
    workflow.add_edge("tools", "agent")

    # 그래프 컴파일
    return workflow.compile()


# 전역 그래프 인스턴스 (싱글톤)
agent_graph = create_agent_graph()
