"""
한국관광공사 Tour API 카테고리 코드 체계 (대분류 cat1 전용)

Tour API는 cat1/cat2/cat3 3단계 구조를 제공하지만, 서비스에서는
대분류(cat1)만 사용해 단순화한다.
"""

from enum import Enum
from typing import Dict, Optional


class TourCat1(str, Enum):
    """Tour API 대분류 (cat1)"""

    NATURE = "A01"  # 자연
    CULTURE = "A02"  # 인문(문화/예술/역사)
    LEISURE = "A03"  # 레포츠
    SHOPPING = "A04"  # 쇼핑
    FOOD = "A05"  # 음식
    ACCOMMODATION = "B02"  # 숙박
    COURSE = "C01"  # 추천코스

    @property
    def korean_name(self) -> str:
        return TourCategoryMapper.CAT1_NAMES.get(self.value, self.value)


class TourCategoryMapper:
    """Tour API cat1 코드 정규화/명칭 조회 헬퍼"""

    CAT1_NAMES: Dict[str, str] = {
        "A01": "자연",
        "A02": "인문(문화/예술/역사)",
        "A03": "레포츠",
        "A04": "쇼핑",
        "A05": "음식",
        "B02": "숙박",
        "C01": "추천코스",
    }

    @classmethod
    def normalize_cat1_code(cls, code: Optional[str]) -> Optional[str]:
        """
        API에서 내려오는 cat1 코드(혹은 실수로 들어온 cat2/cat3 코드)를
        cat1 형식(A01, B02 등)으로 정규화한다.
        """
        if not code:
            return None

        normalized = code.strip().upper()
        if not normalized:
            return None

        if normalized in cls.CAT1_NAMES:
            return normalized

        prefix = normalized[:3]
        return prefix if prefix in cls.CAT1_NAMES else None

    @classmethod
    def get_primary_category_name(cls, code: Optional[str]) -> Optional[str]:
        """정규화된 cat1 코드의 한글 명칭을 반환"""
        normalized = cls.normalize_cat1_code(code)
        return cls.CAT1_NAMES.get(normalized) if normalized else None
