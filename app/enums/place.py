from enum import Enum


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
