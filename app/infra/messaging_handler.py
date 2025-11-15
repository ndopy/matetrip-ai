# Todo : 나중에
from json.decoder import JSONDecodeError
import json
import logging
from typing import Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from app.infra.rabbitmq_schema import (
    BehaviorEmbeddingReqMessage,
    ProfileEmbeddingReqMessage,
)
from app.database.session import get_db
from app.service.behavior_embedding_service import BehaviorEmbeddingService
from app.schemas.behavior import SaveBehaviorEventDto


logger = logging.getLogger(__name__)
# "여기에는 BaseModel을 상속한 어떤 Pydantic 모델 타입이 들어올 거야"라는 걸 타입 시스템에 알려주는 장치.
MessageT = TypeVar("MessageT", bound=BaseModel)


def parse_message(
    body: bytes,
    queue_name: str,
    model: Type[MessageT],  # 타입은 이거 호출하는 쪽에서 정해주는거임
) -> Optional[MessageT]:

    data = body.decode("utf-8").strip()

    if not data:
        logger.warning(f"[Q: {queue_name}] 빈 메시지를 받았습니다. 스킵할게요")
        return None

    try:
        json_payload = json.loads(data)
    except JSONDecodeError as exc:
        logger.warning(
            f"[Q: {queue_name}] 유효하지 않은 JSON 형식입니다. ({exc}): {data!r}"
        )
        return None

    # NestJS에서 {pattern, data} 형태로 보내므로 data 필드 추출
    if isinstance(json_payload, dict) and "data" in json_payload:
        json_payload = json_payload["data"]

    try:
        return model(**json_payload)
    except ValidationError as exc:
        logger.warning(f"[Q: {queue_name}] JSON_PAYLOAD 필드 검증 실패: {exc}")
        return None


def handle_profile_embedding_test(message: ProfileEmbeddingReqMessage) -> None:
    # Profile 임베딩 시작
    print(f"[profile_embedding] Processing user_id={message.user_id}")


def handle_behavior_embedding_test(message: BehaviorEmbeddingReqMessage) -> None:
    """행동 이벤트를 DB에 저장하고 임베딩 재계산"""
    logger.info(
        f"[behavior_embedding] Processing "
        f"user_id={message.user_id}, event_type={message.event_type}, "
        f"place_id={message.place_id}, weight={message.weight}"
    )

    # DB 세션 생성
    db = next(get_db())
    try:
        # BehaviorEmbeddingService를 사용하여 이벤트 저장
        service = BehaviorEmbeddingService(db)

        # event_data를 dict로 변환
        event_data_dict = message.event_data.model_dump() if message.event_data else {}

        # DTO로 변환
        dto = SaveBehaviorEventDto(
            user_id=message.user_id,
            event_type=message.event_type,
            event_data=event_data_dict,
            weight=message.weight,
            workspace_id=message.workspace_id,
            place_id=message.place_id,
        )

        # 행동 이벤트 저장 (임계값 도달 시 자동으로 임베딩 재계산)
        event_id = service.save_behavior_event(dto)

        logger.info(f"[behavior_embedding] Event saved successfully: event_id={event_id}")

    except Exception as e:
        logger.error(f"[behavior_embedding] Error saving event: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
