"""
장소 추천 서비스

사용자 임베딩과 장소 임베딩을 기반으로 코사인 유사도로 장소를 추천합니다.
pgvector의 벡터 연산을 활용하여 효율적으로 유사도 검색을 수행합니다.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from sqlalchemy.orm import Session

from app.repository.recommendation_repository import RecommendationRepository
from app.schemas.recommendation import PlaceRecommendation

logger = logging.getLogger(__name__)


class RecommendationService:
    """장소 추천 서비스."""

    def __init__(self, db: Session) -> None:
        # 나중에 테스트할 땐 Repository만 mock으로 갈아끼우면 됨
        self._repo = RecommendationRepository(db)

    def recommend_places_by_user_embedding(
        self,
        user_embedding: Sequence[float],
        limit: int = 20,
    ) -> List[PlaceRecommendation]:

        rows = self._repo.find_by_user_embedding(user_embedding, limit)

        recommendations: List[PlaceRecommendation] = []
        for row in rows:
            rec = PlaceRecommendation(
                id=row["id"],
                title=row["title"],
                address=row["address"],
                categories=row["categories"],
                tags=row["tags"],
                summary=row["summary"],
                image_url=row["image_url"],
                longitude=row["longitude"],
                latitude=row["latitude"],
                similarity=float(row["similarity"]),
            )
            recommendations.append(rec)

        logger.info(
            "추천 완료: %s개 장소 (limit=%s, embedding_dim=%s)",
            len(recommendations),
            limit,
            len(user_embedding),
        )
        return recommendations
