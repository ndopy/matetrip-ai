import logging
import os
from typing import List
from sqlalchemy.orm import Session

from app.models.place import Place
from app.service.crawl_service import CrawlService
from app.service.naver_search_service import NaverSearchService
from app.models.review import PlaceReview
from app.service.review_service import ReviewService
from app.service.bedrock_llm_service import BedrockLLMService
from app.service.review_filter_service import ReviewFilterService
from app.service.place_embedding_service import PlaceEmbeddingService
from service.bedrock_embedding_service import BedrockEmbeddingService

naver_service = NaverSearchService()
crawl_service = CrawlService()
review_service = ReviewService()
review_filter_service = ReviewFilterService()

logger = logging.getLogger(__name__)


class PlaceService:

    def __init__(self) -> None:
        self.llm_service = BedrockLLMService()  # LLM 서비스
        self.embedding_service = PlaceEmbeddingService()  # Place 임베딩 서비스
        self.review_embedding_service = (
            BedrockEmbeddingService()
        )  # Review 임베딩 서비스

    async def process_place_reviews(
        self, db: Session, place: Place, force_update: bool = False
    ):
        """
        백그라운드에서 장소에 대한 리뷰를 처리하는 함수
        1. naver 검색 API로 리뷰 URL 추출
        2. Crawl4AI로 리뷰 크롤링
        3. 리뷰 저장 및 임베딩 생성
        4. 태그 및 요약 생성

        Args:
            db: 데이터베이스 세션
            place: 처리할 장소
            force_update: True면 임베딩이 있어도 강제로 재처리 (기본값: False)
        """
        try:
            # 환경 변수 체크
            env_force_update = (
                os.getenv("FORCE_UPDATE_EMBEDDINGS", "false").lower() == "true"
            )
            should_force = force_update or env_force_update

            # 이미 임베딩이 있는 장소는 건너뛰기 (force_update가 False인 경우)
            if not should_force and place.embedding is not None:
                logger.info(
                    f"⊘ {place.title} 건너뛰기 (이미 임베딩 존재, embedding dimension: {len(place.embedding)})"
                )
                return

            logger.info(f"process_place_reviews 시작 : {place.title}")

            # 1. naver검색 API로 리뷰 URL 추출
            review_urls = naver_service.search_review_urls(
                place.title, place.address, []
            )
            logger.info(f"{len(review_urls)}개의 리뷰를 찾았습니다")

            if not review_urls:
                return

            # 2. Crawl4AI로 리뷰 크롤링
            review_contents = await crawl_service.crawl_reviews_batch(review_urls)
            logger.info(f"{len(review_contents)}개의 리뷰를 크롤링 완료")

            # 3. 광고성 리뷰 필터링 (키워드 기반)
            filtered_reviews = review_filter_service.filter_reviews(
                review_contents, place.title, use_ai=False
            )

            if not filtered_reviews:
                logger.warning("필터링 후 리뷰가 없습니다.")
                return

            # 4. 리뷰 저장
            reviews: List[PlaceReview] = review_service.save_reviews(
                place.id, filtered_reviews, db
            )
            if not reviews:
                return

            db.commit()
            logger.info(f"{len(reviews)}개의 리뷰 저장 완료")

            # 5. 리뷰 임베딩 생성 (검색 정확도용 - 긍정/부정 비율 보존)
            logger.info("\n[리뷰 임베딩 생성 시작]")
            review_contents = [review.content for review in reviews]
            embeddings = self.review_embedding_service.create_embeddings_batch(
                review_contents
            )

            for idx, (review, embedding) in enumerate(zip(reviews, embeddings), 1):
                setattr(review, "embedding", embedding)
                logger.info(f"  {idx}/{len(reviews)} 리뷰 임베딩 완료")

            db.commit()
            logger.info(f"[리뷰 임베딩 생성 완료]")

            # 6. 태그 및 요약 생성 (사용자 표시용)
            logger.info("\n[태그 및 요약 생성 시작]")
            result = self.llm_service.generate_tags_and_summary(
                review_contents, place.title
            )

            # Tour API 카테고리는 이미 저장되어 있으므로 업데이트하지 않음
            place.tags = result.get("tags", [])
            place.summary = result.get("summary", "")
            db.commit()
            logger.info(f"태그: {place.tags}")
            if place.summary:
                logger.info(f"요약: {place.summary[:100]}...")
            else:
                logger.info("요약: (생성 실패)")

            # 7. 장소 임베딩 생성 (리뷰 임베딩들의 평균 - 검색 정확도용)
            logger.info(f"\n[장소 임베딩 생성 시작]")
            self.embedding_service.refresh_embedding(
                db=db,
                place_id=place.id,
            )
            logger.info(f"[장소 임베딩 생성 완료]")

            logger.info(f"\n[배치 처리 완료]")
            logger.info(f"{'*'*80}\n")

        except Exception:
            logger.error(f"장소 리뷰 처리 중 오류 발생: {place.title}", exc_info=True)
            db.rollback()
            raise
