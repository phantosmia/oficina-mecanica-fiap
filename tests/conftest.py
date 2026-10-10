import os

# ── Banco de testes ──────────────────────────────────────────────────────────
# Cada teste recria o schema (alembic downgrade base + upgrade head), então a
# suíte só usa um banco existente se ele vier explicitamente em
# TEST_DATABASE_URL (de propósito não DATABASE_URL, que pode estar apontando
# para um banco de verdade no ambiente de quem roda). Sem ela, o
# Testcontainers sobe um PostgreSQL descartável para a sessão de testes.
_pg_container = None
if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
else:
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

_ACCOUNT = "123456789012"
_SQS = f"https://sqs.us-east-1.amazonaws.com/{_ACCOUNT}"
os.environ.update(
    {
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "Admin@123",
        "JWT_SECRET_KEY": "test-secret-key",
        # AWS simulada pelo moto
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_REGION": "us-east-1",
        "SAGA_EVENTS_QUEUE_URL": f"{_SQS}/os-saga-eventos",
        "ESTOQUE_COMMANDS_QUEUE_URL": f"{_SQS}/estoque-comandos",
        "EXECUCAO_COMMANDS_QUEUE_URL": f"{_SQS}/execucao-comandos",
        "ORCAMENTO_COMMANDS_QUEUE_URL": f"{_SQS}/orcamento-comandos",
        "PAGAMENTO_COMMANDS_QUEUE_URL": f"{_SQS}/pagamento-comandos",
        "WORKER_WAIT_SECONDS": "0",
        "SMTP_ENABLED": "false",
    }
)
os.environ.pop("AWS_ENDPOINT_URL", None)

from collections.abc import Iterator
from dataclasses import dataclass

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from moto import mock_aws
import pytest
from sqlalchemy import text

from app.main import app
from app.shared.database import get_engine
from app.shared.email import IEmailNotifier


def _alembic_config() -> Config:
    return Config("alembic.ini")


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    if _pg_container is not None:
        _pg_container.stop()


@pytest.fixture(autouse=True)
def reset_database() -> Iterator[None]:
    config = _alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def aws() -> Iterator[None]:
    with mock_aws():
        from scripts.bootstrap_local import bootstrap

        bootstrap()
        yield


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


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str


class FakeNotifier(IEmailNotifier):
    def __init__(self) -> None:
        self.sent: list[SentEmail] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append(SentEmail(to, subject, body))


def outbox() -> list[dict]:
    """Comandos gravados na outbox: [{"destination", "type", "payload", "saga_id", "order_id", ...}]."""
    with get_engine().connect() as connection:
        rows = connection.execute(text("SELECT destination, envelope FROM outbox_messages ORDER BY id"))
        return [{"destination": destination, **envelope} for destination, envelope in rows]
