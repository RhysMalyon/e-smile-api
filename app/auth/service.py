import logging
import uuid
from datetime import UTC, datetime, timedelta

from aiomysql import Connection

from app.auth.repository import (
    UserNotFoundError,
    find_user_credentials_by_email,
    insert_refresh_token,
    update_last_accessed,
)
from app.auth.schemas import InsertTokenPayload, JWTPayload, LoginResponse
from app.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Invalid user verification flow
invalid_plain_password = "dummy"
invalid_hashed_password = hash_password(invalid_plain_password)


class InvalidCredentialsError(Exception):
    pass


async def login(conn: Connection, email: str, password: str) -> LoginResponse:
    try:
        user = await find_user_credentials_by_email(conn, email)
    except UserNotFoundError:
        # Simulate password verification flow for time consistency
        verify_password(plain=invalid_plain_password, hashed=invalid_hashed_password)

        logger.warning("User not found.")
        raise InvalidCredentialsError("Invalid user credentials.") from None

    now = datetime.now(UTC)

    is_valid_password = verify_password(plain=password, hashed=user.password)

    if not is_valid_password:
        logger.warning("Invalid password.")
        raise InvalidCredentialsError("Invalid user credentials.")

    # Access token
    access_token_expires_at = now + timedelta(seconds=settings.jwt.access_token_lifetime_seconds)
    payload = JWTPayload(
        sub=user.id,
        role=user.role,
        exp=int(access_token_expires_at.timestamp()),
        iat=int(now.timestamp()),
    )
    access_token = create_access_token(payload, settings.jwt.private_key)

    # Refresh token
    raw_refresh_token = generate_refresh_token()
    token_hash = hash_token(raw_token=raw_refresh_token)
    session_id = str(uuid.uuid4())
    refresh_token_expires_at = now + timedelta(seconds=settings.jwt.refresh_token_expire_seconds)

    await insert_refresh_token(
        conn,
        InsertTokenPayload(
            token_hash=token_hash,
            session_id=session_id,
            user_id=user.id,
            expires_at=refresh_token_expires_at,
        ),
    )

    await update_last_accessed(conn, user_id=user.id)

    return LoginResponse(access_token=access_token, role=user.role)
