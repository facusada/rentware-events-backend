from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()
_MAX_BCRYPT_BYTES = 72


def _truncate_for_bcrypt(password: str) -> str:
    """Bcrypt only considers the first 72 bytes; truncate to avoid backend errors."""
    if not password:
        return password
    encoded = password.encode("utf-8")
    if len(encoded) <= _MAX_BCRYPT_BYTES:
        return password
    return encoded[:_MAX_BCRYPT_BYTES].decode("utf-8", errors="ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(_truncate_for_bcrypt(plain_password), hashed_password)
    except ValueError:
        # Avoid leaking backend errors (e.g., >72 bytes) as 500s
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(_truncate_for_bcrypt(password))


def create_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, role: str) -> str:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return create_token({"sub": subject, "role": role, "type": "access"}, expires_delta)


def create_refresh_token(subject: str) -> str:
    expires_delta = timedelta(minutes=settings.refresh_token_expire_minutes)
    return create_token({"sub": subject, "type": "refresh"}, expires_delta)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
