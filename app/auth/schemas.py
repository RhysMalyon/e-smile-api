from typing import Literal

from pydantic import BaseModel, EmailStr

from app.core.permissions import Role


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(TokenResponse):
    role: Role


class RefreshResponse(TokenResponse):
    pass


class JWTPayload(BaseModel):
    sub: str
    role: Role
    exp: int
    iat: int
