from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import asyncio
import threading
from contextlib import asynccontextmanager

import uvicorn

<<<<<<< HEAD
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
=======
from app.routes import places, route, chat, planner

app = FastAPI(
    title="MateTrip AI API",
    description="여행 동선 최적화 및 추천을 위한 AI API",
    version="0.1.0",
)

# 허용할 출처(origin) 목록
origins = [
    # 프론트엔드 개발 서버
    "http://localhost:3001",
    # TODO: 프론트엔드 프로덕션 배포 주소 추가
    # "https://your-production-frontend.com",
]
>>>>>>> 27b61ee05234ed2b38fd0b842be03aac34708b76

app.add_middleware(
    CORSMiddleware,
<<<<<<< HEAD
    allow_origins=[
        "http://localhost:3001",  # http://13.125.171.175:3001     # 프론트엔드 주소
        "http://localhost:3000",  # http://13.125.171.175:3000     # 백엔드 주소
    ],
    allow_credentials=True,  # 쿠키 전송 허용
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
=======
    allow_origins=origins,
    allow_credentials=True,  # 요청에 쿠키를 포함할 수 있도록 허용
    allow_methods=["*"],
    allow_headers=["*"],
>>>>>>> 27b61ee05234ed2b38fd0b842be03aac34708b76
)

app.include_router(places.router)
app.include_router(chat.router)
app.include_router(route.router)
<<<<<<< HEAD

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

=======
app.include_router(planner.router)
>>>>>>> 27b61ee05234ed2b38fd0b842be03aac34708b76

@app.get("/")
async def root():
    return {"message": "Hello from matetrip-ai!"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="localhost", port=8000, reload=True)
