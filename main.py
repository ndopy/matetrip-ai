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


# async def main():

#     browser_config = BrowserConfig(
#         headless=True,
#     )

#     content_filter = PruningContentFilter(remove_repeated_points=True)

#     CrawlerRunConfig(
#         browser_config=browser_config,
#         content_filter=content_filter,
#     )

#     async with AsyncWebCrawler() as crawler:
#         # result = await crawler.arun(url="https://www.example.com")
#         result = await crawler.arun(url="https://www.youtube.com/comment")
#         print(result.markdown.raw_markdown)


# if __name__ == "__main__":
# asyncio.run(main())


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="localhost", port=8000, reload=True)
