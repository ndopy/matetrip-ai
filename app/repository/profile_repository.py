import logging
from typing import Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.embedding_utils import EmbeddingUtils
from app.schemas.profile import ProfileTextDto

logger = logging.getLogger(__name__)


class ProfileRepository:
    """profile 테이블 조회/임베딩 저장 전담"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_profile_text(self, user_id: str) -> Optional[ProfileTextDto]:
        sql = text(
            """
            SELECT nickname, intro, description, mbti, travel_styles, tendency
            FROM profile
            WHERE user_id = :user_id
            """
        )
        row = self._db.execute(sql, {"user_id": str(user_id)}).mappings().first()

        if not row:
            return None

        return ProfileTextDto(
            nickname=row["nickname"],
            intro=row["intro"],
            description=row["description"],
            mbti=row["mbti"],
            travel_styles=list(row["travel_styles"] or []),
            tendency=list(row["tendency"] or []),
        )

    def update_profile_embedding(
        self, user_id: str, embedding: Sequence[float]
    ) -> None:
        embedding_literal = EmbeddingUtils._to_vector_literal(embedding)

        sql = text(
            """
            UPDATE profile
            SET profile_embedding = CAST(:embedding AS vector)
            WHERE user_id = :user_id
            """
        )
        self._db.execute(
            sql, {"user_id": str(user_id), "embedding": embedding_literal}
        )
        self._db.commit()
