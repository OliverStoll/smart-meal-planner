"""Entrypoint for the cloud service (scheduler) to call the execution of task_syncer.
Listens to ${PORT} and calls the task_syncer methods on a schedule."""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import uvicorn

from messaging.bot import TelegramBot

bot = TelegramBot()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting bot thread...")
    thread = threading.Thread(target=bot.start_bot_persistent)
    thread.start()
    print("Bot thread started, FastAPI ready")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return JSONResponse(content={"message": "Started up"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"
    print(f"Test locally on http://localhost:{port}")
    uvicorn.run(app, host=host, port=port, log_level="critical", access_log=False)
