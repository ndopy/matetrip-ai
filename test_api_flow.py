"""
실제 API를 호출해서 전체 플로우 테스트
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# 세션 ID
session_id = "test-session-123"

print("=" * 80)
print("1단계: 여행 코스 생성 요청")
print("=" * 80)

# 첫 번째 요청: 여행 코스 생성
response1 = requests.post(
    f"{BASE_URL}/chat/v2",
    json={
        "session_id": session_id,
        "query": "제주도에 여행갈건데, 연동에서 시작해서 해녀촌을 경유하고 김녕해수욕장을 경유하는 1박 2일 여행 코스 만들어줘"
    }
)

print(f"Status: {response1.status_code}")
result1 = response1.json()
print(f"Intent: {result1.get('intent')}")
print(f"Response: {result1.get('response')[:200]}...")
print(f"Tools used: {len(result1.get('tool_calls', []))}")

print("\n" + "=" * 80)
print("2단계: 장소 제외 요청 (한라수목원 대신 다른 곳)")
print("=" * 80)

# 두 번째 요청: 장소 제외
response2 = requests.post(
    f"{BASE_URL}/chat/v2",
    json={
        "session_id": session_id,
        "query": "근데 한라수목원 별론데 이거 대신 다른 거 없어?"
    }
)

print(f"Status: {response2.status_code}")
result2 = response2.json()
print(f"Intent: {result2.get('intent')}")
print(f"Response: {result2.get('response')}")
print(f"Tools used: {len(result2.get('tool_calls', []))}")

# 상세 결과 출력
if result2.get('response') and '추천 기록이 없어' in result2.get('response'):
    print("\n❌ 문제 발생: 이전 추천 기록이 없다고 나옴!")
else:
    print("\n✅ 성공: 장소 제외가 정상적으로 처리됨!")
