import httpx

from app.common.config import NaverSearchConfig


naverSearchConfig = NaverSearchConfig()


class NaverSearchService:
    def __init__(self):
        self.client_id = naverSearchConfig.NAVER_CLIENT_ID
        self.client_secret = naverSearchConfig.NAVER_CLIENT_SECRET
        self.blog_api_url = naverSearchConfig.NAVER_BLOG_SEARCH_URL
        self.image_api_url = naverSearchConfig.NAVER_IMAGE_SEARCH_URL

    def get_place_popularity_score(self, place_title: str, address: str) -> int:
        """
        장소의 인기도를 네이버 블로그 검색 결과 개수로 판단합니다.

        Args:
            place_title: 장소명
            address: 주소

        Returns:
            검색 결과 개수 (total count)
        """
        if not place_title or not address:
            return 0

        city = extract_city(address)
        query = f"{place_title} {city}"

        header = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        param = {"query": query, "display": 1, "sort": "sim"}  # 개수만 확인하므로 1개만

        try:
            response = httpx.get(
                self.blog_api_url,
                headers=header,
                params=param,
                timeout=10.0,
            )
            if response.status_code != 200:
                return 0

            result: dict = response.json()
            total_count = result.get("total", 0)
            return total_count

        except Exception as e:
            print(f"Popularity Check Error: {e}")
            return 0

    def search_review_urls(
        self,
        place_title: str,
        address: str,
        category: list[str] = [],
        display: int = 10,
    ) -> list[str]:

        if not place_title or not address:
            return []

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
        self, place_title: str, address: str, display: int = 10
    ) -> str | None:
        """
        네이버 이미지 검색 API로 장소 대표 이미지 URL을 가져옵니다.
        여러 검색어를 시도하고, 블로그 이미지를 필터링하여 대표 이미지를 선택합니다.

        Args:
            place_title: 장소명
            address: 주소
            display: 가져올 이미지 개수 (기본값 10)

        Returns:
            이미지 URL 또는 None
        """
        if not place_title or not address:
            return None

        city = extract_city(address)

        # 여러 검색어 시도 (외관/전경이 있는 이미지 우선)
        search_queries = [
            f"{place_title} {city} 외관",  # 외관 이미지 우선
            f"{place_title} {city} 전경",  # 전경 이미지
            f"{place_title} {city}",  # 기본 검색
        ]

        header = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        # 각 검색어로 시도
        for query in search_queries:
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
                    continue

                result: dict = response.json()
                items = result.get("items", [])

                if not items:
                    continue

                # 이미지 필터링: 블로그/개인 사진 제외
                filtered_image = self._filter_best_image(items, place_title)

                if filtered_image:
                    print(
                        f"Naver Image Search: {place_title}의 이미지를 찾았습니다. (검색어: {query})"
                    )
                    return filtered_image

            except Exception as e:
                print(f"Image Search Error for '{query}': {e}")
                continue

        print(f"Naver Image Search: {place_title}의 적절한 이미지를 찾지 못했습니다.")
        return None

    def _filter_best_image(self, items: list, place_title: str = "") -> str | None:
        """
        이미지 리스트에서 가장 적합한 대표 이미지를 선택합니다.

        필터링 기준:
        1. 블로그 이미지 제외 (blog.naver.com, tistory.com 등)
        2. 썸네일이 충분히 큰 이미지 우선
        3. 공식 사이트/포털 이미지 우선

        Args:
            items: 네이버 이미지 검색 결과 리스트
            place_title: 장소명 (로깅용)

        Returns:
            선택된 이미지 URL 또는 None
        """
        # 제외할 도메인 (블로그, SNS 등)
        excluded_domains = [
            "blog.naver.com",
            "blog.kakao.com",
            "m.blog.naver.com",
            "tistory.com",
            "instagram.com",
            "facebook.com",
            "pbs.twimg.com",  # 트위터 이미지
        ]

        # 우선순위 도메인 (공식 사이트, 포털 등)
        priority_domains = [
            "place.map.kakao.com",
            "map.naver.com",
            "search.naver.com",
            "img1.kakaocdn.net",
            "phinf.pstatic.net",  # 네이버 공식 이미지
        ]

        priority_images = []
        normal_images = []

        for item in items:
            link = item.get("link", "")
            sizewidth = item.get("sizewidth", "0")
            sizeheight = item.get("sizeheight", "0")

            if not link:
                continue

            # 제외 도메인 체크
            if any(domain in link for domain in excluded_domains):
                continue

            # 이미지 크기 체크 (너무 작은 이미지 제외)
            try:
                width = int(sizewidth)
                height = int(sizeheight)
                if width < 200 or height < 200:  # 최소 200x200
                    continue
            except (ValueError, TypeError):
                pass

            # 우선순위 도메인 체크
            if any(domain in link for domain in priority_domains):
                priority_images.append(link)
            else:
                normal_images.append(link)

        # 우선순위 이미지가 있으면 첫 번째 반환
        if priority_images:
            return priority_images[0]

        # 일반 이미지 중 첫 번째 반환
        if normal_images:
            return normal_images[0]

        # 필터링된 이미지가 없으면 원본 리스트의 첫 번째 반환
        if items:
            return items[0].get("link")

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
