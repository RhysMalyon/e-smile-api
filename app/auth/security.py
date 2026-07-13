import hashlib
import logging
import secrets

import bcrypt
import jwt

from app.auth.schemas import JWTPayload

logger = logging.getLogger(__name__)


class InvalidTokenError(Exception):
    pass


def hash_password(plain: str) -> str:
    password_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password=password_bytes, salt=salt)

    return hashed_bytes.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    password_bytes = plain.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")

    return bcrypt.checkpw(password=password_bytes, hashed_password=hashed_bytes)


def hash_token(raw_token: str) -> str:
    hashed_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    return hashed_token


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(payload: JWTPayload, private_key: str) -> str:
    payload_dict = payload.model_dump()

    return jwt.encode(payload=payload_dict, key=private_key, algorithm="RS256")


def decode_access_token(token: str, public_key: str) -> JWTPayload:
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])

        return JWTPayload(**payload)
    except jwt.ExpiredSignatureError:
        logger.info("Token validation failed: expired")
        raise InvalidTokenError from None
    except jwt.InvalidSignatureError:
        logger.warning("Token validation failed: invalid signature")
        raise InvalidTokenError from None
    except jwt.PyJWTError as e:
        logger.warning(f"Token validation failed: {e}")
        raise InvalidTokenError from None
