import httpx
import time
from typing import List, Dict

from app.common.config import KakaoLocalConfig

kakaoLocalConfig = KakaoLocalConfig()


class KakaoLocalService:
    """카카오 Local API를 사용한 장소 검색 서비스"""

    def __init__(self):
        self.api_key = kakaoLocalConfig.KAKAO_REST_API_KEY
        self.api_url = kakaoLocalConfig.KAKAO_LOCAL_API_URL

    def search_places_by_category(
        self,
        category_code: str,
        x: float,
        y: float,
        radius: int = 20000,
        max_pages: int = 5,
    ) -> List[Dict]:
        """
        카테고리별로 장소를 검색합니다.

        Args:
            category_code: 카테고리 코드 (FD6: 음식점, AT4: 관광명소 등)
            x: 중심 경도
            y: 중심 위도
            radius: 검색 반경 (미터, 최대 20000)
            max_pages: 최대 페이지 수

        Returns:
            장소 리스트
        """
        all_places = []
        page = 1

        headers = {
            "Authorization": f"KakaoAK {self.api_key}",
            "KA": "sdk/1.0 os/python lang/ko-KR origin/http://localhost",
        }

        while page <= max_pages:
            params = {
                "category_group_code": category_code,
                "x": x,
                "y": y,
                "radius": radius,
                "page": page,
                "size": 15,  # 페이지당 최대 15개
            }

            try:
                response = httpx.get(
                    self.api_url, headers=headers, params=params, timeout=10.0
                )

                if response.status_code != 200:
                    print(f"Kakao API Error: {response.status_code} - {response.text}")
                    break

                data = response.json()
                documents = data.get("documents", [])
                meta = data.get("meta", {})

                if not documents:
                    break

                all_places.extend(documents)
                print(
                    f"[카카오 검색] 카테고리: {category_code}, 페이지: {page}, 결과: {len(documents)}개"
                )

                # 더 이상 페이지가 없으면 종료
                if meta.get("is_end", True):
                    break

                page += 1
                time.sleep(0.1)  # API 호출 제한 방지

            except Exception as e:
                print(f"Kakao API Exception: {e}")
                break

        return all_places

    def convert_to_place_data(self, kakao_place: Dict) -> Dict:
        """
        카카오 장소 데이터를 우리 DB 형식으로 변환합니다.

        Args:
            kakao_place: 카카오 API 응답 데이터

        Returns:
            Place 모델에 맞는 데이터
        """
        # 카카오 카테고리 파싱
        # 예: "여행 > 관광,명소 > 테마거리" -> ["여행", "관광,명소", "테마거리"]
        category_name = kakao_place.get("category_name", "")
        categories = []
        if category_name:
            # ">" 기준으로 split하고 앞뒤 공백 제거
            categories = [cat.strip() for cat in category_name.split(">")]

        return {
            "title": kakao_place.get("place_name", ""),
            "address": kakao_place.get("address_name", ""),
            "categories": categories,  # 파싱된 카테고리 배열
            "longitude": float(kakao_place["x"]) if kakao_place.get("x") else None,
            "latitude": float(kakao_place["y"]) if kakao_place.get("y") else None,
            "kakao_place_id": kakao_place.get("id", ""),  # 중복 체크용
            "phone": kakao_place.get("phone", ""),
            "place_url": kakao_place.get("place_url", ""),
        }
