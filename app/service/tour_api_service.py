"""
한국관광공사 Tour API 4.0 서비스

주요 기능:
- 지역기반 관광정보 조회
- 컨텐츠 타입별 필터링 (관광지, 문화시설, 음식점 등)
- 상세 정보 조회 (이미지, 주소 등)
"""

import logging
from typing import Dict, List, Optional, cast

import httpx

from app.common.config import TourAPIConfig
from app.data.tour_categories import TourCategoryMapper

logger = logging.getLogger(__name__)
tourAPIConfig = TourAPIConfig()


class TourAPIService:
    """한국관광공사 Tour API 4.0 서비스"""

    BASE_URL = tourAPIConfig.TOUR_API_BASE_URL
    SERVICE_KEY = tourAPIConfig.TOUR_API_KEY

    # 컨텐츠 타입 (contenttypeid)
    CONTENT_TYPES = {
        "tourism": "12",  # 관광지
        "culture": "14",  # 문화시설
        "festival": "15",  # 축제/공연/행사
        "course": "25",  # 여행코스
        "leisure": "28",  # 레포츠
        "accommodation": "32",  # 숙박
        "shopping": "38",  # 쇼핑
        "food": "39",  # 음식점
    }

    # 지역코드 (areaCode)
    AREA_CODES = {
        "서울": "1",
        "인천": "2",
        "대전": "3",
        "대구": "4",
        "광주": "5",
        "부산": "6",
        "울산": "7",
        "세종": "8",
        "경기": "31",
        "강원": "32",
        "충북": "33",
        "충남": "34",
        "경북": "35",
        "경남": "36",
        "전북": "37",
        "전남": "38",
        "제주": "39",
    }

    def __init__(self):
        self.timeout = 30.0  # Tour API는 응답이 느릴 수 있음

    def search_area_based_list(
        self,
        area_code: str,
        content_type_id: Optional[str] = None,
        sigungu_code: Optional[str] = None,
        page: int = 1,
        num_of_rows: int = 100,
    ) -> List[Dict]:
        """
        지역 기반 관광정보 조회

        Args:
            area_code: 지역코드 (1:서울, 6:부산 등)
            content_type_id: 컨텐츠 타입 (12:관광지, 14:문화시설 등)
            sigungu_code: 시군구코드 (선택)
            page: 페이지 번호
            num_of_rows: 한 페이지 결과 수 (최대 1000)

        Returns:
            관광정보 리스트
        """
        url = f"{self.BASE_URL}/areaBasedList2"

        params = {
            "serviceKey": self.SERVICE_KEY,
            "numOfRows": num_of_rows,
            "pageNo": page,
            "MobileOS": "ETC",
            "MobileApp": "MateTrip",
            "_type": "json",
            "arrange": "A",  # 제목순 정렬
            "areaCode": area_code,
        }

        # 선택적 파라미터
        if content_type_id:
            params["contentTypeId"] = content_type_id

        if sigungu_code:
            params["sigunguCode"] = sigungu_code

        try:
            response = httpx.get(url, params=params, timeout=self.timeout)

            if response.status_code != 200:
                logger.error(f"Tour API Error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                logger.error(f"URL: {url}")
                logger.error(f"Params: {params}")
                return []

            data = response.json()

            # 응답 구조: response.body.items.item
            response_body = data.get("response", {}).get("body", {})
            items = response_body.get("items", {})

            # items가 빈 경우 처리
            if not items:
                return []

            item_list = items.get("item", [])

            # 단일 아이템인 경우 리스트로 변환
            if isinstance(item_list, dict):
                item_list = [item_list]

            logger.info(
                f"Tour API: area={area_code}, contentType={content_type_id}, "
                f"page={page}, results={len(item_list)}"
            )

            return item_list

        except Exception as e:
            logger.error(f"Tour API Request Error: {e}")
            return []

    def get_common_info(self, content_id: str, content_type_id: str) -> Optional[Dict]:
        """
        공통정보 조회 (상세 정보)

        Args:
            content_id: 컨텐츠 ID
            content_type_id: 컨텐츠 타입 ID

        Returns:
            상세 정보 딕셔너리 또는 None
        """
        url = f"{self.BASE_URL}/detailCommon1"

        params = {
            "serviceKey": self.SERVICE_KEY,
            "MobileOS": "ETC",
            "MobileApp": "MateTrip",
            "_type": "json",
            "contentId": content_id,
            "contentTypeId": content_type_id,
            "defaultYN": "Y",  # 기본정보 조회
            "firstImageYN": "Y",  # 대표이미지 조회
            "areacodeYN": "Y",  # 지역코드 조회
            "addrinfoYN": "Y",  # 주소 조회
            "mapinfoYN": "Y",  # 좌표 조회
            "overviewYN": "Y",  # 개요 조회
        }

        try:
            response = httpx.get(url, params=params, timeout=self.timeout)

            if response.status_code != 200:
                logger.error(f"Tour API Detail Error: {response.status_code}")
                return None

            data = response.json()
            response_body = data.get("response", {}).get("body", {})
            items = response_body.get("items", {})

            if not items:
                return None

            item_list = items.get("item", [])

            # 단일 아이템인 경우
            if isinstance(item_list, dict):
                return item_list

            # 리스트인 경우 첫 번째 반환
            if item_list:
                return item_list[0]

            return None

        except Exception as e:
            logger.error(f"Tour API Detail Request Error: {e}")
            return None

    def get_image_list(self, content_id: str, content_type_id: str) -> List[str]:
        """
        이미지 목록 조회

        Args:
            content_id: 컨텐츠 ID
            content_type_id: 컨텐츠 타입 ID

        Returns:
            이미지 URL 리스트
        """
        url = f"{self.BASE_URL}/detailImage1"

        params = {
            "serviceKey": self.SERVICE_KEY,
            "MobileOS": "ETC",
            "MobileApp": "MateTrip",
            "_type": "json",
            "contentId": content_id,
            "imageYN": "Y",
            "subImageYN": "Y",  # 추가이미지도 조회
        }

        try:
            response = httpx.get(url, params=params, timeout=self.timeout)

            if response.status_code != 200:
                return []

            data = response.json()
            response_body = data.get("response", {}).get("body", {})
            items = response_body.get("items", {})

            if not items:
                return []

            item_list = items.get("item", [])

            # 단일 아이템인 경우 리스트로 변환
            if isinstance(item_list, dict):
                item_list = [item_list]

            # originimgurl 추출
            image_urls = [
                cast(str, origin)
                for origin in (item.get("originimgurl") for item in item_list)
                if isinstance(origin, str) and origin
            ]

            return image_urls

        except Exception as e:
            logger.error(f"Tour API Image Request Error: {e}")
            return []

    def convert_to_place_data(self, tour_data: Dict) -> Dict:
        """
        Tour API 응답을 Place 모델 형식으로 변환

        Args:
            tour_data: Tour API 응답 데이터

        Returns:
            Place 모델 형식 딕셔너리
        """
        # 기본 정보
        title = tour_data.get("title", "").strip()
        addr1 = tour_data.get("addr1", "").strip()
        addr2 = tour_data.get("addr2", "").strip()
        address = f"{addr1} {addr2}".strip() if addr2 else addr1

        # 좌표 정보 (mapx: 경도, mapy: 위도)
        mapx = tour_data.get("mapx", "")
        mapy = tour_data.get("mapy", "")

        # 좌표가 문자열인 경우 float으로 변환
        try:
            longitude = float(mapx) if mapx else 0.0
            latitude = float(mapy) if mapy else 0.0
        except (ValueError, TypeError):
            longitude = 0.0
            latitude = 0.0

        # 카테고리 정보 (대분류만 사용)
        cat1 = tour_data.get("cat1")

        # Tour API 코드는 a052 처럼 소문자/혼합형으로 내려오기도 하므로
        # 항상 cat1 단위의 대분류 한글 명칭으로 정규화한다.
        primary_category = TourCategoryMapper.get_primary_category_name(cat1)
        categories: List[str] = [primary_category] if primary_category else []

        # 이미지 URL
        firstimage = tour_data.get("firstimage", "")  # 대표이미지 원본
        firstimage2 = tour_data.get("firstimage2", "")  # 대표이미지 썸네일

        image_url = firstimage if firstimage else firstimage2

        return {
            "title": title,
            "address": address,
            "longitude": longitude,
            "latitude": latitude,
            "categories": categories,
            "image_url": image_url if image_url else None,
        }

    def search_all_pages(
        self,
        area_code: str,
        content_type_id: Optional[str] = None,
        sigungu_code: Optional[str] = None,
        max_pages: int = 10,
    ) -> List[Dict]:
        """
        모든 페이지를 순회하며 데이터 수집

        Args:
            area_code: 지역코드
            content_type_id: 컨텐츠 타입
            sigungu_code: 시군구코드
            max_pages: 최대 페이지 수

        Returns:
            전체 결과 리스트
        """
        all_items = []
        page = 1

        while page <= max_pages:
            items = self.search_area_based_list(
                area_code=area_code,
                content_type_id=content_type_id,
                sigungu_code=sigungu_code,
                page=page,
                num_of_rows=100,
            )

            if not items:
                # 더 이상 결과가 없으면 종료
                break

            all_items.extend(items)
            page += 1

        logger.info(
            f"Tour API 전체 수집: area={area_code}, contentType={content_type_id}, "
            f"total={len(all_items)}"
        )

        return all_items
