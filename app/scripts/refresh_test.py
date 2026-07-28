import asyncio
import logging

from app.auth.repository import UserNotFoundError, find_user_by_email, insert_user
from app.auth.schemas import UserPayload
from app.auth.security import hash_password, hash_token
from app.auth.service import InvalidRefreshTokenError, login, refresh
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
                await find_user_by_email(conn, email)

            except UserNotFoundError:
                logger.warning("User not inserted.")

            login_result = await login(conn, email, password)

            refresh_token_hash = hash_token(login_result.refresh_token)
            refresh_result = await refresh(conn, refresh_token_hash)

            # Test rotated token raise
            try:
                await refresh(conn, refresh_token_hash)
            except InvalidRefreshTokenError:
                logger.info("Reuse correctly detected and rejected.")
            else:
                raise AssertionError("Expected InvalidRefreshTokenError but refresh() succeeded.")

            new_refresh_token_hash = hash_token(refresh_result.refresh_token)

            try:
                await refresh(conn, new_refresh_token_hash)
            except InvalidRefreshTokenError:
                print("Family-wide invalidation confirmed — new token also rejected.")
            else:
                raise AssertionError(
                    "Expected the rotated token's replacement to also be invalidated."
                )

            raise RollbackTestTransaction("Test complete — rolling back.")
    except RollbackTestTransaction as e:
        print(e)
    finally:
        await db_service.close()


if __name__ == "__main__":
    asyncio.run(main())
