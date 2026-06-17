#!/bin/bash
set -e

echo "Starting oficina-mecanica API container..."

# Aguardar PostgreSQL ficar disponível antes de iniciar a aplicação
echo "Aguardando PostgreSQL ficar pronto..."
poetry run python - <<'PY'
import os
import sys
import time

import psycopg

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
user = os.getenv("POSTGRES_USER", "oficina")
password = os.getenv("POSTGRES_PASSWORD", "oficina")
dbname = os.getenv("POSTGRES_DB", "oficina_mecanica")

deadline = time.time() + 60
last_error: Exception | None = None
while time.time() < deadline:
    try:
        with psycopg.connect(
            host=host, port=port, user=user, password=password, dbname=dbname, connect_timeout=3
        ):
            print(f"PostgreSQL disponível em {host}:{port}/{dbname}")
            sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(2)

print(f"Falha ao conectar no PostgreSQL: {last_error}", file=sys.stderr)
sys.exit(1)
PY

# Inicializar o schema do banco
echo "Inicializando banco de dados..."
poetry run python -c "from app.shared.database import init_database; init_database()"

# Popular o banco com dados de exemplo (idempotente)
echo "Populando banco com dados de exemplo..."
poetry run python scripts/populate_db.py

# Iniciar API
echo "Iniciando servidor da API..."
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000