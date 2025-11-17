from fastapi import APIRouter
from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.agent.builder import build_stateful_agent

from app.schemas.chat import ChatRequest, ChatResponse, IntentClassifier
from app.service.agent_service import get_agent_response
from app.core.memory import get_session_history

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

router = APIRouter(prefix="/chat", tags=["chat"])

# AI 라우터 프롬프트
router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a routing assistant. Your job is to classify the user's intent.\n"
                "Based on the <chat_history> and <latest_message>, "
                "you MUST classify the user's intent by outputting the 'IntentClassifier' JSON format."
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

        classification_result = router_chain.invoke(
            {"input": request.query, "chat_history": full_history.messages}
        )

        intent = classification_result.intent

        print(f"AI Router Intent: {intent}")

        # [코드 기반 분기] 의도에 따라 일꾼에게 전달할 기억 선별
        history_to_pass = []

        if intent == "CONVERSATION":
            # [기억 사용 O] 후속 질문으로 모든 기억을 다 줌
            history_to_pass = full_history.messages
        else:
            # [기억 사용 X] 사용자의 말만 줌
            for msg in full_history.messages:
                if isinstance(msg, HumanMessage):
                    history_to_pass.append(msg)

        print(history_to_pass)

        # 1. 도구 생성
        user_tools = create_nest_tools()

        # 2. 에이전트 조립 (global_llm 재사용)
        agent = build_stateful_agent(global_llm, user_tools)

        # 3. 실행
        # 핵심 로직은 agent_service로 위임
        response_dict = get_agent_response(agent, request, history_to_pass)

        # 4. 대화 기록 수동 저장
        full_history.add_user_message(request.query)
        full_history.add_ai_message(response_dict["response"])

        # Pydantic 모델(ChatResponse)로 변환해 반환
        return ChatResponse(
            response=response_dict["response"], tool_data=response_dict["tool_data"]
        )

    except Exception as e:
        return ChatResponse(
            response=f"처리 중 오류가 발생했습니다. : {str(e)}", tool_data=[]
        )
