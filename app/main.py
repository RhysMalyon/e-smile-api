import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .appointments.exceptions import (
    AppointmentNotFoundError,
    InvalidDateRangeError,
    InvalidSlotError,
    SlotUnavailableError,
)
from .appointments.router import availability_router
from .appointments.router import router as appointments_router
from .auth.exceptions import InvalidCredentialsError, InvalidRefreshTokenError
from .auth.router import router as auth_router
from .core.config import settings
from .core.database import db_service
from .core.exceptions import domain_exception_handler
from .core.logging_config import setup_logging
from .courses.exceptions import CourseAlreadyExistsError, CourseNotFoundError
from .courses.router import router as courses_router
from .customers.exceptions import CustomerAlreadyExistsError, CustomerNotFoundError
from .customers.router import router as customers_router
from .time_off.exceptions import TimeOffConflictError, TimeOffNotFoundError, TimeOffRangeError
from .time_off.router import router as time_off_router

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
app.add_exception_handler(InvalidCredentialsError, domain_exception_handler)
app.add_exception_handler(InvalidRefreshTokenError, domain_exception_handler)
app.add_exception_handler(CourseNotFoundError, domain_exception_handler)
app.add_exception_handler(CourseAlreadyExistsError, domain_exception_handler)
app.add_exception_handler(AppointmentNotFoundError, domain_exception_handler)
app.add_exception_handler(InvalidSlotError, domain_exception_handler)
app.add_exception_handler(InvalidDateRangeError, domain_exception_handler)
app.add_exception_handler(SlotUnavailableError, domain_exception_handler)
app.add_exception_handler(CustomerNotFoundError, domain_exception_handler)
app.add_exception_handler(CustomerAlreadyExistsError, domain_exception_handler)
app.add_exception_handler(TimeOffNotFoundError, domain_exception_handler)
app.add_exception_handler(TimeOffRangeError, domain_exception_handler)
app.add_exception_handler(TimeOffConflictError, domain_exception_handler)


# Routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(courses_router, prefix="/courses", tags=["courses"])
app.include_router(appointments_router, prefix="/appointments", tags=["appointments"])
app.include_router(availability_router, prefix="/availability", tags=["availability"])
app.include_router(customers_router, prefix="/customers", tags=["customers"])
app.include_router(time_off_router, prefix="/time-off", tags=["time-off"])

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        log_config=None,
        reload=settings.app.debug,
    )
