import asyncio
import logging

from app.auth.repository import UserNotFoundError, find_user_by_email, insert_user
from app.auth.schemas import UserPayload
from app.auth.security import hash_password
from app.auth.service import login
from app.core.database import db_service
from app.core.permissions import Role

logger = logging.getLogger(__name__)


class RollbackTestTransaction(Exception):
    pass


async def main():
    await db_service.create_pool()

    try:
        async with db_service.transaction() as conn:
            email = "test@example.com"
            password = "known_password"
            hashed_password = hash_password(password)

            user_payload = UserPayload(email=email, password=hashed_password, role=Role.STAFF)

            await insert_user(conn, user_payload)

            try:
                user = await find_user_by_email(conn, email)

                print(user)
            except UserNotFoundError:
                logger.warning("User not inserted.")

            login_response = await login(conn, email, password)
            print(login_response)

            raise RollbackTestTransaction("Test complete — rolling back.")
    except RollbackTestTransaction as e:
        print(e)
    finally:
        await db_service.close()


if __name__ == "__main__":
    asyncio.run(main())
