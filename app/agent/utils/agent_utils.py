from typing import Sequence
from langchain_core.messages import BaseMessage, HumanMessage


def get_last_human_message(messages: Sequence[BaseMessage]) -> HumanMessage:
    """히스토리에서 마지막 HumanMessage만 추출"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg

    return HumanMessage(content="")


def get_last_tool_message(messages: Sequence[BaseMessage]) -> BaseMessage:
    """히스토리에서 마지막 ToolMessage만 추출"""
    for msg in reversed(messages):
        if isinstance(msg, BaseMessage):
            return msg

    return BaseMessage(content="")
