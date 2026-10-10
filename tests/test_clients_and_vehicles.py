"""Cadastro de clientes e veículos (inalterado na Fase 4)."""

from fastapi.testclient import TestClient


def test_client_and_vehicle_crud(client: TestClient, admin_headers: dict[str, str]) -> None:
    client_response = client.post(
        "/clients",
        json={
            "name": "Oficina Cliente",
            "document_number": "04.252.011/0001-10",
            "email": "cliente@empresa.com",
            "phone": "+551133333333",
        },
        headers=admin_headers,
    )
    assert client_response.status_code == 201
    created_client = client_response.json()
    assert created_client["status"] == "ativo"

    vehicle_response = client.post(
        "/vehicles",
        json={
            "client_id": created_client["id"],
            "brand": "Volkswagen",
            "model": "Gol",
            "year": 2021,
            "license_plate": "BRA2E19",
        },
        headers=admin_headers,
    )
    assert vehicle_response.status_code == 201
    vehicle_id = vehicle_response.json()["id"]

    update_response = client.put(
        f"/vehicles/{vehicle_id}",
        json={"model": "Polo"},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["model"] == "Polo"

    list_response = client.get("/clients", headers=admin_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    client_update_response = client.put(
        f"/clients/{created_client['id']}",
        json={"phone": "+551144444444"},
        headers=admin_headers,
    )
    assert client_update_response.status_code == 200
    assert client_update_response.json()["phone"] == "+551144444444"

    client_deactivate_response = client.put(
        f"/clients/{created_client['id']}",
        json={"status": "inativo"},
        headers=admin_headers,
    )
    assert client_deactivate_response.status_code == 200
    assert client_deactivate_response.json()["status"] == "inativo"

    client_reactivate_response = client.put(
        f"/clients/{created_client['id']}",
        json={"status": "ativo"},
        headers=admin_headers,
    )
    assert client_reactivate_response.status_code == 200
    assert client_reactivate_response.json()["status"] == "ativo"

    invalid_status_response = client.put(
        f"/clients/{created_client['id']}",
        json={"status": "banido"},
        headers=admin_headers,
    )
    assert invalid_status_response.status_code == 422

    vehicle_detail_response = client.get(f"/vehicles/{vehicle_id}", headers=admin_headers)
    assert vehicle_detail_response.status_code == 200

    vehicle_delete_response = client.delete(f"/vehicles/{vehicle_id}", headers=admin_headers)
    assert vehicle_delete_response.status_code == 204

    client_delete_response = client.delete(f"/clients/{created_client['id']}", headers=admin_headers)
    assert client_delete_response.status_code == 204




def test_db_status_counts(client: TestClient, admin_headers: dict[str, str]) -> None:
    from tests.saga_helpers import open_order

    open_order(client, admin_headers)
    body = client.get("/db-status").json()
    assert (body["clients"], body["vehicles"], body["service_orders"]) == (1, 1, 1)
    assert "services" not in body and "parts" not in body
    assert client.get("/").json()["message"].startswith("Oficina Mecânica FIAP")
