import logging
from datetime import datetime
from typing import Any, List

import aiomysql
from aiomysql import Connection
from pypika import FormatParameter, MySQLQuery, Table

from app.time_off.exceptions import TimeOffNotFoundError
from app.time_off.schemas import TimeOff

logger = logging.getLogger(__name__)

time_off_table = Table("time_off", schema="e-smile")


async def create(conn: Connection, time_off_payload: dict[str, Any]) -> int:
    async with conn.cursor() as cur:
        columns = []
        values = []
        parameters = []

        for column, value in time_off_payload.items():
            columns.append(column)
            parameters.append(FormatParameter())
            values.append(value)

        query = MySQLQuery.into(time_off_table).columns(*columns).insert(*parameters)

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, tuple(values))

        return cur.lastrowid


async def update_by_id(conn: Connection, id: int, update_time_off_payload: dict[str, Any]) -> int:
    async with conn.cursor() as cur:
        query = MySQLQuery.update(time_off_table)

        values = []

        for column, value in update_time_off_payload.items():
            query = query.set(column, FormatParameter())
            values.append(value)

        query = query.where(time_off_table.id == FormatParameter())
        values.append(id)

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, tuple(values))

        if cur.rowcount == 0:
            raise TimeOffNotFoundError(f"Could not find time off with ID {id}.")

        return id


async def delete_by_id(conn: Connection, id: int) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.from_(time_off_table).delete().where(time_off_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (id,))

        if cur.rowcount == 0:
            raise TimeOffNotFoundError(f"Could not find time off with ID {id}.")


async def get_list(conn: Connection) -> List[TimeOff]:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(time_off_table)
            .select(time_off_table.star)
            .orderby(time_off_table.start_at)
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string)
        results = await cur.fetchall()

        return [TimeOff.model_validate(result) for result in results]


async def get_by_id(conn: Connection, id: int) -> TimeOff:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(time_off_table)
            .select(time_off_table.star)
            .where(time_off_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (id,))
        result = await cur.fetchone()

        if result is None:
            raise TimeOffNotFoundError(f"Could not find time off with ID {id}.")

        return TimeOff.model_validate(result)


async def get_overlapping(
    conn: Connection, range_start: datetime, range_end: datetime
) -> List[TimeOff]:
    """Rows that strictly overlap [range_start, range_end). Touching edges don't count."""
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(time_off_table)
            .select(time_off_table.star)
            .where(
                (time_off_table.start_at < FormatParameter())
                & (time_off_table.end_at > FormatParameter())
            )
            .orderby(time_off_table.start_at)
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (range_end, range_start))
        results = await cur.fetchall()

        return [TimeOff.model_validate(result) for result in results]
