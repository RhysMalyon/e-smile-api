import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import db_service
from .core.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):  # app unused, ignored
    await db_service.create_pool()

    try:
        yield
    finally:
        await db_service.close()


app = FastAPI(
    title=settings.app.title,
    version=settings.app.version,
    debug=settings.app.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_methods=settings.cors.allowed_methods,
    allow_headers=settings.cors.allowed_headers,
    expose_headers=settings.cors.expose_headers,
)


@app.get("/health")
async def health():
    try:
        return {"status": "ok"}
    except Exception as e:
        logger.error("Health check failed", exc_info=e)
        return {"status": "error"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app --reload",
        host=settings.app.host,
        port=settings.app.port,
        log_config=None,
        reload=settings.app.debug,
    )
