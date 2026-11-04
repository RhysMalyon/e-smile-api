import logging
from typing import Any, List

import aiomysql
from aiomysql import Connection, IntegrityError
from pypika import FormatParameter, MySQLQuery, Table

from app.customers.exceptions import CustomerAlreadyExistsError, CustomerNotFoundError
from app.customers.schemas import Customer

logger = logging.getLogger(__name__)

customers_table = Table("customers", schema="e-smile")


async def create(conn: Connection, customer_payload: dict[str, Any]) -> int:
    async with conn.cursor() as cur:
        columns = []
        values = []
        parameters = []

        for column, value in customer_payload.items():
            columns.append(column)
            parameters.append(FormatParameter())
            values.append(value)

        query = MySQLQuery.into(customers_table).columns(*columns).insert(*parameters)

        sql_string = query.get_sql()

        logger.info(sql_string)

        try:
            await cur.execute(sql_string, tuple(values))
        except IntegrityError as exc:
            # Not Duplicate entry (1062)
            if exc.args[0] != 1062:
                raise

            logger.warning("Customer already exists.")
            raise CustomerAlreadyExistsError() from exc

        return cur.lastrowid


async def update_by_id(conn: Connection, id: int, update_customer_payload: dict[str, Any]) -> int:
    async with conn.cursor() as cur:
        query = MySQLQuery.update(customers_table)

        values = []

        for column, value in update_customer_payload.items():
            query = query.set(column, FormatParameter())
            values.append(value)

        query = query.where(customers_table.id == FormatParameter())
        values.append(id)

        sql_string = query.get_sql()

        logger.info(sql_string)

        try:
            await cur.execute(sql_string, tuple(values))
        except IntegrityError as exc:
            # Not Duplicate entry (1062)
            if exc.args[0] != 1062:
                raise

            logger.warning("Duplicate entry, could not update.")
            raise CustomerAlreadyExistsError() from exc

        if cur.rowcount == 0:
            raise CustomerNotFoundError(f"Could not find customer with ID {id}.")

        return id


async def delete_by_id(conn: Connection, id: int) -> None:
    async with conn.cursor() as cur:
        query = (
            MySQLQuery.from_(customers_table)
            .delete()
            .where(customers_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (id,))

        if cur.rowcount == 0:
            raise CustomerNotFoundError(f"Could not find customer with ID {id}.")


async def get_list(conn: Connection) -> List[Customer]:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(customers_table)
            .select(customers_table.star)
            .orderby(customers_table.id)
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string)
        results = await cur.fetchall()

        return [Customer.model_validate(result) for result in results]


async def get_by_id(conn: Connection, id: int) -> Customer:
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(customers_table)
            .select(customers_table.star)
            .where(customers_table.id == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (id,))
        result = await cur.fetchone()

        if result is None:
            raise CustomerNotFoundError(f"Could not find customer with ID {id}.")

        return Customer.model_validate(result)


async def get_by_email(conn: Connection, email: str) -> Customer:
    """Used by booking to resolve a customer. The column collation is case-insensitive."""
    async with conn.cursor(aiomysql.DictCursor) as cur:
        query = (
            MySQLQuery.from_(customers_table)
            .select(customers_table.star)
            .where(customers_table.email == FormatParameter())
        )

        sql_string = query.get_sql()

        logger.info(sql_string)

        await cur.execute(sql_string, (email,))
        result = await cur.fetchone()

        if result is None:
            raise CustomerNotFoundError("Could not find customer with that email.")

        return Customer.model_validate(result)
