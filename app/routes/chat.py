import json
import time
from fastapi import APIRouter
from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.agent.builder import build_stateful_agent
from app.common.logger import logger

from app.schemas.chat import ChatRequest, ChatResponse, IntentClassifier
from app.service.agent_service import get_agent_response
from app.core.memory import get_session_history

from langchain_classic.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage


router = APIRouter(prefix="/chat", tags=["chat"])

# AI 라우터 프롬프트
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
                "   - **Context is NOT needed.**\n\n"

                "2. 'REFINEMENT': User is COMPLETING or MODIFYING previous query based on context\n"
                "   - **[CRITICAL] References to previous items:** 'first one', 'second place', 'that place', 'near there', 'around here'\n"
                "   - Examples:\n"
                "     * 'Recommend restaurants **near the first one**' (This is REFINEMENT because it refers to the previous list)\n"
                "     * 'How about the second option?'\n"
                "     * 'Show me cheaper ones'\n"
                "     * 'Only Korean food'\n\n"

                "3. 'CONVERSATION': Casual chat or follow-up about previous answer\n"
                "   - Examples: 'how to get there?', 'tell me more', 'what time does it open?'\n\n"

                "4. 'FOLLOW_UP': User wants to perform a SPECIFIC ACTION on the result of a previous tool\n"
                "   - Examples: 'Add the first one to my schedule', 'Save the first one', 'Make a plan with these places', 'Put option 2 in the itinerary'\n"
                "   - Use this when user switches from 'Searching' to 'Acting' (e.g., Search -> Add, Search -> Plan)\n"
                "   - Must refer to items found in the previous turn (e.g., 'this place', 'that restaurant', 'option 1')\n"
                "   - Context IS required (must know 'what' to add)\n\n"
                "**Critical Rules:**\n"
                "- If AI just asked a clarifying question (어디요?, 뭘 찾으세요?, etc.), "
                "classify next user input as 'REFINEMENT'\n"
                "- Single keywords like '맛집', '카페', '핫플', '명소' are REFINEMENT unless it's the first message\n"
                "- Single location names like '부산', '서울', '제주', '해운대' are REFINEMENT if AI asked for location\n"
                "- Only classify as NEW_SEARCH if user provides a COMPLETE new query with different context"
                "- If the user mentions **ordinal numbers** (first, 1st, second, 2nd) or **demonstratives** (this, that, there), it is **NEVER** 'NEW_SEARCH'. Classify as 'REFINEMENT' or 'FOLLOW_UP_WORK'.\n"
                "- Only classify as NEW_SEARCH if user provides a COMPLETE new query with different context."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "<latest_message>{input}</latest_message>"),
    ]
)

# Pydantic 모델을 LLM에 강제하는 라우터 체인 생성
router_chain = router_prompt | global_llm.with_structured_output(IntentClassifier)


@router.post("", response_model=ChatResponse)
async def ask_agent(request: ChatRequest) -> ChatResponse:
    """
    AI 에이전트 및 챗봇 실행 엔드포인트
    (대화 응답 + 구조화된 도구 데이터를 함께 반환)
    """
    try:
        # [라우터 실행] AI에게 사용자의 의도부터 물어봄
        full_history = get_session_history(request.session_id)

        t0 = time.perf_counter()
        raw = router_chain.invoke(
            {"input": request.query, "chat_history": full_history.messages}
        )
        t1 = time.perf_counter()
        logger.info(f"[router_chain.invoke] {t1 - t0:.4f} seconds")
        classification_result: IntentClassifier = IntentClassifier.model_validate(raw)
        intent = classification_result.intent

        logger.info(f"AI Router Intent: {intent}")

        # [코드 기반 분기] 의도에 따라 일꾼에게 전달할 기억 선별
        history_to_pass = []

        if intent == "NEW_SEARCH":
            # [완전히 새로운 검색] 과거 기억 없이 시작 (빈 히스토리)
            history_to_pass = []
        elif intent == "REFINEMENT":
            # [기존 결과 정제] 전체 대화 맥락 필요 (이전 검색 결과 포함)
            history_to_pass = full_history.messages
        elif intent == "CONVERSATION":
            # [일반 대화] 전체 대화 맥락 필요
            history_to_pass = full_history.messages
        elif intent == "FOLLOW_UP":
            # [기억 유지] 결과기반 작업(저장, 계획) -> "무엇을" 저장할지 알아야 하므로 문맥 필수
            history_to_pass = full_history.messages

        logger.info(f"history_to_pass : {history_to_pass}")
        logger.info(f"[AI의 의도: ] {intent}")

        # 1. 도구 생성
        user_tools = create_nest_tools()

        # 2. 에이전트 조립 (global_llm 재사용)
        t2 = time.perf_counter()
        agent: AgentExecutor = build_stateful_agent(global_llm, user_tools)
        t3 = time.perf_counter()
        logger.info(f"[build_stateful_agent] {t3 - t2:.4f} seconds")

        # 3. 실행
        # 핵심 로직은 agent_service로 위임
        t4 = time.perf_counter()
        agent_response = get_agent_response(agent, request, history_to_pass)
        chat_response = agent_response.chat_response
        internal_logs = agent_response.internal_tool_log

        t5 = time.perf_counter()
        logger.info(f"[get_agent_response] {t5 - t4:.4f} seconds")

        # 4. 대화 기록 수동 저장
        full_history.add_user_message(request.query)
        full_history.add_ai_message(chat_response.response)

        # (2) [신규] 도구 데이터(tool_data) 저장
        #     이걸 저장해야 "거기 전화번호 뭐야?" 같은 후속 질문에 대답할 수 있습니다.
        #     Bedrock은 [AI의 도구 요청] -> [도구의 실행 결과] 순서를 엄격히 따집니다.
        if internal_logs:
            # [단계 A] AI의 "도구 호출 요청(Request)" 복원 및 저장 (AIMessage)
            ai_tool_calls = []

            for log in internal_logs:
                ai_tool_calls.append({
                    "name": log.tool_name,
                    "args": log.tool_args,      # 저장해둔 진짜 인자
                    "id": log.tool_call_id      # 저장해둔 진짜 ID (tooluse_...)
                })

            # tool_calls 정보가 담긴 AIMessage를 먼저 저장합니다.
            # (이게 없으면 "Expected toolResult blocks..." 에러가 발생합니다)
            full_history.add_message(AIMessage(content="", tool_calls=ai_tool_calls))

            # [단계 B] 도구 실행 "결과(Result)" 저장 (ToolMessage)
            for log in internal_logs:
                tool_msg = ToolMessage(
                    content=log.tool_output_str,   # 미리 변환해둔 결과 문자열
                    tool_call_id=log.tool_call_id, # [중요] 위 요청 ID와 똑같아야 함
                    name=log.tool_name
                )
                full_history.add_message(tool_msg)

        

        return chat_response
    except Exception as e:
        return ChatResponse(
            response=f"처리 중 오류가 발생했습니다. : {str(e)}", tool_data=[]
        )

