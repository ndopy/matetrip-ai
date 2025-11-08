import asyncio
from typing import List, Dict
from urllib.parse import urlparse, parse_qs

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode


# Crawl4AI를 사용하여 웹 페이지에서 리뷰를 크롤링하는 서비스
class CrawlService:
    """
    단일 URL에서 리뷰 컨텐츠를 크롤링합니다.

    Args:
        url: 크롤링할 URL

    Returns:
        추출된 텍스트 컨텐츠
    """

    async def crawl_review(self, url: str) -> str:

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # 캐시 비활성화
            page_timeout=60000,
            word_count_threshold=10,  # 최소 단어 수
            exclude_external_links=True,  # 외부 링크 제외
            remove_overlay_elements=True,  # 오버레이 요소 제거
        )

        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url, config=config)

                if result.success:  # type: ignore
                    # markdown 형태로 추출된 텍스트 반환
                    content = result.markdown.raw_markdown if result.markdown else ""  # type: ignore

                    # 텍스트 정제
                    content = self._refine_content(content)
                    return content

                else:
                    print(f"Failed to crawl {url}: {result.error_message}")  # type: ignore
                    return ""

        except Exception as e:
            print(f"Error crawling {url}: {e}")
            return ""

    async def crawl_reviews_batch(self, urls: List[str]) -> Dict[str, str]:
        """
        여러 URL에서 리뷰를 배치로 크롤링합니다.

        Args:
            urls: 크롤링할 URL 리스트

        Returns:
            {url: content} 형태의 딕셔너리
        """
        normalized_urls = [self._normalize_url(url) for url in urls]
        tasks = [self.crawl_review(url) for url in normalized_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        crawled_data = {}
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                print(f"Exception crawling {url}: {result}")
                crawled_data[url] = ""
            else:
                crawled_data[url] = result

        return crawled_data

    def _normalize_url(self, url: str) -> str:
        """크롤러가 실제 본문을 읽을 수 있도록 URL을 정규화합니다."""

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()

        if "blog.naver.com" in hostname:
            normalized = self._normalize_naver_blog_url(parsed)
            if normalized:
                return normalized

        return url

    def _normalize_naver_blog_url(self, parsed_url) -> str:
        """네이버 블로그는 본문이 iframe으로 분리되어 있어 모바일 도메인으로 변환한다."""

        path_parts = [part for part in parsed_url.path.split("/") if part]

        # https://blog.naver.com/{blogId}/{logNo} 형태
        if len(path_parts) >= 2 and path_parts[0].lower() != "postview.naver":
            blog_id, log_no = path_parts[0], path_parts[1]
            return f"https://m.blog.naver.com/{blog_id}/{log_no}"

        # https://blog.naver.com/PostView.naver?blogId=xxx&logNo=yyy 형태
        query = parse_qs(
            parsed_url.query
        )  # 쿼리 스트링을 딕셔너리 형태로 변환해주는 함수
        blog_id = query.get("blogId", [None])[0]
        log_no = query.get("logNo", [None])[0]
        if blog_id and log_no:
            return f"https://m.blog.naver.com/{blog_id}/{log_no}"

        return ""

    def _refine_content(self, content: str) -> str:
        """
        Args:
            content: 원본 컨텐츠

        Returns:
            정제된 컨텐츠
        """
        if not content:
            return ""

        # 여러 개의 공백을 하나로 축소
        content = " ".join(content.split())

        # 너무 짧은 컨텐츠는 제외
        if len(content) < 50:
            return ""

        # 최대 길이 제한 (임베딩 토큰 제한 고려)
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length]

        return content
