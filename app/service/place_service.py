import logging
import os
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.place import Place
from app.service.crawling.crawl_service import CrawlService
from app.service.crawling.naver_search_service import NaverSearchService
from app.service.review_service import ReviewService
from app.service.crawling.bedrock_llm_service import BedrockLLMService
from app.service.crawling.review_filter_service import ReviewFilterService
from app.service.place_embedding_service import PlaceEmbeddingService
from app.service.bedrock_embedding_service import BedrockEmbeddingService
from app.schemas.review import ReviewContentDto, SavedReviewDto
from app.schemas.place import (
    NearbyPlaceRequest,
    NearbyPlaceResponse,
    PopularPlaceRequest,
    PopularPlaceResponse,
)
from app.repository.place_repository import PlaceRepository

naver_service = NaverSearchService()
crawl_service = CrawlService()
review_service = ReviewService()
review_filter_service = ReviewFilterService()

logger = logging.getLogger(__name__)


class PlaceService:

    def __init__(self, db: Session) -> None:
        self.repository = PlaceRepository(db)
        self.llm_service = BedrockLLMService()  # LLM 서비스
        self.embedding_service = PlaceEmbeddingService()  # Place 임베딩 서비스
        self.review_embedding_service = (
            BedrockEmbeddingService()
        )  # Review 임베딩 서비스

    async def process_place_reviews(self, place: Place, force_update: bool = False):
        """
        백그라운드에서 장소에 대한 리뷰를 처리하는 함수
        1. naver 검색 API로 리뷰 URL 추출
        2. Crawl4AI로 리뷰 크롤링
        3. 리뷰 저장 및 임베딩 생성
        4. 태그 및 요약 생성

        Args:
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
            # 이거 나중에 수정하기 (처음 장소 수집에서만 제외)
            if not should_force and place.embedding is not None:
                logger.info(f"⊘ {place.title} 건너뛰기 (이미 임베딩 존재)")
                return

            logger.info(f"process_place_reviews 시작 : {place.title}")

            # 1. naver검색 API로 리뷰 URL 추출
            review_urls = naver_service.search_review_urls(place.title, place.address)
            logger.info(f"{len(review_urls)}개의 리뷰를 찾았습니다")

            if not review_urls:
                return

            # 2. Crawl4AI로 리뷰 크롤링
            review_contents = await crawl_service.crawl_reviews_batch(review_urls)
            logger.info(f"{len(review_contents)}개의 리뷰를 크롤링 완료")
            review_dtos = [
                ReviewContentDto(source_url=url, content=content)
                for url, content in review_contents.items()
            ]

            # 3. 광고성 리뷰 필터링 (키워드 기반)
            filtered_reviews = review_filter_service.filter_reviews(
                review_dtos, place.title, use_ai=False
            )

            if not filtered_reviews:
                logger.warning("필터링 후 리뷰가 없습니다.")
                return

            # 4. 리뷰 저장
            reviews: List[SavedReviewDto] = review_service.save_reviews(
                place.id, filtered_reviews, self.repository.session
            )
            if not reviews:
                return

            logger.info(f"{len(reviews)}개의 리뷰 저장 완료")

            # 5. 리뷰 임베딩 생성 (검색 정확도용 - 긍정/부정 비율 보존)
            logger.info("\n[리뷰 임베딩 생성 시작]")
            review_contents = [review.content for review in reviews]
            embeddings = self.review_embedding_service.create_embeddings_batch(
                review_contents
            )

            review_service.apply_review_embeddings(
                reviews, embeddings, self.repository.session
            )
            logger.info(f"[리뷰 임베딩 생성 완료]")

            # 6. 태그 및 요약 생성 (사용자 표시용)
            logger.info("\n[태그 및 요약 생성 시작]")
            result = self.llm_service.generate_tags_and_summary(
                review_contents, place.title
            )

            # Tour API 카테고리는 이미 저장되어 있으므로 업데이트하지 않음
            place.tags = result.get("tags", [])
            place.summary = result.get("summary", "")
            self.repository.commit()
            logger.info(f"태그: {place.tags}")
            summary = place.summary
            if summary:
                summary_preview = summary[:100] if len(summary) > 100 else summary
                logger.info(f"요약: {summary_preview}...")
            else:
                logger.info("요약: (생성 실패)")

            # 7. 장소 임베딩 생성 (리뷰 임베딩들의 평균 - 검색 정확도용)
            logger.info(f"\n[장소 임베딩 생성 시작]")
            self.embedding_service.refresh_embedding(
                db=self.repository.session,
                place_id=place.id,
            )
            logger.info(f"[장소 임베딩 생성 완료]")

            logger.info(f"\n[배치 처리 완료]")
            logger.info(f"{'*'*80}\n")

        except Exception:
            logger.error(f"장소 리뷰 처리 중 오류 발생: {place.title}", exc_info=True)
            self.repository.rollback()
            raise

    def find_place_by_id(self, place_id: int):
        return self.repository.find_by_id(place_id)

    def find_nearby_places(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Place]:
        """
        주변 장소를 검색합니다.

        Args:
            latitude: 위도
            longitude: 경도
            radius_km: 검색 반경 (km)
            category: 카테고리 (예: '음식', '숙박', '레포츠' 등)
            limit: 최대 결과 개수

        Returns:
            거리순으로 정렬된 장소 리스트
        """
        print("[Place Service : find_nearby_places 함수 호출]")
        return self.repository.find_nearby_places(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            category=category,
            limit=limit,
        )

    def get_nearby_place(
        self, request: NearbyPlaceRequest
    ) -> List[NearbyPlaceResponse]:
        """주변 장소 검색 결과를 DTO로 캡슐화하여 반환"""
        places = self.find_nearby_places(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km,
            category=request.category,
            limit=request.limit,
        )
        return [NearbyPlaceResponse.from_entity(place) for place in places]

    def get_popular_places_in_region(
        self, request: PopularPlaceRequest
    ) -> List[PopularPlaceResponse]:
        """
        특정 지역의 인기 장소를 검색하여 반환합니다.
        Args:
            request: 인기 장소 검색 요청 DTO
        Returns:
            인기도 순으로 정렬된 장소 응답 DTO 리스트
        Raises:
            ValueError: 유효하지 않은 지역명인 경우
        """
        # Repository를 통해 인기 장소 조회
        places_data = self.repository.find_popular_places_by_region(
            region=request.region.value,
            category=request.category,
            limit=request.limit,
        )

        # 딕셔너리 데이터를 DTO로 변환
        return [PopularPlaceResponse(**place_dict) for place_dict in places_data]
