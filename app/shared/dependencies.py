from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from app.shared.security import JWTError, decode_access_token
from app.shared.settings import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# auto_error=False: ausência de header Authorization não deve virar 401 aqui —
# rotas que aceitam tanto o cliente autenticado por JWT quanto um mecanismo
# público existente (ex.: tracking por CPF na query, ver RFC-0003) tratam
# "nenhum token enviado" como um caso válido, delegando para o outro
# mecanismo. Um token enviado e inválido, por outro lado, sempre levanta 401.
_optional_bearer_scheme = HTTPBearer(auto_error=False)


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


def get_current_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer_scheme),
) -> dict[str, str] | None:
    """Claims do cliente autenticado via CPF, ou `None` se nenhum token foi enviado.

    O token é emitido pela Lambda de autenticação via CPF (repositório
    `oficina-mecanica-lambda-auth`, ver RFC-0004/ADR-0004/ADR-0005) — mesmo
    segredo e formato de claims (`sub`/`exp`) que `create_access_token` usa
    para o admin, mas com `sub` = CPF (dígitos, sem máscara) e uma claim
    extra `type: "client"`. Essa claim é o que diferencia um token de
    cliente de um token de admin: `get_current_admin` (acima) rejeitaria um
    token de cliente porque seu `sub` nunca é igual a `settings.admin_username`,
    e esta função rejeita o inverso — um token de admin não tem `type: "client"`.

    Diferente de `get_current_admin`, não exige um token (retorna `None`
    quando ausente); só levanta 401 se um token FOR enviado e for inválido
    ou não for do tipo "client".
    """
    if credentials is None:
        return None

    unauthorized_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as error:
        raise unauthorized_error from error

    if payload.get("type") != "client":
        raise unauthorized_error

    document_number = payload.get("sub")
    if not document_number:
        raise unauthorized_error

    return {"document_number": str(document_number), "client_id": str(payload.get("client_id", ""))}
