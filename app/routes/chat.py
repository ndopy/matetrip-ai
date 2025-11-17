import logging
from fastapi import APIRouter
from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.agent.builder import build_stateful_agent

from app.schemas.chat import ChatRequest, ChatResponse, IntentClassifier
from app.service.agent_service import get_agent_response
from app.core.memory import get_session_history

from langchain_classic.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)
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
                "**Key Guidelines:**\n"
                "- 'NEW_SEARCH': User asks for a DIFFERENT location/category (e.g., 'Seoul cafes' → 'Busan restaurants')\n"
                "- 'REFINEMENT': User filters existing results (e.g., 'show only Korean food', 'cheaper ones')\n"
                "- 'CONVERSATION': Casual chat or follow-up about previous answer (e.g., 'how to get there?')\n\n"
                "**Critical:** If the user mentions a NEW location that differs from previous search context, "
                "classify as 'NEW_SEARCH', NOT 'REFINEMENT'."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "<latest_message>{input}</latest_message>"),
    ]
)

# Pydantic 모델을 LLM에 강제하는 라우터 체인 생성
router_chain = router_prompt | global_llm.with_structured_output(IntentClassifier)


@router.post("/", response_model=ChatResponse)
async def ask_agent(request: ChatRequest) -> ChatResponse:
    """
    AI 에이전트 및 챗봇 실행 엔드포인트
    (대화 응답 + 구조화된 도구 데이터를 함께 반환)
    """
    try:
        # [라우터 실행] AI에게 사용자의 의도부터 물어봄
        full_history = get_session_history(request.session_id)

        raw = router_chain.invoke(
            {"input": request.query, "chat_history": full_history.messages}
        )
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

        logger.info(f"history_to_pass : {history_to_pass}")

        # 1. 도구 생성
        user_tools = create_nest_tools()

        # 2. 에이전트 조립 (global_llm 재사용)
        agent: AgentExecutor = build_stateful_agent(global_llm, user_tools)

        # 3. 실행
        # 핵심 로직은 agent_service로 위임
        chatResponse: ChatResponse = get_agent_response(agent, request, history_to_pass)

        # 4. 대화 기록 수동 저장
        full_history.add_user_message(request.query)
        # full_history.add_ai_message(response_dict"response"])
        full_history.add_ai_message(chatResponse.response)
        return chatResponse

    except Exception as e:
        return ChatResponse(
            response=f"처리 중 오류가 발생했습니다. : {str(e)}", tool_data=[]
        )
