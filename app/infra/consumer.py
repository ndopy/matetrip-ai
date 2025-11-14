import json
from json.decoder import JSONDecodeError
from typing import Optional, Type, TypeVar

import pika
from pydantic import BaseModel, ValidationError


class Profile_embedding_req_message(BaseModel):
    user_id: str


class Behavior_embedding_req_message(BaseModel):
    user_id: str
    title: str
    address: str
    longitude: float
    latitude: float


MessageT = TypeVar("MessageT", bound=BaseModel)


def parse_message(
    body: bytes, queue_name: str, model: Type[MessageT]
) -> Optional[MessageT]:
    data = body.decode("utf-8").strip()

    if not data:
        print(f"[{queue_name}] Received empty message. Skipping...")
        return None

    try:
        json_payload = json.loads(data)
    except JSONDecodeError as exc:
        print(f"[{queue_name}] Invalid JSON payload ({exc}): {data!r}")
        return None

    try:
        return model(**json_payload)
    except ValidationError as exc:
        print(f"[{queue_name}] Validation failed: {exc}")
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


params = pika.URLParameters("amqp://guest:guest@localhost:5672/")

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

print("Started consuming...")
channel.start_consuming()
