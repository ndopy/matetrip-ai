from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    PruningContentFilter,
)
from fastapi import FastAPI
import asyncio

import uvicorn

from app.routes import places


app = FastAPI()

app.include_router(places.router)


@app.get("/")
async def root():
    return {"message": "Hello from matetrip-ai!"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="localhost", port=8000, reload=True)
