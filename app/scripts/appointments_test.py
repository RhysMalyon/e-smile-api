import asyncio
from datetime import datetime, timedelta

from app.appointments.exceptions import (
    AppointmentNotFoundError,
    InvalidDateRangeError,
    InvalidSlotError,
    SlotUnavailableError,
)
from app.appointments.repository import get_by_id
from app.appointments.scheduling import is_closed_day, shop_now
from app.appointments.schemas import CreateAppointmentRequest
from app.appointments.service import (
    book_appointment,
    delete_appointment,
    get_appointment_by_id,
    get_appointments,
    get_appointments_in_range,
    get_availability,
)
from app.core.database import db_service
from app.courses.exceptions import CourseNotFoundError
from app.courses.schemas import CreateCourseRequest, UpdateCourseRequest
from app.courses.service import create_course, update_course
from app.customers.schemas import CreateCustomerRequest
from app.customers.service import get_customer_by_email, get_customers
from app.time_off.exceptions import TimeOffConflictError
from app.time_off.schemas import CreateTimeOffRequest
from app.time_off.service import create_time_off


class RollbackTestTransaction(Exception):
    pass


def customer(tel: str = "090-1234-5678") -> CreateCustomerRequest:
    return CreateCustomerRequest(
        email="booking@example.com",
        first_name="太郎",
        last_name="山田",
        first_name_phonetic="タロウ",
        last_name_phonetic="ヤマダ",
        tel=tel,
    )


def next_open_day(days_ahead: int = 3) -> datetime:
    day = shop_now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    while is_closed_day(day.date()):
        day += timedelta(days=1)
    return day


async def expect_error(error_type, coro):
    try:
        await coro
    except error_type as exc:
        return exc
    raise AssertionError(f"Expected {error_type.__name__}")


