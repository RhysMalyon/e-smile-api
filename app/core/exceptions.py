from fastapi.responses import JSONResponse


async def domain_exception_handler(_, exc):
    """Renders any domain exception that carries a `status_code` as {"detail": "<message>"}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )
