from fastapi import APIRouter, Cookie, HTTPException
from typing import Annotated

from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.agent.builder import build_stateful_agent

from app.schemas.chat import ChatRequest, ChatResponse
from app.service.agent_service import get_agent_response

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post("/", response_model=ChatResponse)
async def ask_agent(
    request: ChatRequest,
    # 쿠키 이름이 브라우저 쿠키 이름과 같아야 함
    accessToken: Annotated[str | None, Cookie()] = None
):
    """
    AI 에이전트 및 챗봇 실행 엔드포인트
    (대화 응답 + 구조화된 도구 데이터를 함께 반환)
    """
    if not accessToken:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다 (쿠키 없음)")
    
    try:
        # 1. 도구 생성
        user_tools = create_nest_tools(user_token=accessToken)

        # 2. 에이전트 조립 (global_llm 재사용)
        agent = build_stateful_agent(global_llm, user_tools)

        # 3. 실행
        # 핵심 로직은 agent_service로 위임
        response_dict = get_agent_response(agent, request.query, request.session_id)

        # Pydantic 모델(ChatResponse)로 변환해 반환
        return ChatResponse(
            response=response_dict["response"],
            tool_data=response_dict["tool_data"]
        )
    
    except Exception as e:
        return ChatResponse(
            response=f"처리 중 오류가 발생했습니다. : {str(e)}",
            tool_data=[]
            )
    
    