import os
import sys
import logging
from pathlib import Path
from typing import Final

import pika
import pika.exceptions
from dotenv import load_dotenv

# Allow running this module directly via `python app/infra/consumer.py`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / ".env")

from app.infra.messaging_handler import (
    handle_behavior_embedding,
    handle_profile_embedding_test,
    parse_message,
)
from schemas.rabbitmq_schema import (
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def consume_profile_embedding(channel, method, properties, body):
    logger.info(f"[profile_embedding] 메시지 수신: {body[:100]}...")
    message = parse_message(body, profile_queue, ProfileEmbeddingReqMessage)
    if message:
        try:
            handle_profile_embedding_test(message)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"[profile_embedding] 메시지 처리 완료")
        except Exception as e:
            logger.warning(f"[profile_embedding] 처리 중 오류 발생: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    else:
        logger.warning(f"[profile_embedding] 메시지 파싱 실패")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def consume_behavior_embedding(channel, method, properties, body):
    logger.info(f"[behavior_embedding] 메시지 수신: {body[:100]}...")
    message = parse_message(body, behavior_queue, BehaviorEmbeddingReqMessage)
    if message:
        try:
            handle_behavior_embedding(message)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"[behavior_embedding] 메시지 처리 완료")
        except Exception as e:
            logger.warning(f"[behavior_embedding] 처리 중 오류 발생: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    else:
        logger.warning(f"[behavior_embedding] 메시지 파싱 실패")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def create_consumer():
    logger.info(f"RabbitMQ 연결 시도: {rabbitmq_url}")
    params = pika.URLParameters(rabbitmq_url)
    params.blocked_connection_timeout = 300  # 5min

    try:
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        logger.info("RabbitMQ 연결 성공")
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"RabbitMQ 연결 실패", exc_info=True)
        raise

    channel.queue_declare(queue=profile_queue, durable=True)
    logger.info(f"큐 선언 완료: {profile_queue}")
    channel.basic_consume(
        queue=profile_queue,
        on_message_callback=consume_profile_embedding,
        auto_ack=False,
    )

    channel.queue_declare(queue=behavior_queue, durable=True)
    logger.info(f"큐 선언 완료: {behavior_queue}")
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
        logger.info("Started consuming...")
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.warning("컨슈머를 중단합니다...")
    finally:
        if connection and connection.is_open:
            connection.close()
            logger.info("연결이 종료되었습니다.")


if __name__ == "__main__":
    main()
