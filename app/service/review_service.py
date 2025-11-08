import logging
from typing import Dict, List
from uuid import UUID

from sqlalchemy.orm import Session
from app.models.review import PlaceReview

logger = logging.getLogger(__name__)


class ReviewService:

    def __init__(self) -> None:
        pass

    def save_reviews(
        self, place_id: UUID, crawled_reviews: Dict, db: Session
    ) -> List[PlaceReview]:
        """
        크롤링된 리뷰를 벡터 DB에 저장
        Args:
            place_id: 장소 ID
            crawled_reviews: 크롤링된 리뷰 딕셔너리 {url: content}
        """

        reviews = []
        for url, content in crawled_reviews.items():
            review = PlaceReview(
                place_id=place_id,
                content=content,
                source_url=url,
            )
            db.add(review)
            reviews.append(review)

        if len(reviews) <= 0:
            return []

        db.commit()
        logger.info("Reviews saved: %d", len(reviews))

        # todo : dto로
        return reviews
