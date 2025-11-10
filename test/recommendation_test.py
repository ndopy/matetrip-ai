# tests/service/test_recommendation_service.py
import logging
from unittest.mock import MagicMock

from app.service.recommendation_service import RecommendationService
from app.schemas.recommendation import PlaceRecommendation

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_recommend_by_user_embedding_returns_dtos():
    # given: 가짜 DB 세션과 result rows
    db = MagicMock()

    fake_rows = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "title": "밤도깨비 포장마차",
            "address": "서울시 마포구",
            "categories": ["food"],
            "tags": ["late-night"],
            "summary": "맛있음",
            "image_url": None,
            "longitude": 127.0,
            "latitude": 37.0,
            "review_count": 5,
            "similarity": 0.91,
        }
    ]

    result_proxy = MagicMock()
    result_proxy.mappings.return_value.all.return_value = fake_rows
    db.execute.return_value = result_proxy

    service = RecommendationService(db=db)

    # when
    recommendations = service.recommend_places_by_user_embedding(
        user_embedding=[0.1, 0.2, 0.3],
        limit=5,
    )

    logger.info(
        "테스트 추천 결과: %s",
        [rec.model_dump() for rec in recommendations],
    )

    # then
    assert len(recommendations) == 1
    assert isinstance(recommendations[0], PlaceRecommendation)
    assert recommendations[0].title == "밤도깨비 포장마차"
    db.execute.assert_called_once()  # 쿼리가 수행됐는지 확인


if __name__ == "__main__":
    test_recommend_by_user_embedding_returns_dtos()
