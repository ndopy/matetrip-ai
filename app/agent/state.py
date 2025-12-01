from typing import Annotated, List, Literal, Sequence
import operator
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from app.schemas.place import SimplePlace


class AgentState(TypedDict, total=False):
    """LangGraph 상태 타입 분리 (순환 import 방지)"""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    intent: Literal["NEW_SEARCH", "REFINEMENT", "CONVERSATION", "FOLLOW_UP"] | None
    last_recommended_places: List[SimplePlace]
    excluded_place_ids: List[str]  # 제외할 장소 ID 리스트 (도구 호출 시 사용)
