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
    MAX_CONCURRENT_CRAWLS = max(1, int(os.getenv("MAX_CONCURRENT_CRAWLS", "5")))

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
            page_timeout=60000,  # 60초 (원래 설정)
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
                            wait_time = (2**attempt) + random.uniform(0, 1)
                            print(
                                f"Retrying in {wait_time:.2f} seconds... (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            return ""

            except Exception as e:
                print(f"Error crawling {url}: {e}")

                # 재시도 전 대기 (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    print(
                        f"Retrying in {wait_time:.2f} seconds... (attempt {attempt + 1}/{max_retries})"
                    )
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
                    delay = random.uniform(
                        self.MIN_REQUEST_DELAY, self.MAX_REQUEST_DELAY
                    )
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
        크롤링된 컨텐츠를 정제합니다.
        - 네비게이션, 메뉴, 헤더, 푸터 등 불필요한 부분 제거
        - 본문만 추출

        Args:
            content: 원본 컨텐츠

        Returns:
            정제된 컨텐츠
        """
        if not content:
            return ""

        import re

        # 0. 네이버 블로그 특화: 본문 시작점 찾기
        # 네이버 블로그는 네비게이션이 앞쪽에 많이 포함되므로 본문 시작점을 찾습니다.
        content = self._extract_naver_blog_content(content)

        # 1. 이미지 마크다운 제거 (링크 제거보다 먼저 수행)
        # ![alt](URL) -> 제거
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
        # 남은 ! 기호 제거 (이미지 마크다운 잔여물)
        content = re.sub(r"!\s*", "", content)

        # 2. 모든 마크다운 링크를 텍스트만 남기고 제거
        # [텍스트](URL) -> 텍스트
        content = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", content)

        # 3. 빈 링크 제거 (텍스트 없는 링크)
        # [](URL) -> 제거
        content = re.sub(r"\[\]\(.*?\)", "", content)

        # 4. 마크다운 헤더 기호 제거
        # # 제목, ## 제목 -> 제목
        content = re.sub(r"#+\s*", "", content)

        # 5. 마크다운 강조 기호 제거
        # **굵게**, *기울임* -> 굵게, 기울임
        content = re.sub(r"\*\*", "", content)
        content = re.sub(r"\*", "", content)
        content = re.sub(r"__", "", content)
        content = re.sub(r"_", "", content)

        # 6. 네비게이션 관련 텍스트 블록 제거
        nav_patterns = [
            r"로그인이 필요합니다\..*?검색",  # 네이버 블로그 상단 메뉴
            r"MY메뉴 열기.*?본문 바로가기",  # MY메뉴 블록
            r"본문 기타 기능.*?신고하기",  # 본문 기타 기능 블록
            r"이웃추가톡톡.*?이웃추가하고",  # 이웃추가 블록
            r"닫기\s*카테고리.*?닫기",  # 카테고리 블록
            r"공감\s*\d+\s*칭찬.*?슬픔\s*\d+",  # 공감 버튼 블록 (반복 제거)
        ]

        for pattern in nav_patterns:
            content = re.sub(pattern, "", content, flags=re.DOTALL)

        # 7. 네비게이션 키워드가 포함된 짧은 라인 제거
        lines = content.split("\n")
        filtered_lines = []
        nav_keywords = [
            "내소식",
            "이웃목록",
            "통계",
            "클립만들기",
            "글쓰기",
            "My Menu",
            "블로그팀",
            "공식블로그",
            "마켓",
            "장바구니",
            "블로그 앱",
            "카테고리 이동",
            "PC버전으로 보기",
            "블로그 고객센터",
            "이웃추가",
            "공감",
            "칭찬",
            "댓글",
            "취소",
            "닫기공유",
        ]

        for line in lines:
            line = line.strip()
            # 짧은 라인(<20자)에 네비게이션 키워드가 있으면 제거
            if len(line) < 20 and any(kw in line for kw in nav_keywords):
                continue
            filtered_lines.append(line)

        content = "\n".join(filtered_lines)

        # 8. 연속된 줄바꿈을 하나로
        content = re.sub(r"\n\s*\n+", "\n\n", content)

        # 9. 여러 개의 공백을 하나로 축소
        content = " ".join(content.split())

        # 10. 너무 짧은 컨텐츠는 제외
        if len(content) < 50:
            return ""

        # 11. 최대 길이 제한 (임베딩 토큰 제한 고려)
        # AWS Bedrock Titan 임베딩: 최대 8192 토큰
        # 안전하게 5000자로 제한 (약 6000-7000 토큰)
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length]

        return content

    def _extract_naver_blog_content(self, content: str) -> str:
        """
        네이버 블로그 컨텐츠에서 본문 부분만 추출합니다.
        네비게이션/메뉴가 많이 포함되므로 본문 시작점을 찾아 그 이전 부분을 제거합니다.

        Args:
            content: 원본 컨텐츠

        Returns:
            본문만 추출된 컨텐츠
        """
        import re

        # 네이버 블로그 본문 시작 패턴들
        # 이 패턴들이 나오면 그 이후부터 본문으로 간주
        content_start_patterns = [
            r"> 매장정보",  # 맛집 리뷰의 매장정보 섹션
            r"> 외관",  # 맛집 리뷰의 외관 섹션
            r"> 내부",  # 맛집 리뷰의 내부 섹션
            r"📍\s*위치",  # 위치 정보
            r"📍\s*주소",  # 주소 정보
            r"⏰\s*영업시간",  # 영업시간
        ]

        # 패턴을 찾아서 가장 빨리 나오는 위치부터 본문으로 간주
        earliest_pos = len(content)

        for pattern in content_start_patterns:
            match = re.search(pattern, content)
            if match and match.start() < earliest_pos:
                earliest_pos = match.start()

        # 본문 시작점을 찾았으면 그 이후만 반환
        if earliest_pos < len(content):
            content = content[earliest_pos:]

        # 블로그 하단의 태그/해시태그 섹션 제거
        # "맛집" 키워드가 여러 번 나오는 태그 섹션 찾기
        # 예: "서울여행 경복궁맛집 경복궁밥집 광화문맛집..."

        # 1. "맛집"이 3회 이상 나오는 구간을 태그 섹션으로 간주하고 제거
        # 문장 끝(.)이나 감탄사(!) 이후에 "맛집"이 반복되면 그 이후 제거
        split_markers = [
            r"\.\s*​",  # 마침표 + zero-width space
            r"\.\s+[가-힣]+맛집",  # 마침표 + 맛집 키워드
            r"이에요\.\s*​",  # "이에요." + zero-width space
        ]

        for marker in split_markers:
            parts = re.split(marker, content, maxsplit=1)
            if len(parts) > 1:
                # 분리된 뒷부분에 "맛집"이 3개 이상 있으면 태그 섹션으로 간주
                if parts[1].count("맛집") >= 3:
                    content = parts[0]
                    break

        # 2. 마지막 문단이 태그 섹션인지 확인
        # "맛집", "데이트", "코스" 등의 키워드가 밀집된 경우
        lines = content.split("\n")
        if lines:
            last_line = lines[-1].strip()
            # 태그 키워드 카운트
            tag_keywords = ["맛집", "데이트", "코스", "여행", "근처", "추천"]
            keyword_count = sum(last_line.count(kw) for kw in tag_keywords)

            # 마지막 라인에 태그 키워드가 5개 이상 또는
            # 단어가 15개 이상이고 평균 단어 길이가 짧으면 태그로 간주
            words = last_line.split()
            if keyword_count >= 5 or (
                len(words) > 15 and sum(len(w) for w in words) / len(words) < 7
            ):
                lines = lines[:-1]
                content = "\n".join(lines)

        # 3. "새글을 받아보세요", "닫기" 등 블로그 하단 요소 제거
        footer_patterns = [
            r"\s*새글을 받아보세요.*?$",
            r"\s*닫기\s*$",
        ]
        for pattern in footer_patterns:
            content = re.sub(pattern, "", content, flags=re.DOTALL)

        return content
