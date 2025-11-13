from pydantic import BaseModel
from typing import Any, List

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