from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth.security import InvalidTokenError, decode_access_token
from app.core.config import settings
from app.core.permissions import ROLE_PERMISSIONS, Permission, Role

http_bearer = HTTPBearer()


class CurrentUser(BaseModel):
    id: int
    role: Role


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
) -> CurrentUser:
    token = credentials.credentials

    try:
        decoded_token = decode_access_token(token, public_key=settings.jwt.public_key)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid Token") from None

    return CurrentUser(id=int(decoded_token.sub), role=decoded_token.role)


def require_permission(permission: Permission):
    async def validator(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if permission not in ROLE_PERMISSIONS[user.role]:
            raise HTTPException(status_code=403)

        return user

    return validator
