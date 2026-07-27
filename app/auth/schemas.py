from datetime import datetime
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


class User(BaseModel):
    id: int
    email: EmailStr
    role: Role
    is_blocked: bool
    created_at: datetime
    last_accessed: datetime | None


class UserCredentials(BaseModel):
    id: int
    role: Role
    password: str


class UserPayload(BaseModel):
    email: EmailStr
    password: str
    role: Role


class InsertTokenPayload(BaseModel):
    token_hash: str
    session_id: str
    user_id: int
    expires_at: datetime


class RefreshTokenPayload(BaseModel):
    user_id: int
    session_id: str
    is_valid: bool