async def main():
    await db_service.create_pool()

    try:
        async with db_service.transaction() as conn:
            day = next_open_day()

            def booking(hour: int, course_id: int, tel: str = "090-1234-5678"):
                return CreateAppointmentRequest(
                    course_id=course_id, date=day.replace(hour=hour), customer=customer(tel)
                )

            course = await create_course(
                conn, CreateCourseRequest(name="Appointments test course", length=30, price=5000)
            )

            # New customer is created; price is snapshotted; response hides admin fields.
            first = await book_appointment(conn, booking(10, course.id))
            assert first.price_at_booking == 5000 and first.date == day.replace(hour=10)
            assert not hasattr(first, "admin_notes") and not hasattr(first, "customer_id")
            stored = await get_by_id(conn, first.id)
            assert stored.admin_notes is None and stored.customer_id is not None

            # Later course price changes don't touch the snapshot.
            await update_course(conn, course.id, UpdateCourseRequest(price=9000))
            assert (await get_by_id(conn, first.id)).price_at_booking == 5000
            second = await book_appointment(conn, booking(11, course.id))
            assert second.price_at_booking == 9000

            # Same email reuses the customer; same number in another format adds no note.
            assert (await get_by_id(conn, second.id)).customer_id == stored.customer_id
            assert (await get_by_id(conn, second.id)).admin_notes is None
            await book_appointment(conn, booking(13, course.id, tel="09012345678"))
            assert (
                len([c for c in await get_customers(conn) if c.email == "booking@example.com"]) == 1
            )

            # A genuinely different number is noted, and the stored customer is not overwritten.
            mismatch = await book_appointment(conn, booking(14, course.id, tel="080-9999-0000"))
            notes = (await get_by_id(conn, mismatch.id)).admin_notes
            assert "090-1234-5678" in notes and "080-9999-0000" in notes
            assert (await get_customer_by_email(conn, "booking@example.com")).tel == "090-1234-5678"

            # Double booking -> 409 (the UNIQUE index), without a second row.
            await expect_error(SlotUnavailableError, book_appointment(conn, booking(10, course.id)))
            in_day = await get_appointments_in_range(conn, day, day + timedelta(days=1))
            assert [a.date.hour for a in in_day] == [10, 11, 13, 14]

            # Slots that can never be booked.
            for hour in (12, 9, 17):
                await expect_error(
                    InvalidSlotError, book_appointment(conn, booking(hour, course.id))
                )
            closed = day
            while not (closed.weekday() == 3):  # next Thursday
                closed += timedelta(days=1)
            await expect_error(
                InvalidSlotError,
                book_appointment(
                    conn,
                    CreateAppointmentRequest(
                        course_id=course.id, date=closed.replace(hour=10), customer=customer()
                    ),
                ),
            )
            past = next_open_day(days_ahead=-10)
            await expect_error(
                InvalidSlotError,
                book_appointment(
                    conn,
                    CreateAppointmentRequest(
                        course_id=course.id, date=past.replace(hour=10), customer=customer()
                    ),
                ),
            )

            # Missing and inactive courses look the same.
            await expect_error(CourseNotFoundError, book_appointment(conn, booking(15, 999999)))
            await update_course(conn, course.id, UpdateCourseRequest(is_active=False))
            await expect_error(CourseNotFoundError, book_appointment(conn, booking(15, course.id)))
            await update_course(conn, course.id, UpdateCourseRequest(is_active=True))

            # Time off blocks booking with the same error as a taken slot.
            await create_time_off(
                conn,
                CreateTimeOffRequest(start_at=day.replace(hour=15), end_at=day.replace(hour=17)),
            )
            await expect_error(SlotUnavailableError, book_appointment(conn, booking(15, course.id)))
            await expect_error(SlotUnavailableError, book_appointment(conn, booking(16, course.id)))

            # ...and time off can't be created over existing appointments (409 listing dates).
            exc = await expect_error(
                TimeOffConflictError,
                create_time_off(
                    conn,
                    CreateTimeOffRequest(start_at=day.replace(hour=9), end_at=day.replace(hour=12)),
                ),
            )
            assert day.replace(hour=10).isoformat() in str(exc)
            assert day.replace(hour=11).isoformat() in str(exc)
            # Touching the edge of an appointment is not a conflict: [12, 13) holds nothing.
            await create_time_off(
                conn,
                CreateTimeOffRequest(start_at=day.replace(hour=12), end_at=day.replace(hour=13)),
            )

            # --- Admin read / delete
            listed = [a.id for a in await get_appointments(conn)]
            assert first.id in listed and mismatch.id in listed
            assert (await get_appointment_by_id(conn, first.id)).id == first.id
            await expect_error(AppointmentNotFoundError, get_appointment_by_id(conn, 999999))

            # --- Availability: appointments (10, 11, 13, 14) + time off 12-13 and 15-17
            result = await get_availability(conn, day.date(), day.date())
            expected = [day.replace(hour=h).isoformat() for h in (10, 11, 12, 13, 14, 15, 16)]
            assert result == {day.date().isoformat(): expected}, result
            assert "T" in expected[0]

            # Multi-day time off: only the hours inside the requested range are returned.
            long_start = (day + timedelta(days=10)).replace(hour=10)
            long_end = (day + timedelta(days=13)).replace(hour=10)
            await create_time_off(conn, CreateTimeOffRequest(start_at=long_start, end_at=long_end))
            edge = await get_availability(conn, long_end.date(), long_end.date())
            assert edge == {
                long_end.date().isoformat(): [
                    long_end.replace(hour=h).isoformat() for h in range(10)
                ]
            }, edge
            start_day = await get_availability(conn, long_start.date(), long_start.date())
            assert [h[-8:-6] for h in start_day[long_start.date().isoformat()]] == [
                f"{h:02d}" for h in range(10, 24)
            ]

            # Every requested date is a key, empty when nothing is blocked; end is inclusive.
            quiet = await get_availability(
                conn, (day + timedelta(days=20)).date(), (day + timedelta(days=22)).date()
            )
            assert list(quiet.values()) == [[], [], []] and len(quiet) == 3

            # A block ending exactly at the range start does not leak in (strict overlap).
            touching = await get_availability(
                conn, long_end.date() + timedelta(days=1), long_end.date() + timedelta(days=1)
            )
            assert list(touching.values()) == [[]]

            await expect_error(
                InvalidDateRangeError,
                get_availability(conn, day.date(), day.date() - timedelta(days=1)),
            )
            await expect_error(
                InvalidDateRangeError,
                get_availability(conn, day.date(), day.date() + timedelta(days=93)),
            )
            await get_availability(
                conn, day.date(), day.date() + timedelta(days=92)
            )  # exactly 93 days is allowed

            # Deleting frees the slot, and the customer record stays.
            await delete_appointment(conn, mismatch.id)
            await expect_error(AppointmentNotFoundError, delete_appointment(conn, mismatch.id))
            await expect_error(AppointmentNotFoundError, get_appointment_by_id(conn, mismatch.id))
            assert (
                await get_customer_by_email(conn, "booking@example.com")
            ).id == stored.customer_id
            rebooked = await book_appointment(conn, booking(14, course.id))
            assert rebooked.date == day.replace(hour=14)

            print("All appointments checks passed.")
            raise RollbackTestTransaction()
    except RollbackTestTransaction:
        print("Rolled back.")
    finally:
        await db_service.close()


if __name__ == "__main__":
    asyncio.run(main())
