from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session

from app.common.embedding_utils import EmbeddingUtils
from app.models.user_behavior import UserBehaviorEvent, UserBehaviorEmbedding
from app.models.user import User  # noqa: F401
from app.models.workspace import Workspace  # noqa: F401
from app.models.plan_day import PlanDay  # noqa: F401

# Place를 import하기 전에 PlaceReview를 먼저 import (relationship 초기화를 위해)
from app.models.review import PlaceReview  # noqa: F401
from app.models.place import Place
from app.schemas.behavior import (
    UserEventResDto,
    WeightedPlaceEmbeddingDto,
)
from app.enums.user_behavior import BehaviorEventType


class BehaviorRepository:
    """사용자 행동 이벤트 및 임베딩 저장/조회 전담"""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_vector_literal(embedding: Sequence[float]) -> str:
        """임베딩 배열을 PostgreSQL vector 리터럴로 변환"""
        if not all(isinstance(x, (int, float)) for x in embedding):
            raise ValueError("Embedding must contain only numeric values")

        return "[" + ",".join(map(str, embedding)) + "]"

    # ===== user_behavior_events 관련 =====

    def save_behavior_event(
        self,
        user_id: str,
        event_type: str,
        weight: float,
        created_at: datetime,
        workspace_id: Optional[str] = None,
        place_id: Optional[str] = None,
        planday_id: Optional[str] = None,
    ) -> UUID:
        """행동 이벤트를 DB에 저장"""
        event = UserBehaviorEvent(
            user_id=UUID(user_id),
            event_type=event_type,
            weight=weight,
            created_at=created_at,
            workspace_id=UUID(workspace_id) if workspace_id else None,
            place_id=UUID(place_id) if place_id else None,
            plan_day_id=UUID(planday_id) if planday_id else None,
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
        # EXCLUDED: INSERT가 넣으려고 했던 row(데이터)를 담고 있는 임시 테이블 (POSTGRES)

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

    def get_behavior_embedding(self, user_id: UUID) -> Optional[UserBehaviorEmbedding]:
        """특정 사용자의 행동 임베딩 조회"""
        stmt = select(UserBehaviorEmbedding).where(
            UserBehaviorEmbedding.user_id == user_id
        )

        result = self._db.execute(stmt)
        return result.scalar_one_or_none()

    def get_weighted_place_embeddings(
        self,
        user_id: UUID,
        date_range_days: int = 90,
    ) -> List[WeightedPlaceEmbeddingDto]:
        """
        사용자의 최근 행동에서 장소 임베딩과 가중치를 가져옴
        (행동 임베딩 계산용)
        최근 days일 동안에 수행한 행동 로그를 바탕으로 행동에 연관된 장소정보와 임베딩을 불러옴
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=date_range_days)

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
                UserBehaviorEvent.user_id == user_id,
                UserBehaviorEvent.place_id.isnot(None),
                Place.embedding.isnot(None),
                UserBehaviorEvent.created_at > cutoff_date,
            )
            .order_by(UserBehaviorEvent.created_at.desc())
        )

        result = self._db.execute(stmt)
        rows = result.mappings().all()

        weighted_places: List[WeightedPlaceEmbeddingDto] = []
        for row in rows:
            weighted_places.append(
                WeightedPlaceEmbeddingDto(
                    place_id=row["place_id"],
                    weight=float(row["weight"]),
                    created_at=row["created_at"],
                    event_type=BehaviorEventType(row["event_type"]),
                    place_embedding=EmbeddingUtils.to_vector(row["place_embedding"]),
                    place_name=row["place_name"],
                    category=row["category"],
                )
            )

        return weighted_places

    def get_user_recent_events(
        self, user_id: str, date_range_days: int, event_type: BehaviorEventType
    ) -> List[UserEventResDto]:
        """
        특정 기간 내 사용자의 이벤트 조회

        Args:
            user_id: 사용자 ID
            date_range_days: 조회할 날짜 범위 (일 단위)

        Returns:
            marking 이벤트와 관련 장소 정보 리스트
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=date_range_days)

        stmt = (
            select(
                UserBehaviorEvent.id.label("event_id"),
                UserBehaviorEvent.event_type,
                UserBehaviorEvent.weight,
                UserBehaviorEvent.created_at,
                UserBehaviorEvent.workspace_id,
                Place.id.label("place_id"),
            )
            .join(Place, UserBehaviorEvent.place_id == Place.id)
            .where(
                UserBehaviorEvent.user_id == UUID(user_id),
                UserBehaviorEvent.event_type == event_type.value,
                UserBehaviorEvent.place_id.isnot(None),
                UserBehaviorEvent.created_at > cutoff_date,
            )
            .order_by(UserBehaviorEvent.created_at.desc())
        )

        result = self._db.execute(stmt)
        rows = result.mappings().all()

        events: List[UserEventResDto] = []
        for row in rows:
            events.append(
                UserEventResDto(
                    event_id=row["event_id"],
                    event_type=BehaviorEventType(row["event_type"]),
                    created_at=row["created_at"],
                    workspace_id=row["workspace_id"],
                    place_id=row["place_id"],
                )
            )

        return events
