"""
리뷰 추출 기능 테스트 스크립트

실행 방법:
    uv run python scripts/test_review_extraction.py
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.service.bedrock_llm_service import BedrockLLMService


def test_review_extraction():
    """리뷰 추출 기능 테스트"""

    llm_service = BedrockLLMService()

    # 테스트 케이스 1: 관광 정보 사이트 (리뷰 아님)
    tourism_site_content = """
    서울특별시 강동구 2025 서울국제드론레이싱월드컵 스포츠경기

    서울국제드론레이싱월드컵은 전 세계 10개국 대표 선수들이 참가해,
    서울 상공을 무대로 빠르고 정밀한 드론 조종 실력을 겨루는 국제 대회이다.

    행사장소: 광나루 한강 드론공원
    행사시작일: 2025년 10월 01일
    행사종료일: 2025년 10월 01일
    공연시간: 10:00~16:00
    주최자정보: 서울특별시
    이용요금: 무료

    주변 볼거리
    - 광나루자전거공원
    - 허브체험공원
    - 광나루한강공원
    """

    # 테스트 케이스 2: 블로그 리뷰 (리뷰임)
    blog_review_content = """
    경복궁 나들이 후기

    안녕하세요! 오늘은 가족들과 함께 경복궁에 다녀온 이야기를 해볼까 합니다.

    주말이라 사람이 많을 것 같아 일찍 출발했는데 역시나 많은 관광객들이
    벌써 도착해 있더라고요. 한복을 입으면 무료 입장이라서 근처 대여점에서
    한복을 빌려 입고 입장했습니다.

    경복궁은 정말 웅장하고 아름다웠어요. 특히 경회루 연못에 비친 건물이
    정말 멋있었습니다. 사진도 많이 찍었는데 다 인스타에 올릴 예정이에요 ㅎㅎ

    날씨도 좋고 산책하기 딱 좋았어요. 다음에는 창덕궁도 가보려고 합니다!
    추천합니다~
    """

    # 테스트 케이스 3: 메뉴/네비게이션만 있는 페이지 (리뷰 아님)
    navigation_content = """
    홈 > 여행 > 관광지 > 서울

    * 이색체험
    * 전국 오일장
    * 트레킹 코스
    * 미술관
    * 전시회
    * 관광축제
    * 맛집
    * 카테고리 전체보기

    서울 추천 관광지
    - 경복궁
    - 북촌한옥마을
    - 인사동
    - 남산타워
    """

    print("=" * 80)
    print("리뷰 추출 기능 테스트")
    print("=" * 80)

    # 테스트 1
    print("\n[테스트 1] 관광 정보 사이트")
    print("-" * 80)
    result1 = llm_service.extract_review_content(
        tourism_site_content, "서울국제드론레이싱월드컵"
    )
    print(f"결과: {'리뷰로 판단됨' if result1 else '리뷰 아님 (정답!)'}")
    if result1:
        print(f"추출된 내용: {result1[:100]}...")

    # 테스트 2
    print("\n[테스트 2] 블로그 리뷰")
    print("-" * 80)
    result2 = llm_service.extract_review_content(blog_review_content, "경복궁")
    print(f"결과: {'리뷰로 판단됨 (정답!)' if result2 else '리뷰 아님'}")
    if result2:
        print(f"추출된 내용 길이: {len(result2)}자")
        print(f"추출된 내용 미리보기: {result2[:150]}...")

    # 테스트 3
    print("\n[테스트 3] 네비게이션/메뉴만 있는 페이지")
    print("-" * 80)
    result3 = llm_service.extract_review_content(navigation_content, "서울 관광지")
    print(f"결과: {'리뷰로 판단됨' if result3 else '리뷰 아님 (정답!)'}")
    if result3:
        print(f"추출된 내용: {result3[:100]}...")

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    test_review_extraction()
