import logging
from typing import List

from aiomysql import Connection

from app.customers.repository import (
    create,
    delete_by_id,
    get_by_email,
    get_by_id,
    get_list,
    update_by_id,
)
from app.customers.schemas import CreateCustomerRequest, Customer, UpdateCustomerRequest

logger = logging.getLogger(__name__)


async def create_customer(conn: Connection, request: CreateCustomerRequest) -> Customer:
    customer_id = await create(conn, customer_payload=request.model_dump())

    return await get_by_id(conn, id=customer_id)


async def update_customer(conn: Connection, id: int, request: UpdateCustomerRequest) -> Customer:
    updated_customer_id = await update_by_id(conn, id, request.model_dump(exclude_unset=True))

    return await get_by_id(conn, id=updated_customer_id)


async def delete_customer(conn: Connection, id: int) -> None:
    await delete_by_id(conn, id)


async def get_customers(conn: Connection) -> List[Customer]:
    return await get_list(conn)


async def get_customer_by_id(conn: Connection, id: int) -> Customer:
    return await get_by_id(conn, id)


async def get_customer_by_email(conn: Connection, email: str) -> Customer:
    """Used by appointments during booking; raises CustomerNotFoundError when there's no match."""
    return await get_by_email(conn, email)
