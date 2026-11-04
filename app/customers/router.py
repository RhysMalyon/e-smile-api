import logging
from typing import List

from aiomysql import Connection
from fastapi import APIRouter, Depends, status

from app.auth.dependencies import require_permission
from app.core.dependencies import get_transaction
from app.core.permissions import Permission
from app.customers.schemas import CreateCustomerRequest, Customer, UpdateCustomerRequest
from app.customers.service import create_customer as create_customer_service
from app.customers.service import delete_customer as delete_customer_service
from app.customers.service import get_customer_by_id as get_customer_by_id_service
from app.customers.service import get_customers as get_customers_service
from app.customers.service import update_customer as update_customer_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "",
    dependencies=[Depends(require_permission(permission=Permission.CUSTOMERS_WRITE))],
    response_model=Customer,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    request: CreateCustomerRequest, conn: Connection = Depends(get_transaction)
):
    return await create_customer_service(conn, request)


@router.get(
    "",
    dependencies=[Depends(require_permission(permission=Permission.CUSTOMERS_READ))],
    response_model=List[Customer],
)
async def get_customers(conn: Connection = Depends(get_transaction)):
    return await get_customers_service(conn)


@router.get(
    "/{customer_id}",
    dependencies=[Depends(require_permission(permission=Permission.CUSTOMERS_READ))],
    response_model=Customer,
)
async def get_customer(customer_id: int, conn: Connection = Depends(get_transaction)):
    return await get_customer_by_id_service(conn, customer_id)


@router.patch(
    "/{customer_id}",
    dependencies=[Depends(require_permission(permission=Permission.CUSTOMERS_WRITE))],
    response_model=Customer,
)
async def update_customer(
    customer_id: int, request: UpdateCustomerRequest, conn: Connection = Depends(get_transaction)
):
    return await update_customer_service(conn, customer_id, request)


@router.delete(
    "/{customer_id}",
    dependencies=[Depends(require_permission(permission=Permission.CUSTOMERS_DELETE))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_customer(customer_id: int, conn: Connection = Depends(get_transaction)):
    await delete_customer_service(conn, customer_id)
