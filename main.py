from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import asyncio
import threading
from contextlib import asynccontextmanager
import uvicorn
from app.routes import places, route, chat, planner
from app.infra.consumer import create_consumer
from app.common.logger import logger

# RabbitMQ consumer 관리
consumer_thread = None
rabbitmq_connection = None
rabbitmq_channel = None


def start_rabbitmq_consumer():
    """백그라운드 스레드에서 RabbitMQ consumer 실행"""
    global rabbitmq_connection, rabbitmq_channel
    try:
        connection, channel = create_consumer()
        rabbitmq_connection = connection
        rabbitmq_channel = channel
        logger.info("RabbitMQ consumer started in background thread")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"RabbitMQ consumer error: {e}", exc_info=True)


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
        global rabbitmq_connection, rabbitmq_channel

        connection = rabbitmq_connection
        channel = rabbitmq_channel
        if not (connection and connection.is_open):
            return

        # 소비 루프 중단 → 커넥션 종료
        try:
            if channel and channel.is_open:
                connection.add_callback_threadsafe(channel.stop_consuming)
        except Exception as e:
            logger.warning(f"RabbitMQ stop_consuming failed: {e}", exc_info=True)

        try:
            connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.warning(f"RabbitMQ connection close failed: {e}", exc_info=True)


app = FastAPI(
    lifespan=lifespan,
    title="MateTrip AI API",
    description="여행 동선 최적화 및 추천을 위한 AI API",
    version="0.1.0",
    redirect_slashes=False,
)

# 허용할 출처(origin) 목록
origins = [
    # 프론트엔드 개발 서버
    "http://localhost:3001",
    "http://localhost:3000",
    "http://13.125.171.175:5173",
    "https://matetrip10.cloud",
    "https://ws.matetrip10.cloud",
]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,  # 쿠키 전송 허용
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
    allow_origins=origins,
)

app.include_router(places.router)
app.include_router(chat.router)
app.include_router(route.router)
app.include_router(planner.router)


@app.get("/")
async def root():
    print("제발")
    return {"message": "Hello from matetrip-ai!"}


if __name__ == "__main__":
    print("제발2")
    # Bind to all interfaces so external clients/containers can reach the API
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000, reload=True)
