import asyncio
import os
import random
from typing import List, Dict
from urllib.parse import urlparse, parse_qs

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode


# Crawl4AI를 사용하여 웹 페이지에서 리뷰를 크롤링하는 서비스
class CrawlService:
    # 동시 크롤링 수 제한 (메모리 사용량 제어)
    # 환경 변수로 설정 가능, 기본값: 5
    MAX_CONCURRENT_CRAWLS = int(os.getenv("MAX_CONCURRENT_CRAWLS", "5"))

    # 요청 간 최소/최대 딜레이 (초)
    # rate limiting 우회를 위한 랜덤 딜레이
    MIN_REQUEST_DELAY = float(os.getenv("MIN_REQUEST_DELAY", "0.5"))
    MAX_REQUEST_DELAY = float(os.getenv("MAX_REQUEST_DELAY", "2.0"))

    # 최대 재시도 횟수
    MAX_RETRIES = int(os.getenv("CRAWL_MAX_RETRIES", "3"))

    # User-Agent 목록 (rate limiting 우회용)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    """
    단일 URL에서 리뷰 컨텐츠를 크롤링합니다.

    Args:
        url: 크롤링할 URL

    Returns:
        추출된 텍스트 컨텐츠
    """

    async def crawl_review(self, url: str, max_retries: int | None = None) -> str:
        """
        단일 URL 크롤링 (재시도 로직 포함)

        Args:
            url: 크롤링할 URL
            max_retries: 최대 재시도 횟수 (None이면 환경 변수 사용)

        Returns:
            추출된 텍스트 컨텐츠
        """
        if max_retries is None:
            max_retries = self.MAX_RETRIES

        # 랜덤 User-Agent 선택
        user_agent = random.choice(self.USER_AGENTS)

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # 캐시 비활성화
            page_timeout=60000,
            word_count_threshold=10,  # 최소 단어 수
            exclude_external_links=True,  # 외부 링크 제외
            remove_overlay_elements=True,  # 오버레이 요소 제거
            user_agent=user_agent,  # User-Agent rotation for rate limiting bypass
        )

        for attempt in range(max_retries):
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

                        # 재시도 전 대기 (exponential backoff)
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            print(f"Retrying in {wait_time:.2f} seconds... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(wait_time)
                        else:
                            return ""

            except Exception as e:
                print(f"Error crawling {url}: {e}")

                # 재시도 전 대기 (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {wait_time:.2f} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    return ""

        return ""

    async def crawl_reviews_batch(self, urls: List[str]) -> Dict[str, str]:
        """
        여러 URL에서 리뷰를 배치로 크롤링합니다.
        동시 크롤링 수를 제한하여 메모리 사용량을 제어합니다.

        Args:
            urls: 크롤링할 URL 리스트

        Returns:
            {url: content} 형태의 딕셔너리
        """
        import logging

        logger = logging.getLogger(__name__)

        logger.info(
            f"[크롤링 시작] 총 {len(urls)}개 URL, 동시 크롤링 제한: {self.MAX_CONCURRENT_CRAWLS}"
        )

        normalized_urls = [self._normalize_url(url) for url in urls]
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_CRAWLS)

        async def crawl_with_semaphore(url: str, index: int) -> str:
            async with semaphore:
                # 요청 간 랜덤 딜레이 추가 (rate limiting 우회)
                # 첫 번째 요청은 딜레이 없음
                if index > 0:
                    delay = random.uniform(self.MIN_REQUEST_DELAY, self.MAX_REQUEST_DELAY)
                    await asyncio.sleep(delay)

                return await self.crawl_review(url)

        tasks = [crawl_with_semaphore(url, i) for i, url in enumerate(normalized_urls)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        crawled_data = {}
        success_count = 0
        fail_count = 0

        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.warning(f"크롤링 실패: {url[:50]}... - {result}")
                crawled_data[url] = ""
                fail_count += 1
            else:
                crawled_data[url] = result
                if result:  # 빈 문자열이 아닌 경우만 성공으로 카운트
                    success_count += 1
                else:
                    fail_count += 1

        logger.info(f"[크롤링 완료] 성공: {success_count}, 실패: {fail_count}")
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
        # AWS Bedrock Titan 임베딩: 최대 8192 토큰
        # 안전하게 5000자로 제한 (약 6000-7000 토큰)
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length]

        return content
