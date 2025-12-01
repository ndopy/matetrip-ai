from typing import Any, Dict, List, Sequence  # Sequence comes from typing
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.embedding_utils import EmbeddingUtils


class RecommendationRepository:
    """장소 임베딩 기반 추천 쿼리 전담."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_user_embedding(
        self,
        user_embedding: Sequence[float],
        limit: int,
    ) -> List[Dict[str, Any]]:

        embedding_literal = EmbeddingUtils._to_vector_literal(user_embedding)

        sql = text(
            """
            SELECT
                id,
                title,
                address,
                categories,
                tags,
                summary,
                image_url,
                longitude,
                latitude,
                1 - (embedding <=> :user_embedding::vector) AS similarity
            FROM places
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :user_embedding::vector
            LIMIT :limit
            """
        )

        rows = (
            self._db.execute(sql, {"user_embedding": embedding_literal, "limit": limit})
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]
