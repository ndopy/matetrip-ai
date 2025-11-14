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

    try:
        return model(**json_payload)
    except ValidationError as exc:
        logger.warning(f"[Q: {queue_name}] JSON_PAYLOAD 필드 검증 실패: {exc}")
        return None


def handle_profile_embedding_test(message: ProfileEmbeddingReqMessage) -> None:
    # Profile 임베딩 시작
    print(f"[profile_embedding] Processing user_id={message.user_id}")


def handle_behavior_embedding_test(message: BehaviorEmbeddingReqMessage) -> None:
    # Behavior 임베딩 시작
    print(
        "[behavior_embedding] Processing "
        f"user_id={message.user_id}, title={message.title}"
    )
