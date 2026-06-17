import os

# Banco de testes (PostgreSQL). Pode ser sobrescrito via DATABASE_URL no ambiente.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://oficina:oficina@localhost:5432/oficina_test",
)
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "Admin@123"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.shared.database import get_engine
from app.shared.models import Base


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
