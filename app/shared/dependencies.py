from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.shared.security import JWTError, decode_access_token
from app.shared.settings import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_admin(token: str = Depends(oauth2_scheme)) -> dict[str, str]:
    unauthorized_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except JWTError as error:
        raise unauthorized_error from error

    username = payload.get("sub")
    if username != settings.admin_username:
        raise unauthorized_error

    return {"username": username}
