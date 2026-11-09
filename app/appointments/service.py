import logging
import re
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from aiomysql import Connection

from app.appointments.exceptions import (
    InvalidDateRangeError,
    InvalidSlotError,
    SlotUnavailableError,
)
from app.appointments.repository import (
    create,
    delete_by_id,
    get_by_date_range,
    get_by_id,
    get_list,
)
from app.appointments.scheduling import is_bookable_slot, is_closed_day, shop_now
from app.appointments.schemas import (
    Appointment,
    CreateAppointmentRequest,
    PublicAppointmentResponse,
)
from app.courses.exceptions import CourseNotFoundError
from app.courses.service import get_course_by_id
from app.customers.exceptions import CustomerNotFoundError
from app.customers.service import create_customer, get_customer_by_email
from app.time_off.service import get_time_off

logger = logging.getLogger(__name__)


def _digits(tel: str) -> str:
    return re.sub(r"\D", "", tel)


def _tel_mismatch_note(stored_tel: str, submitted_tel: str) -> Optional[str]:
    # Compare digits only, so "090-1234-5678" vs "09012345678" isn't flagged as a mismatch.
    if _digits(stored_tel) == _digits(submitted_tel):
        return None

    return (
        f"Phone number differs from the customer record: record has {stored_tel}, "
        f"booking form had {submitted_tel}. Please follow up."
    )


async def book_appointment(
    conn: Connection, request: CreateAppointmentRequest
) -> PublicAppointmentResponse:
    slot = request.date

    if not is_bookable_slot(slot):
        raise InvalidSlotError("That time is outside opening hours or on a closed day.")

    if slot <= shop_now():
        raise InvalidSlotError("The appointment time must be in the future.")

    course = await get_course_by_id(conn, request.course_id)
    if not course.is_active:
        # Same response as a missing course, so inactive ones aren't discoverable.
        raise CourseNotFoundError()

    if await get_time_off(conn, slot, slot + timedelta(hours=1)):
        raise SlotUnavailableError()

    # Look up by email only. An existing customer is reused unchanged, never overwritten.
    admin_notes = None
    try:
        customer = await get_customer_by_email(conn, request.customer.email)
        admin_notes = _tel_mismatch_note(customer.tel, request.customer.tel)
    except CustomerNotFoundError:
        customer = await create_customer(conn, request.customer)

    # The UNIQUE index on `date` is the real double-booking guard: no check-then-insert race.
    appointment_id = await create(
        conn,
        appointment_payload={
            "course_id": course.id,
            "customer_id": customer.id,
            "date": slot,
            "price_at_booking": course.price,
            "admin_notes": admin_notes,
        },
    )

    appointment = await get_by_id(conn, appointment_id)

    return PublicAppointmentResponse.model_validate(appointment, from_attributes=True)


async def get_appointments_in_range(
    conn: Connection, start: datetime, end: datetime
) -> List[Appointment]:
    """Appointments with start <= date < end. Used by time_off (conflicts) and availability."""
    return await get_by_date_range(conn, start, end)


async def get_appointments(conn: Connection) -> List[Appointment]:
    return await get_list(conn)


async def get_appointment_by_id(conn: Connection, id: int) -> Appointment:
    return await get_by_id(conn, id)


async def delete_appointment(conn: Connection, id: int) -> None:
    await delete_by_id(conn, id)


# Public endpoints, so cap how much one request can ask for.
MAX_AVAILABILITY_DAYS = 93
MAX_CLOSED_DATES_DAYS = 366  # a year, so the front end can fetch it once; no DB involved


def _validate_range(start: date, end: date, max_days: int) -> None:
    if end < start:
        raise InvalidDateRangeError("end must not be before start.")

    if (end - start).days + 1 > max_days:
        raise InvalidDateRangeError(f"The range cannot be longer than {max_days} days.")


async def get_availability(conn: Connection, start: date, end: date) -> dict[str, list[str]]:
    """Blocked hours per day for start..end (both inclusive), as {"2026-08-01": ["2026-08-01T10:00:00"]}.

    Merges appointments and time off. Every requested date is a key, with [] when nothing is
    blocked. Closed days, lunch and opening hours are not included; they are rules, not bookings.
    """
    _validate_range(start, end, MAX_AVAILABILITY_DAYS)

    range_start = datetime.combine(start, time.min)
    range_end = datetime.combine(end + timedelta(days=1), time.min)

    blocked: set[datetime] = {
        appointment.date for appointment in await get_by_date_range(conn, range_start, range_end)
    }

    for block in await get_time_off(conn, range_start, range_end):
        # Only walk the hours inside the requested range, so a very long block stays cheap.
        # Hour-aligned DB values keep this aligned. `end_at` itself is excluded.
        hour = max(block.start_at, range_start)
        last = min(block.end_at, range_end)
        while hour < last:
            blocked.add(hour)
            hour += timedelta(hours=1)

    availability: dict[str, list[str]] = {}
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        availability[day.isoformat()] = sorted(
            hour.isoformat() for hour in blocked if hour.date() == day
        )

    return availability


async def get_closed_dates(start: date, end: date) -> list[str]:
    """Dates in start..end (inclusive) the shop is closed all day: weekly closed days and national
    holidays. Fully booked days and time off are deliberately not here; those stay selectable
    with their hours disabled (see get_availability).
    """
    _validate_range(start, end, MAX_CLOSED_DATES_DAYS)

    days = (start + timedelta(days=offset) for offset in range((end - start).days + 1))

    return [day.isoformat() for day in days if is_closed_day(day)]
