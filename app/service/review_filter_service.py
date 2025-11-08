"""
리뷰 필터링 서비스 - 광고성 글 제거
"""

import logging
import re
from typing import List, Dict
from openai import OpenAI
from app.common.config import openaiConfig

logger = logging.getLogger(__name__)


class ReviewFilterService:
    """리뷰를 필터링하여 광고성 글을 제거하는 서비스"""

    def __init__(self):
        self.client = OpenAI(api_key=openaiConfig.OPENAI_API_KEY)
        self.model = openaiConfig.OPENAI_MODEL

        # 광고성 키워드 (부동산, 분양, 임대 등)
        self.spam_keywords = [
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
        ]

    def keyword_filter(self, content: str) -> bool:
        """
        키워드 기반 1차 필터링 (빠르고 무료)

        Args:
            content: 리뷰 내용

        Returns:
            True: 정상 리뷰, False: 광고성 글
        """
        # 광고성 키워드 개수 카운트
        spam_count = 0
        for keyword in self.spam_keywords:
            if keyword in content:
                spam_count += 1

        # 3개 이상의 광고성 키워드가 있으면 광고로 판단
        if spam_count >= 3:
            logger.info(f"[키워드 필터링] 광고성 글 감지 (키워드 {spam_count}개)")
            return False

        # "임대" 또는 "매물"이 5회 이상 나오면 광고로 판단
        if content.count("임대") >= 5 or content.count("매물") >= 5:
            logger.info("[키워드 필터링] 광고성 글 감지 (특정 키워드 과다)")
            return False

        return True

    def ai_filter(self, content: str, place_title: str) -> bool:
        """
        OpenAI 기반 2차 필터링 (정확하지만 비용 발생)

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
{{"is_review": true/false, "reason": "판단 이유"}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 리뷰와 광고를 정확하게 구분하는 전문가입니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content
            if not result:
                logger.warning("[AI 필터링] 응답이 비어 있습니다")
                return True  # 에러 시 일단 통과

            import json

            parsed = json.loads(result)
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
        reviews: Dict[str, str],  # {url: content} 형식
        place_title: str,
        use_ai: bool = False,
    ) -> Dict[str, str]:
        """
        리뷰 딕셔너리를 필터링하여 광고성 글 제거

        Args:
            reviews: 리뷰 딕셔너리 {url: content, ...}
            place_title: 장소명
            use_ai: AI 필터링 사용 여부 (비용 발생)

        Returns:
            필터링된 리뷰 딕셔너리
        """
        filtered_reviews = {}
        spam_count = 0

        logger.info("\n" + "=" * 80)
        logger.info(f"[리뷰 필터링 시작] 전체 {len(reviews)}개")
        logger.info("=" * 80)

        for idx, (url, content) in enumerate(reviews.items(), 1):

            # 1차: 키워드 필터링
            if not self.keyword_filter(content):
                spam_count += 1
                logger.info(f"  [{idx}/{len(reviews)}] 광고 제거 (키워드)")
                continue

            # 2차: AI 필터링 (옵션)
            # if use_ai:
            #     if not self.ai_filter(content, place_title):
            #         spam_count += 1
            #         logger.info(f"  [{idx}/{len(reviews)}] 광고 제거 (AI)")
            #         continue

            filtered_reviews[url] = content
            logger.info(f"  [{idx}/{len(reviews)}] 정상 리뷰")

        logger.info("\n" + "=" * 80)
        logger.info(f"[리뷰 필터링 완료]")
        logger.info(f"- 전체: {len(reviews)}개")
        logger.info(f"- 정상: {len(filtered_reviews)}개")
        logger.info(f"- 광고: {spam_count}개")
        logger.info("=" * 80 + "\n")

        return filtered_reviews
