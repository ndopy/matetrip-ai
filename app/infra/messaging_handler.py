# Todo : 나중에
import json
import sys
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from app.database.database import get_db
from app.service.behavior.behavior_service import BehaviorService
from app.schemas.behavior import SaveBehaviorEventDto
from app.common.logger import logger
from app.schemas.rabbitmq_schema import (
    BehaviorEmbeddingReqMessage,
    ProfileEmbeddingReqMessage,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    # Allow running the script directly (`python app/infra/...`) without -m flag.
    sys.path.insert(0, str(PROJECT_ROOT))

log = logger
# "여기에는 BaseModel을 상속한 어떤 Pydantic 모델 타입이 들어올 거야"라는 걸 타입 시스템에 알려주는 장치.
MessageT = TypeVar("MessageT", bound=BaseModel)


def parse_message(
    body: bytes,
    queue_name: str,
    model: Type[MessageT],  # 타입은 이거 호출하는 쪽에서 정해주는거임
) -> Optional[MessageT]:

    data = body.decode("utf-8").strip()

    if not data:
        log.warning(f"[Q: {queue_name}] 빈 메시지를 받았습니다. 스킵할게요")
        return None

    try:
        json_payload = json.loads(data)
    except JSONDecodeError as exc:
        log.warning(
            f"[Q: {queue_name}] 유효하지 않은 JSON 형식입니다. ({exc}): {data!r}"
        )
        return None

    if not isinstance(json_payload, dict):
        log.warning(
            f"[Q: {queue_name}] dict 형태가 아닌 payload입니다: {json_payload!r}"
        )
        return None

    # NestJS에서 {pattern, data} 형태로 보내므로 data 필드 추출
    if isinstance(json_payload, dict) and "data" in json_payload:
        json_payload = json_payload["data"]

    try:
        return model(**json_payload)
    except ValidationError as exc:
        log.warning(f"[Q: {queue_name}] JSON_PAYLOAD 필드 검증 실패: {exc}")
        return None


def handle_profile_embedding_test(message: ProfileEmbeddingReqMessage) -> None:
    # Profile 임베딩 시작
    print(f"[profile_embedding] Processing user_id={message.user_id}")


def handle_behavior_save_and_embedding(message: BehaviorEmbeddingReqMessage) -> None:
    """행동 이벤트를 DB에 저장하고 임베딩 재계산"""
    log.info(f"[Behavior_embedding] Processing ")

    # DB 세션 생성
    for db in get_db():
        try:
            service = BehaviorService(db)
            dto = SaveBehaviorEventDto.from_message(message)
            # 행동 이벤트 저장 (임계값 도달 시 자동으로 임베딩 재계산)
            event_id = service.save_behavior_event(dto)

            log.info(
                f"[behavior_embedding] Event saved successfully: event_id={event_id}"
            )

        except Exception as e:
            log.error(f"[behavior_embedding] Error saving event: {e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()
