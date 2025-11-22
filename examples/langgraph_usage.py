"""
LangGraph 기반 채팅 API 사용 예시

기존 /chat 엔드포인트와 새로운 /chat/v2 엔드포인트의 차이점:
- /chat: 기존 AgentExecutor 기반 (chat.py)
- /chat/v2: LangGraph 기반 (chat_v2.py)
"""

import requests
import json

# API 엔드포인트
BASE_URL = "http://localhost:8000"
CHAT_V2_URL = f"{BASE_URL}/chat/v2"

# 세션 ID (동일한 세션에서 대화를 이어가려면 같은 ID 사용)
SESSION_ID = "example-session-123"


def send_message(query: str, session_id: str = SESSION_ID):
    """
    LangGraph 기반 채팅 API에 메시지 전송

    Args:
        query: 사용자 메시지
        session_id: 세션 ID

    Returns:
        API 응답
    """
    payload = {"query": query, "session_id": session_id}

    print(f"\n{'='*60}")
    print(f"사용자: {query}")
    print(f"세션 ID: {session_id}")
    print(f"{'='*60}")

    try:
        response = requests.post(CHAT_V2_URL, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"\nAI 응답: {result.get('response', '응답 없음')}")
        print(f"도구 사용: {len(result.get('tool_data', []))}개")

        return result

    except requests.exceptions.RequestException as e:
        print(f"오류 발생: {e}")
        return None


def example_new_search():
    """예시 1: 새로운 검색 (NEW_SEARCH)"""
    print("\n" + "=" * 60)
    print("예시 1: 새로운 검색")
    print("=" * 60)

    # 완전히 새로운 검색 - 위치와 카테고리가 모두 명확함
    send_message("서울 강남구 카페 추천해줘", "session-new-search-1")


def example_refinement():
    """예시 2: 검색 결과 정제 (REFINEMENT)"""
    print("\n" + "=" * 60)
    print("예시 2: 검색 결과 정제")
    print("=" * 60)

    session_id = "session-refinement-1"

    # 1. 불완전한 첫 쿼리
    send_message("해운대", session_id)

    # 2. AI가 역질문할 것으로 예상 (e.g., "뭘 찾으세요?")
    # 사용자가 카테고리만 답변 -> REFINEMENT로 분류되어야 함
    send_message("맛집", session_id)


def example_conversation():
    """예시 3: 일반 대화 (CONVERSATION)"""
    print("\n" + "=" * 60)
    print("예시 3: 일반 대화")
    print("=" * 60)

    session_id = "session-conversation-1"

    # 1. 검색 수행
    send_message("부산 해운대 카페 추천해줘", session_id)

    # 2. 검색 결과에 대한 추가 질문 (일반 대화)
    send_message("거기 어떻게 가?", session_id)


def example_multi_turn():
    """예시 4: 여러 턴의 대화"""
    print("\n" + "=" * 60)
    print("예시 4: 여러 턴의 대화")
    print("=" * 60)

    session_id = "session-multi-turn-1"

    # 턴 1: 첫 검색
    send_message("제주도 핫플 알려줘", session_id)

    # 턴 2: 다른 주제로 새로운 검색
    send_message("서울 명동 쇼핑 명소", session_id)

    # 턴 3: 두 번째 검색에 대한 질문
    send_message("영업시간이 어떻게 돼?", session_id)


def check_health():
    """헬스체크"""
    try:
        response = requests.get(f"{CHAT_V2_URL}/health")
        response.raise_for_status()
        print("\n" + "=" * 60)
        print("LangGraph API 헬스체크")
        print("=" * 60)
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except requests.exceptions.RequestException as e:
        print(f"헬스체크 실패: {e}")


if __name__ == "__main__":
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║         LangGraph 기반 채팅 API 사용 예시                    ║
╚══════════════════════════════════════════════════════════════╝

이 스크립트는 새로운 /chat/v2 엔드포인트를 사용하는 방법을 보여줍니다.

LangGraph의 주요 기능:
1. 자동 라우팅: NEW_SEARCH / REFINEMENT / CONVERSATION
2. 대화 히스토리 관리: 의도에 따라 자동으로 필터링
3. 도구 호출: LangGraph의 ToolNode를 통한 자동 관리
4. 상태 관리: StateGraph를 통한 명확한 상태 흐름

사용 전 주의사항:
- FastAPI 서버가 http://localhost:8000 에서 실행 중이어야 합니다
- 서버 실행: python main.py 또는 uvicorn main:app --reload
    """
    )

    # 헬스체크
    check_health()

    # 예시 실행
    while True:
        print("\n\n실행할 예시를 선택하세요:")
        print("1. 새로운 검색 (NEW_SEARCH)")
        print("2. 검색 결과 정제 (REFINEMENT)")
        print("3. 일반 대화 (CONVERSATION)")
        print("4. 여러 턴의 대화")
        print("5. 직접 입력")
        print("0. 종료")

        choice = input("\n선택: ").strip()

        if choice == "1":
            example_new_search()
        elif choice == "2":
            example_refinement()
        elif choice == "3":
            example_conversation()
        elif choice == "4":
            example_multi_turn()
        elif choice == "5":
            query = input("메시지 입력: ")
            session = input("세션 ID (엔터=기본값): ").strip() or SESSION_ID
            send_message(query, session)
        elif choice == "0":
            print("\n종료합니다.")
            break
        else:
            print("잘못된 선택입니다.")
