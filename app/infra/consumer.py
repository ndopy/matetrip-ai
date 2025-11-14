import os
import sys
import logging
from pathlib import Path
from typing import Final

import pika
import pika.exceptions

# Allow running this module directly via `python app/infra/consumer.py`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.infra.messaging_handler import (
    handle_behavior_embedding_test,
    handle_profile_embedding_test,
    parse_message,
)
from app.infra.rabbitmq_schema import (
    BehaviorEmbeddingReqMessage,
    ProfileEmbeddingReqMessage,
)

rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
_raw_profile_queue = os.getenv("RABBITMQ_PROFILE_QUEUE")
_raw_behavior_queue = os.getenv("RABBITMQ_BEHAVIOR_QUEUE")
if (_raw_profile_queue is None) or (_raw_behavior_queue is None):
    raise ValueError("환경변수로부터 QUEUE이름을 불러오지 못 했습니다.")

profile_queue: Final[str] = _raw_profile_queue
behavior_queue: Final[str] = _raw_behavior_queue

logger = logging.getLogger(__name__)


def consume_profile_embedding(channel, method, properties, body):
    message = parse_message(body, profile_queue, ProfileEmbeddingReqMessage)
    if message:
        try:
            handle_profile_embedding_test(message)
        except Exception as e:
            print(f"[profile_embedding] 처리 중 오류 발생: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    else:
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def consume_behavior_embedding(channel, method, properties, body):
    message = parse_message(body, "behavior_embedding", BehaviorEmbeddingReqMessage)
    if message:
        try:
            handle_behavior_embedding_test(message)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[behavior_embedding] 처리 중 오류 발생: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    else:
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def create_consumer():

    params = pika.URLParameters(rabbitmq_url)
    params.blocked_connection_timeout = 300  # 5min

    try:
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"RabbitMQ 연결 실패", exc_info=True)
        raise

    channel.queue_declare(queue=profile_queue, durable=True)
    channel.basic_consume(
        queue=profile_queue,
        on_message_callback=consume_profile_embedding,
        auto_ack=False,
    )

    channel.queue_declare(queue=behavior_queue, durable=True)
    channel.basic_consume(
        queue=behavior_queue,
        on_message_callback=consume_behavior_embedding,
        auto_ack=False,
    )

    return connection, channel


def main():
    connection = channel = None
    try:
        connection, channel = create_consumer()
        print("Started consuming...")
        channel.start_consuming()
    except KeyboardInterrupt:
        print("컨슈머를 중단합니다...")
    finally:
        if connection and connection.is_open:
            connection.close()
            print("연결이 종료되었습니다.")


if __name__ == "__main__":
    main()
