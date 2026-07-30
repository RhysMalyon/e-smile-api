import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    auth_exception_handler,
)
from .auth.router import router as auth_router
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

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allowed_methods,
    allow_headers=settings.cors.allowed_headers,
    expose_headers=settings.cors.expose_headers,
)

# Exception Handlers
app.add_exception_handler(InvalidCredentialsError, auth_exception_handler)
app.add_exception_handler(InvalidRefreshTokenError, auth_exception_handler)


# Routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        log_config=None,
        reload=settings.app.debug,
    )
