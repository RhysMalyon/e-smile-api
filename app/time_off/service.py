import logging
from datetime import datetime
from typing import List

from aiomysql import Connection

from app.time_off.exceptions import TimeOffConflictError, TimeOffRangeError
from app.time_off.repository import (
    create,
    delete_by_id,
    get_by_id,
    get_list,
    get_overlapping,
    update_by_id,
)
from app.time_off.schemas import CreateTimeOffRequest, TimeOff, UpdateTimeOffRequest

logger = logging.getLogger(__name__)


async def _ensure_no_appointment_conflicts(
    conn: Connection, start_at: datetime, end_at: datetime
) -> None:
    # Imported here, not at module level: appointments.service imports time_off.service, so a
    # top-level import in both directions would be circular.
    from app.appointments.service import get_appointments_in_range

    conflicts = await get_appointments_in_range(conn, start_at, end_at)

    if conflicts:
        dates = ", ".join(appointment.date.isoformat() for appointment in conflicts)
        raise TimeOffConflictError(f"Time off overlaps existing appointments: {dates}")


async def create_time_off(conn: Connection, request: CreateTimeOffRequest) -> TimeOff:
    payload = request.model_dump()

    await _ensure_no_appointment_conflicts(conn, payload["start_at"], payload["end_at"])

    time_off_id = await create(conn, time_off_payload=payload)

    return await get_by_id(conn, id=time_off_id)


async def update_time_off(conn: Connection, id: int, request: UpdateTimeOffRequest) -> TimeOff:
    payload = request.model_dump(exclude_unset=True)

    # The request can carry just one side of the range, so check the merged result.
    existing = await get_by_id(conn, id)
    start_at = payload.get("start_at", existing.start_at)
    end_at = payload.get("end_at", existing.end_at)

    if start_at >= end_at:
        raise TimeOffRangeError()

    await _ensure_no_appointment_conflicts(conn, start_at, end_at)

    updated_id = await update_by_id(conn, id, payload)

    return await get_by_id(conn, id=updated_id)


async def delete_time_off(conn: Connection, id: int) -> None:
    await delete_by_id(conn, id)


async def get_time_off_list(conn: Connection) -> List[TimeOff]:
    return await get_list(conn)


async def get_time_off_by_id(conn: Connection, id: int) -> TimeOff:
    return await get_by_id(conn, id)


async def get_time_off(conn: Connection, start: datetime, end: datetime) -> List[TimeOff]:
    """Time-off blocks overlapping [start, end). Used by appointments for availability."""
    return await get_overlapping(conn, start, end)
