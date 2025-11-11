import logging
from typing import List
from sqlalchemy.orm import Session

from app.models.place import Place
from app.service.crawl_service import CrawlService
from app.service.naver_search_service import NaverSearchService
from app.models.review import PlaceReview
from app.service.local_embedding_service import BedrockEmbeddingService
from app.service.review_service import ReviewService
from app.service.openai_service import OpenAIService
from app.service.review_filter_service import ReviewFilterService
from app.service.place_embedding_service import PlaceEmbeddingService

naver_service = NaverSearchService()
crawl_service = CrawlService()
review_service = ReviewService()
review_filter_service = ReviewFilterService()

logger = logging.getLogger(__name__)


class PlaceService:

    def __init__(self) -> None:
        self.local_embedding_service = BedrockEmbeddingService()
        self.openai_service = OpenAIService()
        self.embedding_service = PlaceEmbeddingService()  # 🆕 임베딩 서비스 추가

    async def process_place_reviews(self, db: Session, place: Place):
        """
        백그라운드에서 장소에 대한 리뷰를 처리하는 함수
        1. naver 검색 API로 리뷰 URL 추출
        2. Crawl4AI로 리뷰 크롤링
        3. 리뷰 저장 및 임베딩 생성
        4. 태그 및 요약 생성
        """
        try:
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
                review_contents, place.title, use_ai=False  # AI 필터링은 비용 발생
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

            # 5. 임베딩 생성
            texts = [str(review.content) for review in reviews]
            embeddings = self.local_embedding_service.create_embeddings_batch(texts)

            for idx, (review, embedding) in enumerate(zip(reviews, embeddings), 1):
                setattr(review, "embedding", embedding)
                logger.info(f"{idx}번째 리뷰 임베딩 생성 완료")

            db.commit()

            # 6. 장소 임베딩 재계산
            logger.info(f"\n[장소 임베딩 업데이트 시작]")
            self.embedding_service.refresh_embedding(
                db=db,
                place_id=place.id,
            )
            logger.info(f"[장소 임베딩 업데이트 완료]")

            logger.info(f"\n[배치 처리 완료]")
            logger.info(f"{'*'*80}\n")

            # 7. 태그 생성
            review_contents = [review.content for review in reviews]
            tags: List[str] = self.openai_service.generate_tags_from_reviews(
                review_contents, place.title
            )

            # 8. 요약 생성
            summary = self.openai_service.generate_summary_from_reviews(
                review_contents, place.title
            )

            # Tour API 카테고리는 이미 저장되어 있으므로 업데이트하지 않음
            place.tags = tags
            place.summary = summary

        except Exception:
            logger.error(f"장소 리뷰 처리 중 오류 발생: {place.title}", exc_info=True)
            db.rollback()
            raise
