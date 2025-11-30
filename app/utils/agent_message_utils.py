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


def get_messages_after_last_human(messages: Sequence) -> list:
    """마지막 HumanMessage 이후의 메시지들만 반환"""
    for idx in range(len(messages) - 1, -1, -1):
        if getattr(messages[idx], "type", None) == "human":
            return list(messages[idx + 1 :])

    logger.warning("[extract_tool_data] No HumanMessage found")
    return []


def prepare_messages_for_bedrock(
    messages: Sequence[BaseMessage], max_count: int = 10
) -> list[BaseMessage]:
    """
    Bedrock 제약에 맞게 메시지 준비
    - 최근 N개만 사용
    - 첫 메시지가 반드시 HumanMessage가 되도록 조정
    """
    # 최근 N개만 사용
    recent = messages[-max_count:] if len(messages) > max_count else list(messages)

    # 첫 번째 HumanMessage 찾기
    first_human_idx = next(
        (idx for idx, msg in enumerate(recent) if msg.type == "human"),
        None,
    )

    if first_human_idx is None:
        # HumanMessage가 없으면 전체에서 마지막 것 찾기
        last_human = next(
            (msg for msg in reversed(messages) if msg.type == "human"),
            None,
        )
        return [last_human] if last_human else []

    # 첫 HumanMessage 이전 메시지들 제거
    if first_human_idx > 0:
        return list(recent[first_human_idx:])
    return recent if isinstance(recent, list) else list(recent)
