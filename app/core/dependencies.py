from typing import AsyncGenerator

import aiomysql

from .database import db_service


async def get_transaction() -> AsyncGenerator[aiomysql.Connection, None]:
    async with db_service.transaction() as conn:
        yield conn
