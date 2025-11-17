"""Agent Tool 통합 테스트"""
from app.core.llm import global_llm
from app.tools import create_nest_tools
from app.agent.builder import build_stateful_agent


def test_agent_with_popular_places():
    """Agent를 통해 인기 장소 추천 도구가 잘 호출되는지 테스트"""

    # Tools 생성
    tools = create_nest_tools()
    print(f"\n📋 등록된 도구 개수: {len(tools)}")
    print("등록된 도구 목록:")
    for tool in tools:
        print(f"  - {tool.name}")

    # Agent 생성
    agent_executor = build_stateful_agent(global_llm, tools)

    # 테스트 쿼리
    test_queries = [
        "제주도에서 사람들이 많이 가는 곳 추천해줘",
        "서울에서 인기 있는 맛집 알려줘",
    ]

    print("\n" + "="*80)
    for query in test_queries:
        print(f"\n🧪 테스트 쿼리: {query}")
        print("-"*80)

        try:
            result = agent_executor.invoke({
                "input": query,
                "session_id": "test_session_123"
            })

            # 도구 호출 여부 확인
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                print("\n✅ 도구 호출됨:")
                for step in intermediate_steps:
                    action, observation = step
                    print(f"  - 도구: {action.tool}")
                    print(f"  - 입력: {action.tool_input}")

            # 최종 응답
            output = result.get("output", "")
            print(f"\n📝 Agent 응답:\n{output[:200]}...")

        except Exception as e:
            print(f"\n❌ 에러 발생: {e}")
            import traceback
            traceback.print_exc()

        print("="*80)


if __name__ == "__main__":
    test_agent_with_popular_places()
