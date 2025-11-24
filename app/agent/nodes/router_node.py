from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.graph import AgentState
from schemas.chat import IntentClassifier
from app.common.logger import logger
from app.core.llm import global_llm


# =========================
# 2. 라우터 프롬프트
# =========================
router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a routing assistant. Classify the user's intent.\n\n"
                "**CRITICAL RULE: Check the last AI message first!**\n"
                "- If the last AI message is a QUESTION, the user's response is ALWAYS 'REFINEMENT'\n"
                "- Questions end with '?' or ask for clarification (어디, 무엇, 어떤, etc.)\n\n"
                "**Key Guidelines:**\n\n"
                "1. 'REFINEMENT': User is answering AI's question or adding missing info\n"
                "   - Examples:\n"
                "     * AI: '어떤 지역의 양식 식당을 찾으시는 건가요?' → User: '부산이 좋을 것 같아'\n"
                "     * AI: '어디요?' → User: '해운대'\n"
                "     * AI asked for category → User: '맛집', '카페'\n\n"
                "2. 'NEW_SEARCH': Completely new search with location AND category\n"
                "   - Must have BOTH location AND category in ONE message\n"
                "   - Examples: '서울 카페', '부산 호텔', '강남 맛집'\n"
                "   - NOT examples: '부산' (no category), '카페' (no location)\n\n"
                "3. 'CONVERSATION': Follow-up about search results already shown\n"
                "   - Examples: '거기 어떻게 가?', 'tell me more', '영업시간은?'\n\n"
                "**Decision Process:**\n"
                "1. Is the last AI message a question? → REFINEMENT\n"
                "2. Does user message have location + category? → NEW_SEARCH\n"
                "3. Is user asking about previous results? → CONVERSATION\n"
                "4. Otherwise → REFINEMENT"
            ),
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# =========================
# 라우터 체인
# =========================
router_chain = router_prompt | global_llm.with_structured_output(IntentClassifier)


# =========================
# 라우터 노드
# =========================
def router_node(state: AgentState) -> AgentState:
    """의도 분류 노드"""
    logger.info("[router_node] Starting intent classification")

    messages = state.get("messages", [])
    logger.info(f"[router_node] Messages count: {len(messages)}")

    # 최근 10개 메시지만 사용
    recent_messages = messages[-10:] if len(messages) > 10 else messages

    # 의도 분류
    classification = router_chain.invoke({"messages": recent_messages})
    classification = IntentClassifier.model_validate(classification)

    intent = classification.intent
    logger.info(f"[router_node] Classified intent: {intent}")

    return {
        "intent": intent,
    }
