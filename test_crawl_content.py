"""크롤링된 리뷰 내용을 확인하는 스크립트"""
import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.service.naver_search_service import NaverSearchService
from app.service.crawl_service import CrawlService

async def test_crawl():
    """경복궁 리뷰 크롤링 테스트"""

    naver_service = NaverSearchService()
    crawl_service = CrawlService()

    # 경복궁 리뷰 URL 검색
    place_title = "경복궁"
    address = "서울특별시 종로구 사직로 161 (세종로)"

    urls = naver_service.search_review_urls(place_title, address, [], display=3)  # 3개만
    print(f"Found {len(urls)} URLs")

    if not urls:
        print("No URLs found!")
        return

    # 첫 번째 URL만 크롤링
    first_url = urls[0]
    print(f"\nCrawling: {first_url}")

    results = await crawl_service.crawl_reviews_batch([first_url])

    if not results:
        print("No content crawled!")
        return

    content = results[first_url]

    print(f"\n{'='*80}")
    print("크롤링된 내용:")
    print(f"{'='*80}")
    print(f"길이: {len(content)} 자")
    print(f"{'='*80}")
    print(content[:2000])  # 처음 2000자만
    print(f"\n{'='*80}")

    # URL 패턴 분석
    import re
    https_count = len(re.findall(r'https?://', content, re.IGNORECASE))
    www_count = len(re.findall(r'www\.', content, re.IGNORECASE))

    print(f"\nURL 분석:")
    print(f"- https?:// 패턴: {https_count}개")
    print(f"- www. 패턴: {www_count}개")
    print(f"- 총 URL 수: {https_count + www_count}개")

if __name__ == "__main__":
    asyncio.run(test_crawl())
