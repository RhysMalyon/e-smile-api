import asyncio
from datetime import datetime

from app.core.database import db_service
from app.time_off.exceptions import TimeOffNotFoundError, TimeOffRangeError
from app.time_off.schemas import CreateTimeOffRequest, UpdateTimeOffRequest
from app.time_off.service import (
    create_time_off,
    delete_time_off,
    get_time_off,
    get_time_off_by_id,
    update_time_off,
)

class RollbackTestTransaction(Exception):
    pass


def dt(day: int, hour: int) -> datetime:
    return datetime(2026, 8, day, hour)


async def main():
    await db_service.create_pool()

    try:
        async with db_service.transaction() as conn:
            created = await create_time_off(
                conn, CreateTimeOffRequest(start_at=dt(3, 10), end_at=dt(3, 13))
            )
            assert created.start_at == dt(3, 10) and created.end_at == dt(3, 13)

            # Overlap is strict: touching edges don't count, one hour inside does.
            assert [t.id for t in await get_time_off(conn, dt(3, 13), dt(3, 15))] == []
            assert [t.id for t in await get_time_off(conn, dt(3, 8), dt(3, 10))] == []
            assert [t.id for t in await get_time_off(conn, dt(3, 12), dt(3, 14))] == [created.id]
            assert [t.id for t in await get_time_off(conn, dt(2, 0), dt(4, 0))] == [created.id]

            # PATCH with one side: merged with the stored value.
            updated = await update_time_off(
                conn, created.id, UpdateTimeOffRequest(end_at=dt(3, 15))
            )
            assert updated.start_at == dt(3, 10) and updated.end_at == dt(3, 15)

            # One-sided PATCH that would invert the range is a domain error, not a DB 500.
            try:
                await update_time_off(conn, created.id, UpdateTimeOffRequest(start_at=dt(3, 16)))
                raise AssertionError("Expected TimeOffRangeError")
            except TimeOffRangeError:
                pass

            await delete_time_off(conn, created.id)

            try:
                await get_time_off_by_id(conn, created.id)
                raise AssertionError("Expected TimeOffNotFoundError")
            except TimeOffNotFoundError:
                pass

            print("All time_off checks passed.")
            raise RollbackTestTransaction()
    except RollbackTestTransaction:
        print("Rolled back.")
    finally:
        await db_service.close()


if __name__ == "__main__":
    asyncio.run(main())
