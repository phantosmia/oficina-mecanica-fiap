from functools import lru_cache
from urllib.parse import urlparse, urlunparse

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.shared.models import Base
from app.shared.settings import settings


def get_database_url() -> str:
    return settings.database_url


def get_safe_database_url() -> str:
    """Retorna a URL do banco sem expor a senha (para logs e endpoints públicos)."""
    parsed = urlparse(settings.database_url)
    if parsed.password is None:
        return settings.database_url
    netloc = parsed.hostname or ""
    if parsed.username:
        netloc = f"{parsed.username}:***@{netloc}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Session:
    return get_session_factory()()


def init_database() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_db():
    """FastAPI dependency that provides a SQLAlchemy session per request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()