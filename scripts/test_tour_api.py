"""Tour API 테스트 스크립트"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.service.crawling.tour_api_service import TourAPIService


def test_tour_api():
    """Tour API 기본 동작 테스트"""
    print("=" * 80)
    print("Tour API 테스트 시작")
    print("=" * 80)

    service = TourAPIService()

    # 1. 서울 관광지 검색
    print("\n[테스트 1] 서울 관광지 검색 (contentTypeId=12)")
    seoul_tourism = service.search_area_based_list(
        area_code="1",  # 서울
        content_type_id="12",  # 관광지
        page=1,
        num_of_rows=5,  # 테스트용으로 5개만
    )

    if seoul_tourism:
        print(f"✓ {len(seoul_tourism)}개 결과 조회 성공")
        for i, item in enumerate(seoul_tourism, 1):
            print(f"  {i}. {item.get('title')} - {item.get('addr1', 'N/A')}")
    else:
        print("✗ 검색 실패")

    # 2. 제주 관광지 검색
    print("\n[테스트 2] 제주 관광지 검색 (contentTypeId=12)")
    jeju_tourism = service.search_area_based_list(
        area_code="39",  # 제주
        content_type_id="12",  # 관광지
        page=1,
        num_of_rows=5,
    )

    if jeju_tourism:
        print(f"✓ {len(jeju_tourism)}개 결과 조회 성공")
        for i, item in enumerate(jeju_tourism, 1):
            title = item.get("title", "N/A")
            addr = item.get("addr1", "N/A")
            content_id = item.get("contentid", "N/A")
            print(f"  {i}. {title} - {addr} (ID: {content_id})")
    else:
        print("✗ 검색 실패")

    # 3. Place 데이터 변환 테스트
    if jeju_tourism:
        print("\n[테스트 3] Place 데이터 변환")
        first_item = jeju_tourism[0]
        place_data = service.convert_to_place_data(first_item)

        print("✓ 변환 성공:")
        print(f"  - title: {place_data['title']}")
        print(f"  - address: {place_data['address']}")
        print(f"  - longitude: {place_data['longitude']}")
        print(f"  - latitude: {place_data['latitude']}")
        print(f"  - categories: {place_data['categories']}")
        print(f"  - image_url: {place_data.get('image_url', 'N/A')}")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    test_tour_api()
