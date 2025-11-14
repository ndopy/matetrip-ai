from pydantic import BaseModel, Field
from typing import Any, List, Literal

class ChatRequest(BaseModel):
    query: str
    session_id: str

class ToolCallData(BaseModel):
    """
    프론트엔드가 어떤 도구의 결과인지 식별할 수 있도록
    도구 이름과 원본 데이터를 함께 캡슐화
    """
    tool_name: str
    tool_output: Any
    frontend_actions: List[str] = []

class ChatResponse(BaseModel):
    """
    프론트엔드가 필요한 모든 정보를 담는 최종 응답 모델
    """
    response: str
    tool_data: List[ToolCallData] = []

class IntentClassifier(BaseModel):
    """
    라우터 AI가 반환할 Pydantic 모델 (JSON 양식) 정의
    """
    intent: Literal["TOOL_USE", "CONVERSATION"] = Field(
        description=(
            "Classify as 'TOOL_USE' if the user needs new info (search, create).\n"
            "Classify as 'CONVERSATION' for simple chat or follow-ups about the last response."
        )
    )