import json

import pika

params = pika.URLParameters("amqp://guest:guest@localhost:5672/")
connection = pika.BlockingConnection(params)
channel = connection.channel()

channel.queue_declare(queue="profile_embedding", durable=True)
channel.queue_declare(queue="behavior_embedding", durable=True)

profile_message = json.dumps({"user_id": "test-user-123"})
behavior_message = json.dumps(
    {
        "user_id": "test-user-123",
        "title": "테스트 장소",
        "address": "서울시 강남구 123",
        "longitude": 127.0276,
        "latitude": 37.4979,
    }
)

channel.basic_publish(
    exchange="",
    routing_key="profile_embedding",
    body=profile_message,
    properties=pika.BasicProperties(delivery_mode=2),
)
print(f"Sent profile message: {profile_message}")

channel.basic_publish(
    exchange="",
    routing_key="behavior_embedding",
    body=behavior_message,
    properties=pika.BasicProperties(delivery_mode=2),
)
print(f"Sent behavior message: {behavior_message}")

connection.close()
