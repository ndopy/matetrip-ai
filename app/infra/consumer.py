import json
from json.decoder import JSONDecodeError
import os
from typing import Optional, Type, TypeVar

import pika
from pydantic import BaseModel, Field, ValidationError


class Profile_embedding_req_message(BaseModel):
    user_id: str


class Behavior_embedding_req_message(BaseModel):
    user_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    latitude: float = Field(..., ge=-90.0, le=90.0)


# "여기에는 BaseModel을 상속한 어떤 Pydantic 모델 타입이 들어올 거야"라는 걸 타입 시스템에 알려주는 장치.
MessageT = TypeVar("MessageT", bound=BaseModel)


# Todo : 나중에
def parse_message(
    body: bytes,
    queue_name: str,
    model: Type[MessageT],  # 타입은 이거 호출하는 쪽에서 정해주는거임
) -> Optional[MessageT]:

    data = body.decode("utf-8").strip()

    if not data:
        print(f"[Q: {queue_name}] 빈 메시지를 받았습니다. 스킵할게요")
        return None

    try:
        json_payload = json.loads(data)
    except JSONDecodeError as exc:
        print(f"[Q: {queue_name}] 유효하지 않은 JSON 형식입니다. ({exc}): {data!r}")
        return None

    try:
        return model(**json_payload)
    except ValidationError as exc:
        print(f"[Q: {queue_name}] JSON_PAYLOAD 필드 검증 실패: {exc}")
        return None


def handle_profile_embedding_test(message: Profile_embedding_req_message) -> None:
    # Profile 임베딩 시작
    print(f"[profile_embedding] Processing user_id={message.user_id}")


def handle_behavior_embedding_test(message: Behavior_embedding_req_message) -> None:
    # Behavior 임베딩 시작
    print(
        "[behavior_embedding] Processing "
        f"user_id={message.user_id}, title={message.title}"
    )


def consume_profile_embedding(channel, method, properties, body):
    message = parse_message(body, "profile_embedding", Profile_embedding_req_message)
    if message:
        handle_profile_embedding_test(message)


def consume_behavior_embedding(channel, method, properties, body):
    message = parse_message(body, "behavior_embedding", Behavior_embedding_req_message)
    if message:
        handle_behavior_embedding_test(message)


def create_consumer():
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    params = pika.URLParameters(rabbitmq_url)
    params.blocked_connection_timeout = 300  # 5min

    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.queue_declare(queue="profile_embedding", durable=True)
    channel.basic_consume(
        queue="profile_embedding",
        on_message_callback=consume_profile_embedding,
        auto_ack=True,
    )

    channel.queue_declare(queue="behavior_embedding", durable=True)
    channel.basic_consume(
        queue="behavior_embedding",
        on_message_callback=consume_behavior_embedding,
        auto_ack=True,
    )

    return connection, channel


def main():
    connection = None
    connection, channel = create_consumer()
    print("Started consuming...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
