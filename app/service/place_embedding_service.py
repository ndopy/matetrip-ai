"""
장소 임베딩 서비스 (하이브리드 방식)

리뷰 임베딩들의 평균을 계산하여 places.embedding에 저장합니다.
- place.embedding: 리뷰 임베딩 평균 (검색 정확도 - 긍정/부정 비율 보존)
- place.summary: LLM 요약 (사용자 표시용)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Sequence
from uuid import UUID

import numpy as np
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from pgvector import Vector as PgVector

from app.models.place import Place
from app.models.review import PlaceReview

logger = logging.getLogger(__name__)


class PlaceEmbeddingService:
    """리뷰 임베딩 평균을 계산하여 장소 임베딩을 생성/갱신하는 서비스."""

    def __init__(self, *, minimum_reviews: int = 1) -> None:
        self.minimum_reviews = minimum_reviews

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def refresh_embedding(self, db: Session, place_id: UUID) -> List[float] | None:
        """
        리뷰 임베딩들의 평균을 계산하여 places.embedding을 업데이트합니다.
        리뷰가 minimum_reviews 미만이면 임베딩을 삭제합니다.
        """
        place = self._get_place(db, place_id)
        review_vectors = self._fetch_review_embeddings(db, place_id)

        if len(review_vectors) < self.minimum_reviews:
            if place.embedding is not None:
                logger.info(
                    "Clearing embedding for %s (reviews=%s < threshold=%s)",
                    place.title,
                    len(review_vectors),
                    self.minimum_reviews,
                )
            place.embedding = None
            db.commit()
            return None

        # 리뷰 임베딩들의 평균 계산
        averaged_vector = self._mean_vector(review_vectors)
        place.embedding = PgVector(averaged_vector)
        db.commit()

        logger.info(
            "✓ Updated embedding for %s (reviews=%s)",
            place.title,
            len(review_vectors),
        )
        return averaged_vector

    def get_places_without_embedding(
        self,
        db: Session,
        limit: int = 1000,
    ) -> List[Place]:
        """임베딩이 비어 있는 장소 목록."""
        stmt = (
            select(Place)
            .where(Place.embedding.is_(None))
            .order_by(Place.created_at.desc())
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def get_places_needing_update(
        self,
        db: Session,
        days_threshold: int = 30,
        limit: int = 1000,
    ) -> List[Place]:
        """
        오래되었거나 임베딩이 비어 있는 장소 목록을 조회합니다.
        updated_at 기준으로 필터링하며, days_threshold가 0 이하이면
        단순히 임베딩이 없는 장소만 반환합니다.
        """
        if days_threshold <= 0:
            base_condition = Place.embedding.is_(None)
        else:
            threshold_date = self._utc_now() - timedelta(days=days_threshold)
            base_condition = or_(
                Place.embedding.is_(None),
                Place.updated_at.is_(None),
                Place.updated_at < threshold_date,
            )

        stmt = (
            select(Place)
            .where(base_condition)
            .order_by(Place.updated_at.asc().nullsfirst())
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    # ------------------------------------------------------------------
    # 내부 헬퍼 함수
    # ------------------------------------------------------------------
    def _get_place(self, db: Session, place_id: UUID) -> Place:
        place = db.get(Place, place_id)
        if not place:
            raise ValueError(f"Place not found: {place_id}")
        return place

    def _fetch_review_embeddings(
        self, db: Session, place_id: UUID
    ) -> List[List[float]]:
        """리뷰 임베딩들을 가져옵니다."""
        stmt = (
            select(PlaceReview.embedding)
            .where(
                PlaceReview.place_id == place_id,
                PlaceReview.is_deleted == False,  # noqa: E712
                PlaceReview.embedding.isnot(None),
            )
            .order_by(PlaceReview.created_at.asc())
        )
        rows = db.execute(stmt).fetchall()
        return [list(row[0]) for row in rows if row[0] is not None]

    @staticmethod
    def _mean_vector(vectors: Sequence[Sequence[float]]) -> list[float]:
        """벡터들의 평균을 계산합니다."""
        matrix = np.array(vectors, dtype=np.float32)
        return np.mean(matrix, axis=0).tolist()

    @staticmethod
    def _utc_now() -> datetime:
        """Return a timezone-aware UTC timestamp (trimmed to naive for DB comparisons)."""
        return datetime.now(timezone.utc).replace(tzinfo=None)
