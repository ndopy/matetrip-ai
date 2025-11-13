# app/core/memory.py
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

# 전역 변수로 메모리에 대화 기록 저장 (서버 껐다 켜면 사라짐)
# 실제 서비스에서는 Redis 등을 사용해야 함
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    session_id에 해당하는 대화 기록을 반환합니다.
    없으면 새로 만듭니다.
    """
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]