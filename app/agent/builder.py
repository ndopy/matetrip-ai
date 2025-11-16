from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def build_stateful_agent(llm, tools):
    """
    LLM과 도구(Tools)를 결합하여 기억력을 가진 에이전트를 만듭니다.
    """
    # 1. 시스템 프롬프트
    system_prompt = (
        "You are a helpful and accurate AI assistant for a travel planning service.\n\n"
        
        "**<response_format_guide>**\n"
        "When you get results from a tool (like `search_places`), that data contains technical fields (e.g., `x`, `y`, `id`).\n"
        "In your text response to the user, **NEVER** mention these technical fields.\n"
        "**ONLY** use human-readable information like `name`, `road_address`, `phone`, and `category` to create a natural summary.\n"
        "**</response_format_guide>**\n"
    )

    # chat_history: 이전 대화 내용을 넣을 공간
    # agent_scratchpad: AI가 도구를 사용한 생각의 과정을 적는 공간
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("system", "The user's session ID is: {session_id}"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 2. 에이전트 생성 (LLM + 도구 + 프롬프트)
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # 3. 실행기 생성
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        return_intermediate_steps=True,
        max_iterations=15,
    )

    return agent_executor