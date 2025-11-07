from fastapi import FastAPI

import uvicorn


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello from matetrip-ai!"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="localhost", port=8000)
