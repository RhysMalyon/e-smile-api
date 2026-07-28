import logging

import aiomysql
from aiomysql import Connection
from pypika import FormatParameter, Table
from pypika import functions as fn
from pypika.dialects import MySQLQuery

from app.auth.schemas import (
    InsertTokenPayload,
    RefreshTokenPayload,
    User,
    UserCredentials,
    UserPayload,
    UserStatus,
)

logger = logging.getLogger(__name__)

refresh_tokens_table = Table("refresh_tokens", schema="e-smile")
users_table = Table("users", schema="e-smile")


# LOGIN
class UserNotFoundError(Exception):
    pass


async def find_user_by_email(conn: Connection, email: str) -> User:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(users_table)
            .select(users_table.star)
            .where(users_table.email == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (email,))
        result = await cur.fetchone()

        if result is None:
            raise UserNotFoundError("Could not find user.")

        return User(**result)


async def find_user_by_id(conn: Connection, user_id: int) -> UserStatus:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(users_table)
            .select(users_table.id, users_table.role, users_table.is_blocked)
            .where(users_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (user_id,))
        result = await cur.fetchone()

        if result is None:
            raise UserNotFoundError("Could not find user.")

        return UserStatus(**result)


async def find_user_credentials_by_email(conn: Connection, email: str) -> UserCredentials:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(users_table)
            .select(users_table.id, users_table.role, users_table.password)
            .where(users_table.email == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (email,))
        result = await cur.fetchone()

        if result is None:
            raise UserNotFoundError("Could not find user.")

        return UserCredentials(**result)


async def insert_user(conn: Connection, user_payload: UserPayload) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.into(users_table)
            .columns("email", "password", "role")
            .insert(FormatParameter(), FormatParameter(), FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(
            sql_string,
            (
                user_payload.email,
                user_payload.password,
                user_payload.role,
            ),
        )


async def update_last_accessed(conn: Connection, user_id: int) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.update(users_table)
            .set("last_accessed", fn.Now())
            .where(users_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (user_id,))


async def insert_refresh_token(conn: Connection, token_payload: InsertTokenPayload) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.into(refresh_tokens_table)
            .columns("token_hash", "session_id", "user_id", "expires_at")
            .insert(FormatParameter(), FormatParameter(), FormatParameter(), FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(
            sql_string,
            (
                token_payload.token_hash,
                token_payload.session_id,
                token_payload.user_id,
                token_payload.expires_at,
            ),
        )


# REFRESH
class RefreshTokenNotFoundError(Exception):
    pass


async def find_hashed_refresh_token(
    conn: Connection, refresh_token_hash: str
) -> RefreshTokenPayload:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(refresh_tokens_table)
            .select("user_id", "session_id", "is_valid")
            .where(refresh_tokens_table.token_hash == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (refresh_token_hash,))
        result = await cur.fetchone()

        if result is None:
            raise RefreshTokenNotFoundError("Could not find refresh token.")

        return RefreshTokenPayload(**result)


async def invalidate_session_tokens(conn: Connection, session_id: str) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.update(refresh_tokens_table)
            .set("is_valid", 0)
            .where(refresh_tokens_table.session_id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (session_id,))


async def invalidate_user_tokens(conn: Connection, user_id: int) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.update(refresh_tokens_table)
            .set("is_valid", 0)
            .where(refresh_tokens_table.user_id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (user_id,))


async def invalidate_refresh_token(conn: Connection, refresh_token_hash: str) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.update(refresh_tokens_table)
            .set("is_valid", 0)
            .where(refresh_tokens_table.token_hash == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (refresh_token_hash,))
