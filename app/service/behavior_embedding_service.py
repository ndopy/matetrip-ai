import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.common.embedding_utils import EmbeddingUtils
from app.repository.behavior_repository import BehaviorRepository
from app.models.user_behavior import UserBehaviorEvent, UserBehaviorEmbedding
from app.schemas.behavior import SaveBehaviorEventDto

log = logging.getLogger(__name__)


class BehaviorEmbeddingService:
    """
    사용자 행동 기반 임베딩 생성 및 관리 서비스
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = BehaviorRepository(db)

    # TODO: DB에 없는 장소일 경우 예외가 아니라 다르게 처리할 수 있을지 고민
    def save_behavior_event(self, dto: SaveBehaviorEventDto) -> str:
        """
        행동 이벤트를 저장하고, 임계값 도달 시 임베딩 재계산

        Args:
            dto: SaveBehaviorEventDto

        Returns:
            저장된 이벤트 ID
        """
        # 1. 이벤트 저장
        event_id = self.repository.save_behavior_event(
            user_id=dto.user_id,
            event_type=dto.event_type,
            weight=dto.weight,
            workspace_id=dto.workspace_id,
            place_id=dto.place_id,
        )

        log.info(
            f"[행동 이벤트 저장] user_id={dto.user_id}, "
            f"event_type={dto.event_type}, place_id={dto.place_id}, event_id={event_id}"
        )

        # 2. 이벤트 개수 확인
        total_events = self.repository.count_user_events(dto.user_id)

        # 3. 임계값 도달 시 임베딩 재계산 (10개마다)
        if total_events % 10 == 0:
            log.info(f"[임베딩 재계산 트리거 발동]")
            self.regenerate_behavior_embedding(dto.user_id)

        return str(event_id)

    def regenerate_behavior_embedding(self, user_id: str, days: int = 7) -> None:
        """
        사용자의 행동 임베딩을 재생성
        최근 N일 동안의 행동에서 장소 임베딩의 가중평균 계산

        Args:
            days: 최근 N일 (기본 7 -> 실제 서비스는 길게 하는게 좋을 듯 90일 정도)
        """
        log.info(f"[행동 임베딩 재생성 시작]")

        # 1. 사용자의 최근 행동에서 장소 임베딩과 가중치 가져오기
        weighted_places = self.repository.get_weighted_place_embeddings(user_id, days)

        if not weighted_places:
            log.warning(
                f"[행동 임베딩 재생성 실패] 사용자의 행동 데이터가 없습니다. user_id={user_id}"
            )
            return

        # 2. 시간 기반 감쇠 적용 (최근 행동에 더 높은 가중치)
        weighted_embeddings = []
        total_weight = 0.0
        aggregated_stats = {
            "category_scores": {},
            "total_events": len(weighted_places),
            "date_range_days": days,
        }

        for place in weighted_places:
            # 시간 감쇠 계산
            created_at = place["created_at"]
            days_ago = (datetime.now(timezone.utc) - created_at).days

            decay_factor = 0.95 ** (days_ago / 7)  # 주당 5% 감소

            # 최종 가중치 = 행동 가중치 × 시간 감쇠
            final_weight: float = place.get("weight") * decay_factor

            place_embedding: List[float] = EmbeddingUtils.to_vector(
                place.get("place_embedding")
            )

            weighted_embeddings.append((place_embedding, final_weight))
            total_weight += abs(final_weight)  # 부정 가중치도 고려

            # 카테고리별 점수 집계
            category = place.get("category")
            if category:
                if category not in aggregated_stats["category_scores"]:
                    aggregated_stats["category_scores"][category] = 0.0
                aggregated_stats["category_scores"][category] += final_weight

        # 3. 가중평균 계산
        if total_weight == 0:
            log.warning(
                f"[행동 임베딩 재생성 실패] 총 가중치가 0입니다. user_id={user_id}"
            )
            return

        # 각 임베딩에 가중치를 곱하고 합산
        embedding_dim = len(weighted_embeddings[0][0])
        behavior_embedding = np.zeros(embedding_dim)

        for embedding, weight in weighted_embeddings:
            behavior_embedding += np.array(embedding) * weight

        # 정규화
        behavior_embedding = behavior_embedding / total_weight

        # 4. 카테고리 점수 정규화
        for category in aggregated_stats["category_scores"]:
            aggregated_stats["category_scores"][category] = round(
                aggregated_stats["category_scores"][category] / total_weight, 2
            )

        # 5. DB에 저장
        total_events = self.repository.count_user_events(user_id)
        self.repository.upsert_behavior_embedding(
            user_id=user_id,
            behavior_embedding=behavior_embedding.tolist(),
            aggregated_data=aggregated_stats,
            total_events_count=total_events,
        )

        log.info(
            f"[행동 임베딩 재생성 완료] user_id={user_id}, "
            f"embedding_dim={embedding_dim}, "
            f"total_events={total_events}, "
            f"categories={list(aggregated_stats['category_scores'].keys())}"
        )

    def get_user_behavior_embedding(
        self, user_id: str
    ) -> Optional[UserBehaviorEmbedding]:
        """사용자의 행동 임베딩 조회"""
        return self.repository.get_behavior_embedding(user_id)

    def get_user_recent_events(
        self, user_id: str, limit: int = 50
    ) -> List[UserBehaviorEvent]:
        """사용자의 최근 행동 이벤트 조회"""
        return self.repository.get_user_behavior_events(user_id, limit)
