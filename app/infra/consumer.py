import os
import pika
import pika.exceptions

from infra.messaging_handler import (
    handle_behavior_embedding_test,
    handle_profile_embedding_test,
    parse_message,
)
from infra.rabbitmq_schema import (
    Behavior_embedding_req_message,
    Profile_embedding_req_message,
)


def consume_profile_embedding(channel, method, properties, body):
    message = parse_message(body, "profile_embedding", Profile_embedding_req_message)
    if message:
        try:
            handle_profile_embedding_test(message)
        except Exception as e:
            print(f"[profile_embedding] 처리 중 오류 발생: {e}")


def consume_behavior_embedding(channel, method, properties, body):
    message = parse_message(body, "behavior_embedding", Behavior_embedding_req_message)
    if message:
        try:
            handle_behavior_embedding_test(message)
        except Exception as e:
            print(f"[behavior_embedding] 처리 중 오류 발생: {e}")


def create_consumer():
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    params = pika.URLParameters(rabbitmq_url)
    params.blocked_connection_timeout = 300  # 5min

    try:
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
    except pika.exceptions.AMQPConnectionError as e:
        print(f"RabbitMQ 연결 실패: {e}")
        raise

    channel.queue_declare(queue="profile_embedding", durable=True)
    channel.basic_consume(
        queue="profile_embedding",
        on_message_callback=consume_profile_embedding,
        auto_ack=False,
    )

    channel.queue_declare(queue="behavior_embedding", durable=True)
    channel.basic_consume(
        queue="behavior_embedding",
        on_message_callback=consume_behavior_embedding,
        auto_ack=False,
    )

    return connection, channel


def main():
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
