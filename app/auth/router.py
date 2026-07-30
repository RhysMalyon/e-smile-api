import logging

from aiomysql import Connection
from fastapi import APIRouter, Cookie, Depends, Response, status

from app.auth.exceptions import InvalidRefreshTokenError
from app.auth.schemas import LoginRequest, LoginResponse, RefreshResponse
from app.auth.security import hash_token
from app.auth.service import login as user_login, logout as user_logout, refresh as token_refresh
from app.core.config import settings
from app.core.dependencies import get_transaction

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response,
    credentials: LoginRequest,
    conn: Connection = Depends(get_transaction),
):
    email, password = credentials.email, credentials.password

    login_result = await user_login(conn, email, password)

    response.set_cookie(
        key="refresh_token",
        value=login_result.refresh_token,
        httponly=True,
        secure=settings.app.is_production,
        samesite="lax",
        path="/auth",
        max_age=settings.jwt.refresh_token_expire_seconds,
    )

    return LoginResponse(access_token=login_result.access_token, role=login_result.role)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None),
    conn: Connection = Depends(get_transaction),
):
    if refresh_token is None:
        raise InvalidRefreshTokenError("Missing refresh token")

    refresh_token_hash = hash_token(raw_token=refresh_token)

    token_pair = await token_refresh(conn, refresh_token_hash)

    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        httponly=True,
        secure=settings.app.is_production,
        samesite="lax",
        path="/auth",
        max_age=settings.jwt.refresh_token_expire_seconds,
    )

    return RefreshResponse(access_token=token_pair.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    conn: Connection = Depends(get_transaction),
):
    if refresh_token is not None:
        refresh_token_hash = hash_token(raw_token=refresh_token)

        await user_logout(conn, refresh_token_hash)

    response.delete_cookie(
        key="refresh_token",
        path="/auth",
    )
