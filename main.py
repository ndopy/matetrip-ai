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

app = FastAPI()

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",    #http://13.125.171.175:3001     # 프론트엔드 주소
        "http://localhost:3000",    #http://13.125.171.175:3000     # 백엔드 주소
    ],
    allow_credentials=True,          # 쿠키 전송 허용
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
