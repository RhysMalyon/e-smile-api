from fastapi.responses import JSONResponse


async def auth_exception_handler(_, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


class InvalidCredentialsError(Exception):
    status_code = 401


class InvalidRefreshTokenError(Exception):
    status_code = 401
