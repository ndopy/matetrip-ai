import logging
from typing import List
from openai import OpenAI
from app.common.config import openaiConfig
from app.service.naver_search_service import NaverSearchService
import json

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=openaiConfig.OPENAI_API_KEY)
        self.model = openaiConfig.OPENAI_MODEL
        self.embedding_model = openaiConfig.OPENAI_EMBEDDING_MODEL
        self.naver_search = NaverSearchService()

    def extract_review_urls(
        self, place_title: str, address: str, category: list[str] = []
    ) -> List[str]:
        """
        네이버 검색 API를 사용하여 실제 리뷰 URL들을 검색합니다.
        (이전에는 OpenAI가 URL을 생성했지만, 실제로 존재하지 않는 URL이 많았습니다)

        Args:
            place_title: 장소 이름
            address: 장소 주소
            category: 카테고리 이름

        Returns:
            실제 리뷰 URL 리스트
        """
        return self.naver_search.search_review_urls(place_title, address, category)

    def generate_categories_from_reviews(
        self, reviews: List[str], place_title: str, kakao_category: str = ""
    ) -> List[str]:
        """
        리뷰들을 분석하여 장소의 카테고리를 생성합니다.

        Args:
            reviews: 리뷰 내용 리스트
            place_title: 장소 이름
            kakao_category: 카카오에서 받아온 카테고리 (참고용)

        Returns:
            카테고리 리스트 (최대 3개)
        """
        try:
            logger.info("\n%s", "=" * 80)
            logger.info("[카테고리 생성 시작]")
            logger.info("%s", "=" * 80)
            logger.info("장소: %s", place_title)
            logger.info("리뷰 개수: %d", len(reviews))
            if kakao_category:
                logger.info("카카오 카테고리: %s", kakao_category)

            # 리뷰들을 하나의 텍스트로 결합
            combined_reviews = "\n\n".join(
                [
                    review[:500] + "..." if len(review) > 500 else review
                    for review in reviews[:10]
                ]
            )

            kakao_hint = (
                f"\n참고로 카카오맵 카테고리는 '{kakao_category}' 입니다."
                if kakao_category
                else ""
            )

            prompt = f"""다음은 "{place_title}"에 대한 실제 리뷰들입니다.
{kakao_hint}

리뷰 내용:
{combined_reviews}

이 리뷰들을 분석하여 이 장소의 카테고리를 1-3개 추출해주세요.
카테고리는 다음 중에서 선택해주세요:
- 한식, 중식, 일식, 양식, 아시안, 카페/디저트, 주점/바
- 관광명소, 문화시설, 테마파크, 자연/공원
- 쇼핑, 숙박, 액티비티, 기타

JSON 배열 형식으로만 답변해주세요. 설명은 필요없습니다.
예시: {{"카테고리": ["한식", "관광명소"]}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 리뷰를 분석해서 장소의 카테고리를 정확하게 분류하는 전문가입니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content
            if not result:
                logger.warning("카테고리 생성 결과가 비어 있습니다.")
                return []

            logger.info("\n[생성된 카테고리]")
            logger.info("%s", result)
            logger.info("%s\n", "=" * 80)

            parsed = json.loads(result)

            # 다양한 형식 처리
            if isinstance(parsed, dict):
                categories = parsed.get("categories", parsed.get("카테고리", []))
            else:
                categories = parsed

            return categories[:3]  # 최대 3개

        except Exception as e:
            logger.error("Error generating categories: %s", e, exc_info=True)
            return []

    def generate_tags_from_reviews(
        self, reviews: List[str], place_title: str
    ) -> List[str]:
        """
        리뷰들을 분석하여 장소에 대한 태그를 생성합니다.

        Args:
            reviews: 리뷰 내용 리스트
            place_title: 장소 이름

        Returns:
            태그 리스트 (최대 5개)
        """
        try:
            logger.info("\n%s", "=" * 80)
            logger.info("[태그 생성 시작]")
            logger.info("%s", "=" * 80)
            logger.info("장소: %s", place_title)
            logger.info("리뷰 개수: %d", len(reviews))

            # 리뷰들을 하나의 텍스트로 결합 (너무 길면 각 리뷰를 잘라서)
            combined_reviews = "\n\n".join(
                [
                    review[:500] + "..." if len(review) > 500 else review
                    for review in reviews[:10]
                ]
            )

            prompt = f"""다음은 "{place_title}"에 대한 실제 리뷰들입니다.

리뷰 내용:
{combined_reviews}

이 리뷰들을 분석하여 이 장소를 가장 잘 설명하는 태그 3-5개를 추출해주세요.
태그는 한글로 작성하고, 각 태그는 2-4단어 이내로 간결하게 만들어주세요.

예시: ["분위기 좋음", "맛집", "데이트 코스", "친절한 서비스"]

JSON 배열 형식으로만 답변해주세요. 설명은 필요없습니다."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 리뷰를 분석해서 장소의 특징을 추출하는 전문가입니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content
            if not result:
                logger.warning("태그 생성 결과가 비어 있습니다.")
                return []

            logger.info("\n[생성된 태그]")
            logger.info("%s", result)
            logger.info("%s\n", "=" * 80)

            parsed = json.loads(result)

            # 다양한 형식 처리
            if isinstance(parsed, dict):
                tags = parsed.get("tags", parsed.get("태그", []))
            else:
                tags = parsed

            return tags[:5]  # 최대 5개

        except Exception as e:
            logger.error("Error generating tags: %s", e, exc_info=True)
            return []

    def generate_summary_from_reviews(
        self, reviews: List[str], place_title: str
    ) -> str:
        """
        리뷰들을 분석하여 장소에 대한 요약을 생성합니다.

        Args:
            reviews: 리뷰 내용 리스트
            place_title: 장소 이름

        Returns:
            요약 텍스트 (3-4줄)
        """
        try:
            logger.info("\n%s", "=" * 80)
            logger.info("[요약 생성 시작]")
            logger.info("%s", "=" * 80)
            logger.info("장소: %s", place_title)
            logger.info("리뷰 개수: %d", len(reviews))

            # 리뷰들을 하나의 텍스트로 결합
            combined_reviews = "\n\n".join(
                [
                    review[:500] + "..." if len(review) > 500 else review
                    for review in reviews[:10]
                ]
            )

            prompt = f"""다음은 "{place_title}"에 대한 실제 리뷰들입니다.

리뷰 내용:
{combined_reviews}

이 리뷰들을 종합하여 이 장소에 대한 요약을 3-4줄로 작성해주세요.
요약은 다음을 포함해야 합니다:
1. 이 장소의 주요 특징
2. 고객들의 전반적인 평가
3. 추천 포인트 또는 주의사항

자연스러운 한글로 작성하고, 구체적이고 유용한 정보를 제공해주세요."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 리뷰를 분석해서 간결하고 유용한 요약을 작성하는 전문가입니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )

            summary = response.choices[0].message.content
            if not summary:
                logger.warning("요약 생성 결과가 비어 있습니다.")
                return ""

            logger.info("\n[생성된 요약]")
            logger.info("%s", summary)
            logger.info("%s\n", "=" * 80)

            return summary

        except Exception as e:
            logger.error("Error generating summary: %s", e, exc_info=True)
            return ""
