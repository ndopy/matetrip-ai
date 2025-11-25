from typing import Sequence
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from app.common.logger import logger


def get_last_human_message(messages: Sequence[BaseMessage]) -> HumanMessage:
    """히스토리에서 마지막 HumanMessage만 추출"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg

    return HumanMessage(content="")


def get_last_tool_message(messages: Sequence[BaseMessage]) -> ToolMessage:
    """히스토리에서 마지막 ToolMessage만 추출"""
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            return msg

    return ToolMessage(content="")


def messages_after_last_human(messages: Sequence) -> list:
    """마지막 HumanMessage 이후의 메시지들만 반환"""
    for idx in range(len(messages) - 1, -1, -1):
        if getattr(messages[idx], "type", None) == "human":
            return list(messages[idx + 1 :])

    logger.warning("[extract_tool_data] No HumanMessage found")
    return []
