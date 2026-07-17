from aiomysql import Connection

from app.auth.schemas import InsertTokenPayload, RefreshTokenPayload, User


# LOGIN
class UserNotFoundError(Exception):
    pass


async def find_user_by_email(conn: Connection, email: str) -> User:
    pass


async def update_last_accessed(conn: Connection, user_id: int) -> None:
    pass


async def insert_refresh_token(conn: Connection, token_payload: InsertTokenPayload) -> None:
    pass


# REFRESH
class RefreshTokenNotFoundError(Exception):
    pass


async def find_hashed_refresh_token(
    conn: Connection, refresh_token_hash: str
) -> RefreshTokenPayload:
    pass


async def rotate_refresh_token(conn: Connection, refresh_token_hash: str) -> None:
    pass


async def invalidate_session_tokens(conn: Connection, session_id: str) -> None:
    pass


# LOGOUT
async def invalidate_refresh_token_hash(conn: Connection, refresh_token_hash: str) -> None:
    pass
