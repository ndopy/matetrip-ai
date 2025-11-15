import logging
from typing import List, Sequence
from uuid import UUID

from sqlalchemy.orm import Session
from app.models.review import PlaceReview
from app.schemas.review import ReviewContentDto, SavedReviewDto

logger = logging.getLogger(__name__)


class ReviewService:

    def __init__(self) -> None:
        pass

    def save_reviews(
        self, place_id: UUID, crawled_reviews: List[ReviewContentDto], db: Session
    ) -> List[SavedReviewDto]:
        """
        크롤링된 리뷰를 벡터 DB에 저장
        Args:
            place_id: 장소 ID
            crawled_reviews: 크롤링된 리뷰 DTO 리스트
        """

        created_reviews: List[PlaceReview] = []
        try:
            for review_input in crawled_reviews:
                content = (review_input.content or "").strip()
                if not content:
                    logger.warning(
                        "Skipping empty review content for URL: %s",
                        review_input.source_url,
                    )
                    continue

                review = PlaceReview(
                    place_id=place_id,
                    content=content,
                    source_url=review_input.source_url,
                )
                db.add(review)
                created_reviews.append(review)

            if not created_reviews:
                return []

            db.flush()  # ID 발급
            reviews = [SavedReviewDto.from_model(review) for review in created_reviews]
            db.commit()
            logger.info("Reviews saved: %d", len(reviews))
            return reviews
        except Exception as e:
            db.rollback()
            logger.error("Failed to save reviews for place_id %s: %s", place_id, str(e))
            raise

    def apply_review_embeddings(
        self,
        reviews: List[SavedReviewDto],
        embeddings: Sequence[Sequence[float]],
        db: Session,
    ) -> None:
        """생성된 임베딩을 리뷰 레코드에 반영"""

        if len(reviews) != len(embeddings):
            raise ValueError("리뷰와 임베딩 개수가 일치하지 않습니다.")

        if not reviews:
            return

        total = len(reviews)
        update_payload = []
        for idx, (review, embedding) in enumerate(zip(reviews, embeddings), 1):
            update_payload.append({"id": review.id, "embedding": embedding})
            logger.info("  %d/%d 리뷰 임베딩 완료", idx, total)

        db.bulk_update_mappings(PlaceReview.__mapper__, update_payload)
        db.commit()
        logger.info("[리뷰 임베딩 저장 완료] %d건", total)
