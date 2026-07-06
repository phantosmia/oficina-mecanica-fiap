from __future__ import annotations

import os
from typing import Any

from locust import HttpUser, between, task
from requests import Response


class OficinaMecanicaApiUser(HttpUser):
    wait_time = between(0.1, 0.8)

    def on_start(self) -> None:
        self.auth_headers: dict[str, str] = {}
        self._authenticate()

    def _authenticate(self) -> None:
        username = os.getenv("LOCUST_ADMIN_USERNAME", "admin")
        password = os.getenv("LOCUST_ADMIN_PASSWORD", "Admin@123")
        response = self.client.post(
            "/auth/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="POST /auth/token",
            catch_response=True,
        )
        with response:
            if response.status_code != 200:
                response.failure(f"login failed with status {response.status_code}")
                return

            payload: dict[str, Any] = response.json()
            access_token = payload.get("access_token")
            if not access_token:
                response.failure("login response did not include access_token")
                return

            self.auth_headers = {"Authorization": f"Bearer {access_token}"}
            response.success()

    @task(8)
    def healthcheck(self) -> None:
        self.client.get("/health", name="GET /health")

    @task(4)
    def database_status(self) -> None:
        self.client.get("/db-status", name="GET /db-status")

    @task(3)
    def list_clients(self) -> None:
        self._get_protected("/clients", "GET /clients")

    @task(3)
    def list_vehicles(self) -> None:
        self._get_protected("/vehicles", "GET /vehicles")

    @task(3)
    def list_service_orders(self) -> None:
        self._get_protected("/service-orders", "GET /service-orders")

    @task(2)
    def list_services(self) -> None:
        self._get_protected("/services", "GET /services")

    @task(2)
    def list_parts(self) -> None:
        self._get_protected("/parts", "GET /parts")

    def _get_protected(self, path: str, name: str) -> Response:
        return self.client.get(path, headers=self.auth_headers, name=name)
