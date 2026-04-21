from datetime import UTC, datetime, timedelta
import secrets

from jose import JWTError, jwt

from app.shared.settings import settings


def verify_password(plain_password: str, expected_password: str) -> bool:
    return secrets.compare_digest(plain_password, expected_password)


def authenticate_admin(username: str, password: str) -> bool:
    if username != settings.admin_username:
        return False
    return verify_password(password, settings.admin_password)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


__all__ = ["JWTError", "authenticate_admin", "create_access_token", "decode_access_token"]
