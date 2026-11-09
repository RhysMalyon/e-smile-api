import logging
from datetime import datetime
from typing import Any, List

import aiomysql
from aiomysql import Connection, IntegrityError
from pypika import FormatParameter, MySQLQuery, Table

from app.appointments.exceptions import AppointmentNotFoundError, SlotUnavailableError
from app.appointments.schemas import Appointment

logger = logging.getLogger(__name__)

appointments_table = Table("appointments", schema="e-smile")


async def create(conn: Connection, appointment_payload: dict[str, Any]) -> int:
    async with conn.cursor() as cur:
        columns = []
        values = []
        parameters = []

        for column, value in appointment_payload.items():
            columns.append(column)
            parameters.append(FormatParameter())
            values.append(value)

        query = MySQLQuery.into(appointments_table).columns(*columns).insert(*parameters)

        sql_string = query.get_sql()

        logger.info(sql_string)

        try:
            await cur.execute(sql_string, tuple(values))
        except IntegrityError as exc:
            # Not Duplicate entry (1062)
            if exc.args[0] != 1062:
                raise

            # The only unique column besides the id is `date`: the slot is already taken.
            logger.warning("Slot already booked.")
            raise SlotUnavailableError() from exc

        return cur.lastrowid


async def get_by_id(conn: Connection, id: int) -> Appointment:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(appointments_table)
            .select(appointments_table.star)
            .where(appointments_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (id,))
        result = await cur.fetchone()

        if result is None:
            raise AppointmentNotFoundError(f"Could not find appointment with ID {id}.")

        return Appointment.model_validate(result)


async def get_by_date_range(
    conn: Connection, range_start: datetime, range_end: datetime
) -> List[Appointment]:
    """Appointments with range_start <= date < range_end, earliest first."""
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(appointments_table)
            .select(appointments_table.star)
            .where(
                (appointments_table.date >= FormatParameter())
                & (appointments_table.date < FormatParameter())
            )
            .orderby(appointments_table.date)
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (range_start, range_end))
        results = await cur.fetchall()

        return [Appointment.model_validate(result) for result in results]


async def get_list(conn: Connection) -> List[Appointment]:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(appointments_table)
            .select(appointments_table.star)
            .orderby(appointments_table.date)
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string)
        results = await cur.fetchall()

        return [Appointment.model_validate(result) for result in results]


async def delete_by_id(conn: Connection, id: int) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.from_(appointments_table)
            .delete()
            .where(appointments_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (id,))

        if cur.rowcount == 0:
            raise AppointmentNotFoundError(f"Could not find appointment with ID {id}.")
