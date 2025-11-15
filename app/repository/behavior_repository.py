from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session

from app.models.user_behavior import UserBehaviorEvent, UserBehaviorEmbedding
from app.models.place import Place


class BehaviorRepository:
    """사용자 행동 이벤트 및 임베딩 저장/조회 전담"""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_vector_literal(embedding: Sequence[float]) -> str:
        """임베딩 배열을 PostgreSQL vector 리터럴로 변환"""
        return "[" + ",".join(map(str, embedding)) + "]"

    # ===== user_behavior_events 관련 =====

    def save_behavior_event(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        weight: float,
        workspace_id: Optional[str] = None,
        place_id: Optional[str] = None,
    ) -> UUID:
        """행동 이벤트를 DB에 저장"""
        event = UserBehaviorEvent(
            user_id=UUID(user_id),
            event_type=event_type,
            event_data=event_data,
            weight=weight,
            workspace_id=UUID(workspace_id) if workspace_id else None,
            place_id=UUID(place_id) if place_id else None,
        )

        self._db.add(event)
        self._db.commit()
        self._db.refresh(event)

        return event.id

    def get_user_behavior_events(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[UserBehaviorEvent]:
        """특정 사용자의 최근 행동 이벤트 조회"""
        stmt = (
            select(UserBehaviorEvent)
            .where(UserBehaviorEvent.user_id == UUID(user_id))
            .order_by(UserBehaviorEvent.created_at.desc())
            .limit(limit)
        )

        result = self._db.execute(stmt)
        return list(result.scalars().all())

    def count_user_events(self, user_id: str) -> int:
        """특정 사용자의 전체 행동 이벤트 수"""
        stmt = (
            select(func.count())
            .select_from(UserBehaviorEvent)
            .where(UserBehaviorEvent.user_id == UUID(user_id))
        )
        return self._db.execute(stmt).scalar_one()

    # ===== user_behavior_embeddings 관련 =====

    def upsert_behavior_embedding(
        self,
        user_id: str,
        behavior_embedding: Sequence[float],
        aggregated_data: Dict[str, Any],
        total_events_count: int,
    ) -> None:
        """사용자의 행동 임베딩을 저장 또는 업데이트 (ORM + Raw SQL)"""
        # pgvector는 ORM에서 직접 upsert가 까다로우므로 raw SQL 사용
        embedding_literal = self._to_vector_literal(behavior_embedding)

        sql = text(
            """
            INSERT INTO user_behavior_embeddings (
                user_id, behavior_embedding, aggregated_data, total_events_count, last_updated
            )
            VALUES (
                :user_id, :embedding::vector, :aggregated_data::jsonb, :total_events_count, NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                behavior_embedding = EXCLUDED.behavior_embedding,
                aggregated_data = EXCLUDED.aggregated_data,
                total_events_count = EXCLUDED.total_events_count,
                last_updated = NOW()
            """
        )

        self._db.execute(
            sql,
            {
                "user_id": user_id,
                "embedding": embedding_literal,
                "aggregated_data": aggregated_data,
                "total_events_count": total_events_count,
            },
        )
        self._db.commit()

    def get_behavior_embedding(self, user_id: str) -> Optional[UserBehaviorEmbedding]:
        """특정 사용자의 행동 임베딩 조회"""
        stmt = select(UserBehaviorEmbedding).where(
            UserBehaviorEmbedding.user_id == UUID(user_id)
        )

        result = self._db.execute(stmt)
        return result.scalar_one_or_none()

    def get_weighted_place_embeddings(
        self,
        user_id: str,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """
        사용자의 최근 행동에서 장소 임베딩과 가중치를 가져옴
        (행동 임베딩 계산용)
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        stmt = (
            select(
                UserBehaviorEvent.place_id,
                UserBehaviorEvent.weight,
                UserBehaviorEvent.created_at,
                UserBehaviorEvent.event_type,
                Place.embedding.label("place_embedding"),
                Place.title.label("place_name"),
                Place.category,
            )
            .join(Place, UserBehaviorEvent.place_id == Place.id)
            .where(
                UserBehaviorEvent.user_id == UUID(user_id),
                UserBehaviorEvent.place_id.isnot(None),
                Place.embedding.isnot(None),
                UserBehaviorEvent.created_at > cutoff_date,
            )
            .order_by(UserBehaviorEvent.created_at.desc())
        )

        result = self._db.execute(stmt)
        rows = result.mappings().all()

        return [dict(row) for row in rows]
