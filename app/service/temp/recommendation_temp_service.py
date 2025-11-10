"""
Recommendation service

Provides user-, place-, and location-based place recommendations backed by pgvector.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import CTE, Select, func, literal, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import AliasedClass, Session, aliased
from sqlalchemy.sql import ColumnElement

from app.models.place import Place
from app.models.review import PlaceReview
from app.schemas.recommendation import PlaceRecommendation

logger = logging.getLogger(__name__)

PlaceEntity = type[Place] | AliasedClass


class RecommendationServiceError(RuntimeError):
    """Raised when recommendation queries fail."""


class RecommendationTempService:
    """Business layer for place recommendations."""

    EARTH_RADIUS_KM = 6371.0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def recommend_places_by_user_embedding(
        self,
        db: Session,
        user_embedding: Sequence[float],
        limit: int = 20,
        min_review_count: int = 3,
        categories: Sequence[str] | None = None,
        region: str | None = None,
    ) -> list[PlaceRecommendation]:
        stats = self._review_stats_cte()
        vector = self._normalize_vector(user_embedding)
        similarity_expr = self._similarity_against_vector(Place, vector)
        columns = self._place_columns(Place, stats)

        stmt = (
            select(*columns, similarity_expr.label("similarity"))
            .select_from(Place)
            .outerjoin(stats, stats.c.place_id == Place.id)
            .where(Place.embedding.isnot(None))
        )
        stmt = self._apply_min_reviews(stmt, stats, min_review_count)
        stmt = self._apply_category_filter(stmt, Place, categories)
        stmt = self._apply_region_filter(stmt, Place, region)
        stmt = stmt.order_by(similarity_expr.desc(), Place.id).limit(limit)

        recommendations = self._execute(db, stmt, context="user_embedding")
        logger.info(
            "추천 완료: %s개 장소 (min_reviews=%s, categories=%s, region=%s)",
            len(recommendations),
            min_review_count,
            categories,
            region,
        )
        return recommendations

    def recommend_similar_places(
        self,
        db: Session,
        place_id: str,
        limit: int = 10,
        min_review_count: int = 3,
    ) -> list[PlaceRecommendation]:
        stats = self._review_stats_cte()
        origin = aliased(Place, name="origin")
        candidate = aliased(Place, name="candidate")
        similarity_expr = self._similarity_between_places(candidate, origin)
        columns = self._place_columns(candidate, stats)

        stmt = (
            select(*columns, similarity_expr.label("similarity"))
            .select_from(origin)
            .join(candidate, candidate.id != origin.id)
            .outerjoin(stats, stats.c.place_id == candidate.id)
            .where(
                origin.id == place_id,
                origin.embedding.isnot(None),
                candidate.embedding.isnot(None),
                self._review_count_expr(stats) >= min_review_count,
            )
            .order_by(similarity_expr.desc(), candidate.id)
            .limit(limit)
        )

        recommendations = self._execute(db, stmt, context="similar_places")
        logger.info(
            "유사 장소 추천 완료: %s개 (place_id=%s)", len(recommendations), place_id
        )
        return recommendations

    def recommend_places_by_location(
        self,
        db: Session,
        user_embedding: Sequence[float],
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        limit: int = 20,
        min_review_count: int = 3,
    ) -> list[PlaceRecommendation]:
        stats = self._review_stats_cte()
        vector = self._normalize_vector(user_embedding)
        similarity_expr = self._similarity_against_vector(Place, vector)
        distance_expr = self._distance_from(latitude, longitude, Place)
        columns = self._place_columns(Place, stats)

        stmt = (
            select(
                *columns,
                similarity_expr.label("similarity"),
                distance_expr.label("distance_km"),
            )
            .select_from(Place)
            .outerjoin(stats, stats.c.place_id == Place.id)
            .where(
                Place.embedding.isnot(None),
                self._review_count_expr(stats) >= min_review_count,
                distance_expr <= radius_km,
            )
            .order_by(similarity_expr.desc(), distance_expr.asc(), Place.id)
            .limit(limit)
        )

        recommendations = self._execute(db, stmt, context="location")
        logger.info(
            "위치 기반 추천 완료: %s개 (lat=%s, lon=%s, radius=%skm)",
            len(recommendations),
            latitude,
            longitude,
            radius_km,
        )
        return recommendations

    def get_trending_places(
        self,
        db: Session,
        limit: int = 20,
        days: int = 7,
        region: str | None = None,
    ) -> list[PlaceRecommendation]:
        stats = self._review_stats_cte()
        columns = self._place_columns(Place, stats)
        review_count = self._review_count_expr(stats)
        threshold = self._days_ago(days)

        stmt = (
            select(*columns, Place.updated_at.label("last_updated"))
            .select_from(Place)
            .outerjoin(stats, stats.c.place_id == Place.id)
            .where(
                Place.embedding.isnot(None),
                Place.updated_at.isnot(None),
                Place.updated_at > threshold,
            )
            .order_by(review_count.desc(), Place.updated_at.desc(), Place.id)
            .limit(limit)
        )
        stmt = self._apply_region_filter(stmt, Place, region)

        recommendations = self._execute(db, stmt, context="trending")
        logger.info("인기 장소 조회 완료: %s개 (최근 %s일)", len(recommendations), days)
        return recommendations

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _execute(
        self,
        db: Session,
        stmt: Select,
        *,
        context: str,
    ) -> list[PlaceRecommendation]:
        try:
            rows = db.execute(stmt).mappings().all()
        except SQLAlchemyError as exc:  # pragma: no cover
            logger.exception("Recommendation query failed (%s)", context)
            raise RecommendationServiceError(
                f"Failed to execute {context} recommendation query"
            ) from exc
        return [PlaceRecommendation.from_mapping(row) for row in rows]

    def _review_stats_cte(self) -> CTE:
        return (
            select(
                PlaceReview.place_id.label("place_id"),
                func.count().label("review_count"),
            )
            .where(
                PlaceReview.is_deleted.is_(False),
                PlaceReview.embedding.isnot(None),
            )
            .group_by(PlaceReview.place_id)
            .cte("review_stats")
        )

    def _place_columns(self, place: PlaceEntity, stats: CTE) -> tuple:
        review_count = self._review_count_expr(stats).label("review_count")
        return (
            place.id.label("id"),
            place.title.label("title"),
            place.address.label("address"),
            place.categories.label("categories"),
            place.tags.label("tags"),
            place.summary.label("summary"),
            place.image_url.label("image_url"),
            place.longitude.label("longitude"),
            place.latitude.label("latitude"),
            review_count,
        )

    @staticmethod
    def _normalize_vector(vector: Sequence[float]) -> list[float]:
        try:
            return [float(value) for value in vector]
        except TypeError as exc:  # pragma: no cover
            raise ValueError("Embedding vector must be iterable") from exc

    def _similarity_against_vector(
        self,
        place: PlaceEntity,
        vector: Sequence[float],
    ) -> ColumnElement[float]:
        return 1 - place.embedding.cosine_distance(vector)

    @staticmethod
    def _similarity_between_places(
        candidate: PlaceEntity,
        origin: PlaceEntity,
    ) -> ColumnElement[float]:
        return 1 - candidate.embedding.cosine_distance(origin.embedding)

    def _distance_from(
        self,
        latitude: float,
        longitude: float,
        place: PlaceEntity,
    ) -> ColumnElement[float]:
        lat = func.radians(literal(latitude))
        lon = func.radians(literal(longitude))
        place_lat = func.radians(place.latitude)
        place_lon = func.radians(place.longitude)
        return literal(self.EARTH_RADIUS_KM) * func.acos(
            func.cos(lat) * func.cos(place_lat) * func.cos(place_lon - lon)
            + func.sin(lat) * func.sin(place_lat)
        )

    @staticmethod
    def _review_count_expr(stats: CTE) -> ColumnElement[int]:
        return func.coalesce(stats.c.review_count, 0)

    def _apply_min_reviews(
        self,
        stmt: Select,
        stats: CTE,
        minimum: int,
    ) -> Select:
        if minimum <= 0:
            return stmt
        return stmt.where(self._review_count_expr(stats) >= minimum)

    def _apply_category_filter(
        self,
        stmt: Select,
        place: PlaceEntity,
        categories: Sequence[str] | None,
    ) -> Select:
        if not categories:
            return stmt
        category_filters = [
            place.categories.contains([category]) for category in categories
        ]
        return stmt.where(or_(*category_filters))

    def _apply_region_filter(
        self,
        stmt: Select,
        place: PlaceEntity,
        region_prefix: str | None,
    ) -> Select:
        if not region_prefix:
            return stmt
        return stmt.where(place.address.like(f"{region_prefix}%"))

    @staticmethod
    def _days_ago(days: int) -> datetime:
        days = max(days, 0)
        return datetime.utcnow() - timedelta(days=days)
