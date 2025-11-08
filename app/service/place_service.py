import logging
from typing import List
from fastapi import BackgroundTasks
from sqlalchemy import exists, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.coercions import expect

from app.models.place import Place
from app.schemas.place import PlaceListCreateRequest
from app.service.crawl_service import CrawlService
from app.service.naver_search_service import NaverSearchService
from models.review import PlaceReview

naver_service = NaverSearchService()
crawl_service = CrawlService()

logger = logging.getLogger(__name__)


class PlaceService:

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
            review_urls = naver_service._search_review_urls(place.title, place.address)
            logger.info(f"{len(review_urls)}개의 리뷰를 찾았습니다")

            if not review_urls:
                return

            # 2. Crawl4AI로 리뷰 크롤링
            review_contents = await crawl_service.crawl_reviews_batch(review_urls)
            logger.info(f"{len(review_contents)}개의 리뷰를 크롤링 완료")

            # 3. 리뷰 저장 및 임베딩 생성
            self._save_reviews

        except Exception as e:
            print(f"Error processing place reviews: {e}")
            db.rollback()

        pass

    def _save_reviews(
        self, id: str, crawled_reviews: dict, db: Session
    ) -> List[PlaceReview]:

        return []
