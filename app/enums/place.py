from __future__ import annotations

from enum import Enum
from typing import Self


class RegionGroupType(str, Enum):
    """지역 그룹 타입"""

    SEOUL = "서울"
    GYEONGGI = "경기도"
    INCHEON = "인천"
    GANGWON = "강원도"
    BUSAN = "부산"
    GYEONGSANG = "경상도"
    JEOLLA = "전라도"
    CHUNGCHEONG = "충청도"
    JEJU = "제주도"

    @classmethod
    def from_input(cls, region: str | Self) -> Self:
        """
        입력 문자열을 RegionGroupType으로 변환.
        - 정확히 일치하거나
        - 값이 포함되는 경우(예: '서울특별시' -> '서울')를 허용
        """
        if isinstance(region, cls):
            return region

        if not region:
            raise ValueError("지역명이 비어 있습니다.")

        region_text = str(region).strip()
        for regionType in cls:
            if region_text == regionType.value or regionType.value in region_text:
                return regionType

        valid = ", ".join([r.value for r in cls])
        raise ValueError(f"'{region_text}' 지역을 찾을 수 없습니다. 가능 지역: {valid}")
