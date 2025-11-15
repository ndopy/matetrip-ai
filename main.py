from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    PruningContentFilter,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import asyncio

import uvicorn

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # 요청에 쿠키를 포함할 수 있도록 허용
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(places.router)
app.include_router(chat.router)
app.include_router(route.router)
app.include_router(planner.router)

@app.get("/")
async def root():
    return {"message": "Hello from matetrip-ai!"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="localhost", port=8000, reload=True)
