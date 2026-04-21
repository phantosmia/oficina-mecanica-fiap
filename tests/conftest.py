from pathlib import Path
import os

TEST_DATABASE_PATH = Path(__file__).resolve().parent / "test_oficina_mecanica.db"
os.environ["DATABASE_PATH"] = str(TEST_DATABASE_PATH)
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "Admin@123"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.shared.database import init_database


@pytest.fixture(autouse=True)
def reset_database() -> None:
    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()
    init_database()
    yield
    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()


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
