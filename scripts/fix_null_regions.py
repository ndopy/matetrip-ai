# fix_null_regions.py

"""
DB에 있는 region이 NULL인 places 데이터를 주소 기반으로 업데이트하는 스크립트

실행 방법:
    uv run python scripts/fix_null_regions.py
"""

import sys
import os
import re
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.place import Place
from app.enums import RegionGroupType


def get_region_from_address(address: str) -> Optional[str]:
    """주소에서 region_group을 추출합니다."""
    if not address:
        return None

    sido_raw = address.split()[0]
    # "서울시" -> "서울", "경기도" -> "경기" 등으로 정규화
    sido_normalized = re.sub(
        r"(특별시|광역시|특별자치시|특별자치도|도|시)$", "", sido_raw
    )

    region_mapping = {
        "서울": RegionGroupType.SEOUL.value,
        "경기": RegionGroupType.GYEONGGI.value,
        "인천": RegionGroupType.INCHEON.value,
        "강원": RegionGroupType.GANGWON.value,
        "부산": RegionGroupType.BUSAN.value,
        "경남": RegionGroupType.GYEONGSANG.value,
        "경북": RegionGroupType.GYEONGSANG.value,
        "대구": RegionGroupType.GYEONGSANG.value,
        "울산": RegionGroupType.GYEONGSANG.value,
        "전남": RegionGroupType.JEOLLA.value,
        "전북": RegionGroupType.JEOLLA.value,
        "세종": RegionGroupType.CHUNGCHEONG.value,
        "충남": RegionGroupType.CHUNGCHEONG.value,
        "충북": RegionGroupType.CHUNGCHEONG.value,
        "대전": RegionGroupType.CHUNGCHEONG.value,
        "제주": RegionGroupType.JEJU.value,
    }

    return region_mapping.get(sido_normalized)


def main():
    """메인 실행 함수"""
    db = SessionLocal()

    try:
        # region이 NULL인 places 조회
        null_region_places = db.query(Place).filter(Place.region.is_(None)).all()

        print(f"region이 NULL인 장소: {len(null_region_places)}개")
        print("\n업데이트 시작...\n")

        updated_count = 0
        failed_count = 0

        for place in null_region_places:
            region = get_region_from_address(place.address)

            if region:
                place.region = region
                updated_count += 1
                if updated_count % 100 == 0:
                    print(f"진행: {updated_count}개 업데이트됨...")
            else:
                failed_count += 1
                print(f"  ✗ 지역 매핑 실패: {place.title} ({place.address})")

        # 변경사항 커밋
        db.commit()

        print("\n" + "=" * 80)
        print("업데이트 완료!")
        print(f"- 성공: {updated_count}개")
        print(f"- 실패: {failed_count}개")
        print("=" * 80)

        # 업데이트 후 NULL 개수 확인
        remaining_nulls = db.query(Place).filter(Place.region.is_(None)).count()
        print(f"\n남은 NULL region: {remaining_nulls}개")

    except Exception as e:
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
