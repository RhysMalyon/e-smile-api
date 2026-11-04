import asyncio

from app.core.database import db_service
from app.customers.exceptions import CustomerAlreadyExistsError, CustomerNotFoundError
from app.customers.schemas import CreateCustomerRequest, UpdateCustomerRequest
from app.customers.service import (
    create_customer,
    delete_customer,
    get_customer_by_email,
    get_customer_by_id,
    get_customers,
    update_customer,
)


class RollbackTestTransaction(Exception):
    pass


def make_request(email: str) -> CreateCustomerRequest:
    return CreateCustomerRequest(
        email=email,
        first_name="太郎",
        last_name="山田",
        first_name_phonetic="タロウ",
        last_name_phonetic="ヤマダ",
        tel="090-1234-5678",
    )


async def expect_error(error_type, coro):
    try:
        await coro
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


async def main():
    await db_service.create_pool()

    try:
        async with db_service.transaction() as conn:
            created = await create_customer(conn, make_request("taro@example.com"))

            # Kanji + furigana survive the round trip through MySQL (utf8mb4).
            fetched = await get_customer_by_id(conn, created.id)
            assert fetched.first_name == "太郎" and fetched.last_name == "山田"
            assert (
                fetched.first_name_phonetic == "タロウ" and fetched.last_name_phonetic == "ヤマダ"
            )

            # Lookup by email (case-insensitive collation).
            assert (await get_customer_by_email(conn, "TARO@example.com")).id == created.id
            await expect_error(
                CustomerNotFoundError, get_customer_by_email(conn, "nobody@example.com")
            )

            # Duplicate email -> domain error, not a raw IntegrityError.
            await expect_error(
                CustomerAlreadyExistsError, create_customer(conn, make_request("taro@example.com"))
            )

            # Partial update leaves the other fields alone.
            updated = await update_customer(
                conn, created.id, UpdateCustomerRequest(tel="080-0000-0000")
            )
            assert updated.tel == "080-0000-0000" and updated.first_name == "太郎"

            # Changing email to one that's taken -> 409 error.
            other = await create_customer(conn, make_request("hanako@example.com"))
            await expect_error(
                CustomerAlreadyExistsError,
                update_customer(conn, other.id, UpdateCustomerRequest(email="taro@example.com")),
            )

            assert {c.id for c in await get_customers(conn)} >= {created.id, other.id}

            await delete_customer(conn, created.id)
            await expect_error(CustomerNotFoundError, get_customer_by_id(conn, created.id))
            await expect_error(CustomerNotFoundError, delete_customer(conn, created.id))
            await expect_error(
                CustomerNotFoundError,
                update_customer(conn, created.id, UpdateCustomerRequest(tel="1")),
            )

            print("All customers checks passed.")
            raise RollbackTestTransaction()
    except RollbackTestTransaction:
        print("Rolled back.")
    finally:
        await db_service.close()


if __name__ == "__main__":
    asyncio.run(main())
