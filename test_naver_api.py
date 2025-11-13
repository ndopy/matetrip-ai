import httpx
import json

# 환경 변수에서 가져오기
import os
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

place_title = "경복궁"
address = "서울특별시 종로구 사직로 161 (세종로)"

# extract_city 함수
def extract_city(address: str) -> str:
    address_parts = address.split()
    for part in address_parts:
        if "시" in part and part != "시":
            return part.replace("시", "").replace("특별", "").replace("광역", "")
        elif "구" in part and part != "구":
            return part.replace("구", "")
        elif "군" in part and part != "군":
            return part.replace("군", "")
    return address_parts[0] if len(address_parts) > 0 else ""

city = extract_city(address)
query = f"{place_title} {city} 리뷰"

print(f"Place Title: {place_title}")
print(f"Address: {address}")
print(f"Extracted City: {city}")
print(f"Search Query: {query}")
print(f"\nNaver Client ID: {NAVER_CLIENT_ID[:10]}..." if NAVER_CLIENT_ID else "None")
print(f"Naver Client Secret: {NAVER_CLIENT_SECRET[:10]}..." if NAVER_CLIENT_SECRET else "None")
print("-" * 80)

header = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}
param = {"query": query, "display": 10, "sort": "sim"}

try:
    response = httpx.get(
        "https://openapi.naver.com/v1/search/blog.json",
        headers=header,
        params=param,
        timeout=10.0,
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response:")
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    items = result.get("items", [])
    urls = [item.get("link") for item in items if item.get("link")]
    print(f"\n총 {len(urls)}개의 URL 발견:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")

except Exception as e:
    print(f"Error: {e}")
