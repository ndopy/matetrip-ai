import json
import logging
from typing import List, Dict, Any
import boto3
from app.common.config import bedrockConfig

logger = logging.getLogger(__name__)


class BedrockLLMService:
    """
    AWS Bedrock Claude를 사용한 LLM 서비스
    태그 및 요약 생성에 사용
    """

    def __init__(self):
        logger.info(f"\n[AWS Bedrock LLM 서비스 초기화]")
        logger.info(f"AWS Region: {bedrockConfig.AWS_REGION}")

        # Claude 3 Haiku 사용 (빠르고 저렴)
        self.model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        logger.info(f"Model ID: {self.model_id}\n")

        # AWS Bedrock Runtime 클라이언트 생성
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=bedrockConfig.AWS_REGION,
            aws_access_key_id=bedrockConfig.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=bedrockConfig.AWS_SECRET_ACCESS_KEY,
        )
        logger.info("[AWS Bedrock LLM 서비스 초기화 완료]\n")

    def generate_tags_and_summary(
        self, reviews: List[str], place_title: str
    ) -> Dict[str, Any]:
        """
        리뷰들을 분석하여 태그와 요약을 한 번에 생성합니다. (API 호출 1회)

        Args:
            reviews: 리뷰 내용 리스트
            place_title: 장소 이름

        Returns:
            {"tags": [...], "summary": "..."}
        """
        try:
            logger.info("\n%s", "=" * 80)
            logger.info("[태그 및 요약 생성 시작]")
            logger.info("%s", "=" * 80)
            logger.info("장소: %s", place_title)
            logger.info("리뷰 개수: %d", len(reviews))

            # 리뷰들을 하나의 텍스트로 결합 (상위 10개, 각 500자 제한)
            combined_reviews = "\n\n".join(
                [
                    review[:500] + "..." if len(review) > 500 else review
                    for review in reviews[:10]
                ]
            )

            prompt = f"""다음은 "{place_title}"에 대한 실제 리뷰들입니다.

리뷰 내용:
{combined_reviews}

위 리뷰들을 분석하여 다음을 생성해주세요:

1. 태그 (3-5개): 장소의 특징을 나타내는 짧은 키워드 (각 2-4단어)
   예시: ["분위기 좋음", "맛집", "데이트 코스", "친절한 서비스"]

2. 요약 (3-4줄): 장소의 주요 특징, 고객들의 평가, 추천 포인트를 포함한 간결한 설명

다음 JSON 형식으로만 답변해주세요:
{{"tags": ["태그1", "태그2", "태그3"], "summary": "요약 내용..."}}"""

            # Claude API 호출
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
            })

            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            # 응답 파싱
            response_body = json.loads(response["body"].read())
            content = response_body.get("content", [])

            if not content:
                logger.warning("LLM 응답이 비어 있습니다.")
                return {"tags": [], "summary": ""}

            # Claude는 content[0].text에 결과 반환
            result_text = content[0].get("text", "")
            logger.info("\n[LLM 응답]")
            logger.info("%s", result_text)

            # JSON 파싱
            result = json.loads(result_text)

            tags = result.get("tags", [])[:5]  # 최대 5개
            summary = result.get("summary", "")

            logger.info("\n[생성된 태그]")
            logger.info("%s", tags)
            logger.info("\n[생성된 요약]")
            logger.info("%s", summary)
            logger.info("%s\n", "=" * 80)

            return {"tags": tags, "summary": summary}

        except Exception as e:
            logger.error("Error generating tags and summary: %s", e, exc_info=True)
            return {"tags": [], "summary": ""}

    def generate_tags_from_reviews(
        self, reviews: List[str], place_title: str
    ) -> List[str]:
        """
        OpenAI 서비스와 호환성을 위한 메서드
        실제로는 generate_tags_and_summary를 호출하고 tags만 반환
        """
        result = self.generate_tags_and_summary(reviews, place_title)
        return result.get("tags", [])

    def generate_summary_from_reviews(
        self, reviews: List[str], place_title: str
    ) -> str:
        """
        OpenAI 서비스와 호환성을 위한 메서드
        실제로는 generate_tags_and_summary를 호출하고 summary만 반환
        """
        result = self.generate_tags_and_summary(reviews, place_title)
        return result.get("summary", "")

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

다음 JSON 형식으로만 답변해주세요:
{{"categories": ["카테고리1", "카테고리2"]}}"""

            # Claude API 호출
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
            content = response_body.get("content", [])

            if not content:
                logger.warning("카테고리 생성 결과가 비어 있습니다.")
                return []

            result_text = content[0].get("text", "")
            logger.info("\n[생성된 카테고리]")
            logger.info("%s", result_text)
            logger.info("%s\n", "=" * 80)

            parsed = json.loads(result_text)
            categories = parsed.get("categories", parsed.get("카테고리", []))

            return categories[:3]  # 최대 3개

        except Exception as e:
            logger.error("Error generating categories: %s", e, exc_info=True)
            return []
