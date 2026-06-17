import os

# Configuração do banco de testes:
# - Se DATABASE_URL já estiver definida (ex.: no pipeline de CI, onde o
#   PostgreSQL é provisionado em um passo dedicado), ela é usada diretamente.
# - Caso contrário, um container PostgreSQL efêmero é provisionado via
#   Testcontainers no início da sessão de testes e destruído ao final,
#   eliminando a necessidade de subir o banco manualmente em desenvolvimento.
_pg_container = None
if not os.environ.get("DATABASE_URL"):
    from testcontainers.postgres import PostgresContainer

    _pg_container = PostgresContainer(
        image="postgres:16-alpine",
        username="oficina",
        password="oficina",
        dbname="oficina_test",
        driver="psycopg",
    )
    _pg_container.start()
    os.environ["DATABASE_URL"] = _pg_container.get_connection_url()

os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "Admin@123"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.shared.database import get_engine
from app.shared.models import Base


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    if _pg_container is not None:
        _pg_container.stop()


@pytest.fixture(autouse=True)
def reset_database() -> None:
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "Admin@123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
