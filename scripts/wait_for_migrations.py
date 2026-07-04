#!/usr/bin/env python3
"""Wait until the database Alembic revision reaches head."""

import time
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.shared.settings import settings


def _get_current_heads() -> set[str]:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            return set(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()


def main() -> None:
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    expected_heads = set(script.get_heads())

    while True:
        current_heads = _get_current_heads()
        if current_heads == expected_heads:
            print("Banco de dados está na revisão head do Alembic.")
            return
        print(
            "Aguardando migrations do Alembic chegarem em head "
            f"(atual={sorted(current_heads)}, esperado={sorted(expected_heads)})..."
        )
        time.sleep(3)


if __name__ == "__main__":
    main()