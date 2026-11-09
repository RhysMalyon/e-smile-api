import logging
from datetime import date
from typing import List

from aiomysql import Connection
from fastapi import APIRouter, Depends, status

from app.appointments.schemas import (
    Appointment,
    CreateAppointmentRequest,
    PublicAppointmentResponse,
)
from app.appointments.service import book_appointment as book_appointment_service
from app.appointments.service import delete_appointment as delete_appointment_service
from app.appointments.service import get_appointment_by_id as get_appointment_by_id_service
from app.appointments.service import get_appointments as get_appointments_service
from app.appointments.service import get_availability as get_availability_service
from app.auth.dependencies import require_permission
from app.core.dependencies import get_transaction
from app.core.permissions import Permission

router = APIRouter()
# Separate router so main.py can mount it at /availability rather than /appointments/availability.
availability_router = APIRouter()
logger = logging.getLogger(__name__)


# Public: this is the booking form, so there is no permission dependency.
@router.post("", response_model=PublicAppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    request: CreateAppointmentRequest, conn: Connection = Depends(get_transaction)
):
    return await book_appointment_service(conn, request)


@router.get(
    "",
    dependencies=[Depends(require_permission(permission=Permission.APPOINTMENTS_READ))],
    response_model=List[Appointment],
)
async def get_appointments(conn: Connection = Depends(get_transaction)):
    return await get_appointments_service(conn)


@router.get(
    "/{appointment_id}",
    dependencies=[Depends(require_permission(permission=Permission.APPOINTMENTS_READ))],
    response_model=Appointment,
)
async def get_appointment(appointment_id: int, conn: Connection = Depends(get_transaction)):
    return await get_appointment_by_id_service(conn, appointment_id)


@router.delete(
    "/{appointment_id}",
    dependencies=[Depends(require_permission(permission=Permission.APPOINTMENTS_DELETE))],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_appointment(appointment_id: int, conn: Connection = Depends(get_transaction)):
    await delete_appointment_service(conn, appointment_id)


# Public: only reveals which hours are blocked, never who booked them.
@availability_router.get("", response_model=dict[str, list[str]])
async def get_availability(start: date, end: date, conn: Connection = Depends(get_transaction)):
    return await get_availability_service(conn, start, end)
