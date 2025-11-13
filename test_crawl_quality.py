"""
크롤링 품질 테스트 - 본문과 관련없는 데이터가 수집되는지 확인
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.service.naver_search_service import NaverSearchService
from app.service.crawl_service import CrawlService


async def test_crawl_quality():
    """크롤링 품질 테스트"""

    # 테스트할 장소
    place_title = "경복궁"
    address = "서울특별시 종로구 사직로 161"

    print("=" * 80)
    print(f"테스트 장소: {place_title}")
    print(f"주소: {address}")
    print("=" * 80)

    # 1. Naver 검색으로 리뷰 URL 가져오기
    naver_service = NaverSearchService()
    review_urls = naver_service.search_review_urls(place_title, address, [], display=3)

    print(f"\n[1단계] 검색된 URL: {len(review_urls)}개")
    for i, url in enumerate(review_urls, 1):
        print(f"  {i}. {url}")

    if not review_urls:
        print("검색 결과가 없습니다.")
        return

    # 2. 여러 URL 크롤링 테스트
    crawl_service = CrawlService()

    print(f"\n[2단계] 여러 URL 크롤링 및 품질 테스트")
    print("-" * 80)

    total_nav_keywords = 0
    total_length = 0

    for idx, url in enumerate(review_urls[:3], 1):  # 최대 3개
        print(f"\n테스트 {idx}/3: {url}")
        normalized_url = crawl_service._normalize_url(url)

        content = await crawl_service.crawl_review(normalized_url)

        if not content:
            print(f"  ❌ 크롤링 실패 (빈 내용)")
            continue

        print(f"  ✓ 길이: {len(content)}자")
        total_length += len(content)

        # 네비게이션 키워드 체크
        nav_keywords = [
            '내소식', '이웃목록', '통계', '클립만들기', '글쓰기',
            '블로그팀', '공식블로그', '마켓', '장바구니', '블로그 앱',
            '카테고리 이동', 'PC버전으로 보기', '블로그 고객센터',
            '이웃추가', '공감', '칭찬', '댓글', '취소', '닫기공유',
            '로그인', '회원가입'
        ]

        found_keywords = []
        for keyword in nav_keywords:
            if keyword in content:
                count = content.count(keyword)
                found_keywords.append(f"{keyword}({count})")
                total_nav_keywords += count

        if found_keywords:
            print(f"  ⚠️  네비게이션 키워드: {', '.join(found_keywords[:5])}")
        else:
            print(f"  ✓ 네비게이션 키워드 없음")

        # 첫 200자 미리보기
        print(f"  📝 내용 미리보기: {content[:200]}...")

    print("\n" + "=" * 80)
    print("[최종 요약]")
    print(f"- 테스트한 URL 개수: {len(review_urls[:3])}개")
    print(f"- 평균 길이: {total_length / len(review_urls[:3]):.0f}자")
    print(f"- 전체 네비게이션 키워드: {total_nav_keywords}개")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_crawl_quality())
