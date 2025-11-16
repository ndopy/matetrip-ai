from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import asyncio
import threading
from contextlib import asynccontextmanager

import uvicorn

from app.routes import places, route, chat
from app.infra.consumer import create_consumer
from app.common.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """RabbitMQ의 Consumer를 백그라운드로 실행. FastAPI와 life를 같게하기"""
    global consumer_thread
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    consumer_thread.start()
    logger.info("Starting RabbitMQ consumer")
    try:
        yield
    finally:
        global rabbitmq_connection
        if rabbitmq_connection and rabbitmq_connection.is_open:
            rabbitmq_connection.close()
            logger.info("RabbitMQ connection closed")


app = FastAPI(lifespan=lifespan)

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",  # http://13.125.171.175:3001     # 프론트엔드 주소
        "http://localhost:3000",  # http://13.125.171.175:3000     # 백엔드 주소
    ],
    allow_credentials=True,  # 쿠키 전송 허용
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(places.router)
app.include_router(chat.router)
app.include_router(route.router)

# RabbitMQ consumer 관리
consumer_thread = None
rabbitmq_connection = None


def start_rabbitmq_consumer():
    """백그라운드 스레드에서 RabbitMQ consumer 실행"""
    global rabbitmq_connection
    try:
        connection, channel = create_consumer()
        rabbitmq_connection = connection
        logger.info("RabbibtMQ consumer started in background thread")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"RabbitMQ consumer error: {e}", exc_info=True)


@app.get("/")
async def root():
    return {"message": "Hello from matetrip-ai!"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="localhost", port=8000, reload=True)
