import httpx

from app.common.config import NaverSearchConfig


naverSearchConfig = NaverSearchConfig()


class NaverSearchService:
    def __init__(self):
        self.client_id = naverSearchConfig.NAVER_CLIENT_ID
        self.client_secret = naverSearchConfig.NAVER_CLIENT_SECRET
        self.blog_api_url = naverSearchConfig.NAVER_BLOG_SEARCH_URL
        self.image_api_url = naverSearchConfig.NAVER_IMAGE_SEARCH_URL

    def search_review_urls(
        self, place_title: str, address: str, category: list[str], display: int = 10
    ) -> list[str]:

        city = extract_city(address)
        query = f"{place_title} {city} 리뷰"

        header = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        param = {"query": query, "display": display, "sort": "sim"}

        try:
            # naver blog 검색 API에 GET 요청
            response = httpx.get(
                self.blog_api_url,
                headers=header,
                params=param,
                timeout=10.0,  # 10초 timeout
            )
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return []

            result: dict = response.json()
            items = result.get("items", [])
            urls = [
                item.get("link") for item in items if item.get("link")
            ]  # 리스트 컴프레핸션 문법은 없으면 빈 배열 반환해서 예외 처리 x
            print(f"Naver Search Service: {len(urls)}개의 URL을 찾았습니다.")
            return urls
        except Exception as e:
            print(f"Error: {e}")
            return []

    def search_place_image(
        self, place_title: str, address: str, display: int = 1
    ) -> str | None:
        """
        네이버 이미지 검색 API로 장소 대표 이미지 URL을 가져옵니다.

        Args:
            place_title: 장소명
            address: 주소
            display: 가져올 이미지 개수 (기본값 1)

        Returns:
            이미지 URL 또는 None
        """
        city = extract_city(address)
        query = f"{place_title} {city}"

        header = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        param = {
            "query": query,
            "display": display,
            "sort": "sim",  # 정확도순
            "filter": "large",  # 큰 이미지만
        }

        try:
            response = httpx.get(
                self.image_api_url,
                headers=header,
                params=param,
                timeout=10.0,
            )
            if response.status_code != 200:
                print(f"Image Search Error: {response.status_code}")
                return None

            result: dict = response.json()
            items = result.get("items", [])

            if items and len(items) > 0:
                image_url = items[0].get("link")
                print(f"Naver Image Search: {place_title}의 이미지를 찾았습니다.")
                return image_url

            print(f"Naver Image Search: {place_title}의 이미지를 찾지 못했습니다.")
            return None

        except Exception as e:
            print(f"Image Search Error: {e}")
            return None


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
