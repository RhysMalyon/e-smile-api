import logging
from typing import List

from aiomysql import Connection
from fastapi import APIRouter, Depends, status

from app.auth.dependencies import require_permission
from app.core.dependencies import get_transaction
from app.core.permissions import Permission
from app.time_off.schemas import CreateTimeOffRequest, TimeOff, UpdateTimeOffRequest
from app.time_off.service import create_time_off as create_time_off_service
from app.time_off.service import delete_time_off as delete_time_off_service
from app.time_off.service import get_time_off_by_id as get_time_off_by_id_service
from app.time_off.service import get_time_off_list as get_time_off_list_service
from app.time_off.service import update_time_off as update_time_off_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "",
    dependencies=[Depends(require_permission(permission=Permission.TIME_OFF_WRITE))],
    response_model=TimeOff,
    status_code=status.HTTP_201_CREATED,
)
async def create_time_off(
    request: CreateTimeOffRequest, conn: Connection = Depends(get_transaction)
):
    return await create_time_off_service(conn, request)


@router.get(
    "",
    dependencies=[Depends(require_permission(permission=Permission.TIME_OFF_READ))],
    response_model=List[TimeOff],
)
async def get_time_off_list(conn: Connection = Depends(get_transaction)):
    return await get_time_off_list_service(conn)


@router.get(
    "/{time_off_id}",
    dependencies=[Depends(require_permission(permission=Permission.TIME_OFF_READ))],
    response_model=TimeOff,
)
async def get_time_off(time_off_id: int, conn: Connection = Depends(get_transaction)):
    return await get_time_off_by_id_service(conn, time_off_id)


@router.patch(
    "/{time_off_id}",
    dependencies=[Depends(require_permission(permission=Permission.TIME_OFF_WRITE))],
    response_model=TimeOff,
)
async def update_time_off(
    time_off_id: int, request: UpdateTimeOffRequest, conn: Connection = Depends(get_transaction)
):
    return await update_time_off_service(conn, time_off_id, request)


@router.delete(
    "/{time_off_id}",
    dependencies=[Depends(require_permission(permission=Permission.TIME_OFF_WRITE))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_time_off(time_off_id: int, conn: Connection = Depends(get_transaction)):
    await delete_time_off_service(conn, time_off_id)
