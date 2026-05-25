from functools import lru_cache
from pathlib import Path
import sqlite3

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.shared.models import Base
from app.shared.settings import settings


def get_database_path() -> Path:
    return Path(settings.database_path)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{database_path}",
        future=True,
        poolclass=NullPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: sqlite3.Connection, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


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