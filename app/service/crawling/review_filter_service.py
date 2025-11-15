"""
리뷰 필터링 서비스 - 광고성 글 제거
"""

import logging
import re
import json
from typing import List
import boto3
from app.common.config import bedrockConfig
from app.schemas.review import ReviewContentDto

logger = logging.getLogger(__name__)


class ReviewFilterService:
    """리뷰를 필터링하여 광고성 글을 제거하는 서비스"""

    def __init__(self):
        # AWS Bedrock Claude 사용
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=bedrockConfig.AWS_REGION,
            aws_access_key_id=bedrockConfig.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=bedrockConfig.AWS_SECRET_ACCESS_KEY,
        )
        self.model_id = bedrockConfig.BEDROCK_LLM_MODEL_ID

        # 광고성 키워드 (부동산, 분양, 임대 등)
        self.spam_keywords = [
            # 부동산 관련
            "임대",
            "매물",
            "분양",
            "투자",
            "수익",
            "전세",
            "월세",
            "평형",
            "실평수",
            "권리금",
            "중개",
            "부동산",
            "공실",
            "입주",
            "계약",
            "프리미엄",
            "매매",
            "보증금",
            # 일반 광고 관련
            "협찬",
            "제공받",
            "제공 받",
            "홍보",
            "체험단",
            "서포터즈",
            "할인코드",
            "쿠폰코드",
            "프로모션",
            "이벤트참여",
            "무료제공",
            "증정",
            "리뷰이벤트",
            "대가없이",
        ]

        # 명확한 광고성 URL 패턴 (하나라도 있으면 차단)
        self.suspicious_url_patterns = [
            r'bit\.ly',  # 단축 URL
            r'goo\.gl',  # 구글 단축 URL
            r'카톡[\s:]+',  # 카톡 ID
            r'카카오톡[\s:]+',
            r'텔레그램',
            r'오픈채팅',
            r'카톡\s*ID',
            r'문의.*010',  # 문의 전화번호
            r'연락.*010',
        ]

        # 일반 URL 패턴 (3개 이상 있으면 차단)
        self.general_url_patterns = [
            r'https?://',  # http://, https://
            r'www\.',  # www.
        ]

    def keyword_filter(self, content: str) -> bool:
        """
        키워드 기반 1차 필터링 (빠르고 무료)

        Args:
            content: 리뷰 내용

        Returns:
            True: 정상 리뷰, False: 광고성 글
        """
        # 1. 너무 짧은 리뷰 (10자 미만)
        if len(content.strip()) < 10:
            logger.info("[키워드 필터링] 너무 짧은 리뷰")
            return False

        # 2. 명확한 광고성 URL 패턴 체크 (하나라도 있으면 차단)
        for pattern in self.suspicious_url_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.info(f"[키워드 필터링] 광고성 URL/연락처 감지: {pattern}")
                return False

        # 3. 일반 URL이 너무 많으면 차단 (3개 이상)
        url_count = 0
        for pattern in self.general_url_patterns:
            url_count += len(re.findall(pattern, content, re.IGNORECASE))

        if url_count >= 3:
            logger.info(f"[키워드 필터링] 과도한 URL 감지 ({url_count}개)")
            return False

        # 4. 과도한 특수문자/이모티콘 (전체의 30% 이상)
        special_chars = len(re.findall(r'[^\w\s가-힣]', content))
        if len(content) > 0 and special_chars / len(content) > 0.3:
            logger.info(f"[키워드 필터링] 과도한 특수문자 ({special_chars}/{len(content)})")
            return False

        # 5. 광고성 키워드 개수 카운트
        spam_count = 0
        for keyword in self.spam_keywords:
            if keyword in content:
                spam_count += 1

        # 3개 이상의 광고성 키워드가 있으면 광고로 판단
        if spam_count >= 3:
            logger.info(f"[키워드 필터링] 광고성 글 감지 (키워드 {spam_count}개)")
            return False

        # 6. 특정 광고성 키워드가 단독으로 있어도 차단
        high_spam_keywords = ["협찬", "제공받", "체험단", "서포터즈", "할인코드", "쿠폰코드"]
        for keyword in high_spam_keywords:
            if keyword in content:
                logger.info(f"[키워드 필터링] 광고성 키워드 감지: {keyword}")
                return False

        # 7. "임대" 또는 "매물"이 5회 이상 나오면 광고로 판단
        if content.count("임대") >= 5 or content.count("매물") >= 5:
            logger.info("[키워드 필터링] 광고성 글 감지 (특정 키워드 과다)")
            return False

        return True

    def ai_filter(self, content: str, place_title: str) -> bool:
        """
        Bedrock Claude 기반 2차 필터링 (정확하지만 비용 발생)

        Args:
            content: 리뷰 내용
            place_title: 장소명

        Returns:
            True: 정상 리뷰, False: 광고성 글
        """
        try:
            # 너무 긴 내용은 잘라서 전송 (비용 절약)
            truncated_content = content[:1000]

            prompt = f"""다음 글이 "{place_title}"에 대한 실제 방문 리뷰인지, 광고성 글인지 판단해주세요.

글 내용:
{truncated_content}

판단 기준:
- 실제 방문 리뷰: 음식/서비스/분위기 등 실제 경험에 대한 내용
- 광고성 글: 부동산 매물/임대, 투자, 분양 등 상업적 광고

JSON 형식으로만 답변해주세요:
{{"is_review": true, "reason": "판단 이유"}}"""

            # Bedrock Claude API 호출
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
            })

            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            # 응답 파싱
            response_body = json.loads(response["body"].read())
            content_list = response_body.get("content", [])

            if not content_list:
                logger.warning("[AI 필터링] 응답이 비어 있습니다")
                return True  # 에러 시 일단 통과

            result_text = content_list[0].get("text", "")
            parsed = json.loads(result_text)
            is_review = parsed.get("is_review", True)
            reason = parsed.get("reason", "")

            if not is_review:
                logger.info(f"[AI 필터링] 광고성 글 감지: {reason}")

            return is_review

        except Exception as e:
            logger.error(f"[AI 필터링] 오류 발생: {e}")
            return True  # 에러 시 일단 통과

    def filter_reviews(
        self,
        reviews: List[ReviewContentDto],
        place_title: str,
        use_ai: bool = False,
    ) -> List[ReviewContentDto]:
        """
        리뷰 리스트를 필터링하여 광고성 글 제거

        Args:
            reviews: 리뷰 DTO 리스트
            place_title: 장소명
            use_ai: AI 필터링 사용 여부 (비용 발생)

        Returns:
            필터링된 리뷰 DTO 리스트
        """
        filtered_reviews: List[ReviewContentDto] = []
        spam_count = 0

        logger.info("\n" + "=" * 80)
        logger.info(f"[리뷰 필터링 시작] 전체 {len(reviews)}개")
        logger.info("=" * 80)

        for idx, review in enumerate(reviews, 1):
            url = review.source_url
            content = review.content

            # 1차: 키워드 필터링
            if not self.keyword_filter(content):
                spam_count += 1
                logger.info(f"  [{idx}/{len(reviews)}] 광고 제거 (키워드)")
                continue

            # 2차: AI 필터링 (옵션)
            if use_ai:
                if not self.ai_filter(content, place_title):
                    spam_count += 1
                    logger.info(f"  [{idx}/{len(reviews)}] 광고 제거 (AI)")
                    continue

            filtered_reviews.append(review)
            logger.info(f"  [{idx}/{len(reviews)}] 정상 리뷰")

        logger.info("\n" + "=" * 80)
        logger.info(f"[리뷰 필터링 완료]")
        logger.info(f"- 전체: {len(reviews)}개")
        logger.info(f"- 정상: {len(filtered_reviews)}개")
        logger.info(f"- 광고: {spam_count}개")
        logger.info("=" * 80 + "\n")

        return filtered_reviews
