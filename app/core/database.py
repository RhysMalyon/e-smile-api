import asyncio
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncGenerator, cast

import aiomysql

from .config import Settings, settings

logger = logging.getLogger(__name__)

db_connection_ctx: ContextVar[aiomysql.Connection | None] = ContextVar(
    "db_connection", default=None
)


class DatabaseService:
    def __init__(self, settings: Settings):
        self.config = settings
        self.pool: aiomysql.Pool | None = None
        self._lock = asyncio.Lock()

    async def create_pool(self):
        async with self._lock:
            if not self.pool:
                settings = self.config.db

                try:
                    self.pool = await aiomysql.create_pool(
                        host=settings.host,
                        port=settings.port,
                        user=settings.user,
                        password=settings.password,
                        db=settings.database,
                        # Handle commit/rollback in dedicated handler
                        autocommit=False,
                        # Set the session timezone to UTC
                        init_command="SET SESSION time_zone='+00:00'",
                    )

                    logger.info("Database pool created.")
                except Exception as e:
                    logger.error(f"Error creating database pool: {e}")
                    raise

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiomysql.Connection, None]:
        existing_conn = db_connection_ctx.get()

        if existing_conn is not None:
            raise RuntimeError("Connection already present in context")

        async with self.pool.acquire() as conn:
            conn = cast(aiomysql.Connection, conn)

            token = db_connection_ctx.set(conn)

            try:
                # Start transaction
                await conn.begin()
                # Provide connection to caller
                yield conn
                # Commit if no exceptions
                await conn.commit()
            except Exception as e:
                # Rollback on any error
                await conn.rollback()
                # Re-raise exception
                raise e
            finally:
                db_connection_ctx.reset(token)

    async def close(self):
        if self.pool is not None:
            await self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            logger.info("DB connection pool closed.")


db_service = DatabaseService(settings=settings.db)
