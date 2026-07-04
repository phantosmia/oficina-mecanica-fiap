from fastapi.testclient import TestClient
from sqlalchemy import select

from app.shared.database import get_session
from app.shared.models import ServiceOrder


def _get_quote_token(order_id: int) -> str | None:
    with get_session() as session:
        return session.scalar(select(ServiceOrder.quote_token).where(ServiceOrder.id == order_id))


def test_admin_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/clients")
    assert response.status_code == 401


def test_full_service_order_flow(client: TestClient, admin_headers: dict[str, str]) -> None:
    service_response = client.post(
        "/services",
        json={
            "name": "Troca de óleo",
            "description": "Troca completa de óleo e filtro",
            "base_price": 150.0,
            "estimated_minutes": 45,
            "active": True,
        },
        headers=admin_headers,
    )
    assert service_response.status_code == 201
    service_id = service_response.json()["id"]

    part_response = client.post(
        "/parts",
        json={
            "name": "Óleo sintético 5W30",
            "sku": "OLEO-5W30",
            "description": "Lubrificante sintético",
            "unit_price": 50.0,
            "stock_quantity": 10,
            "min_stock_level": 2,
        },
        headers=admin_headers,
    )
    assert part_response.status_code == 201
    part_id = part_response.json()["id"]

    order_response = client.post(
        "/service-orders",
        json={
            "client": {
                "name": "Maria da Silva",
                "document_number": "529.982.247-25",
                "email": "maria@example.com",
                "phone": "+5511999999999",
            },
            "vehicle": {
                "plate": "ABC1234",
                "brand": "Fiat",
                "model": "Argo",
                "year": 2022,
            },
            "problem_description": "Revisão preventiva",
            "requested_services": [{"service_id": service_id, "quantity": 1}],
            "requested_parts": [{"part_id": part_id, "quantity": 2}],
        },
        headers=admin_headers,
    )
    assert order_response.status_code == 201
    created_order = order_response.json()
    assert created_order["status"] == "recebida"
    assert created_order["quote_total"] == 250.0
    order_id = created_order["id"]

    list_orders_response = client.get("/service-orders", headers=admin_headers)
    assert list_orders_response.status_code == 200
    assert len(list_orders_response.json()) == 1

    detail_response = client.get(f"/service-orders/{order_id}", headers=admin_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["client_name"] == "Maria da Silva"

    diagnosis_response = client.post(
        f"/service-orders/{order_id}/diagnosis",
        json={"diagnosis_notes": "Necessária revisão e troca de óleo."},
        headers=admin_headers,
    )
    assert diagnosis_response.status_code == 200
    assert diagnosis_response.json()["status"] == "em_diagnostico"

    quote_response = client.post(
        f"/service-orders/{order_id}/send-quote",
        json={"diagnosis_notes": "Orçamento enviado ao cliente."},
        headers=admin_headers,
    )
    assert quote_response.status_code == 200
    assert quote_response.json()["status"] == "aguardando_aprovacao"

    approval_response = client.post(f"/service-orders/{order_id}/approve", headers=admin_headers)
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "em_execucao"

    finish_response = client.post(f"/service-orders/{order_id}/finish", headers=admin_headers)
    assert finish_response.status_code == 200
    assert finish_response.json()["status"] == "finalizada"

    deliver_response = client.post(f"/service-orders/{order_id}/deliver", headers=admin_headers)
    assert deliver_response.status_code == 200
    assert deliver_response.json()["status"] == "entregue"

    tracking_response = client.get(
        f"/service-orders/{order_id}/tracking",
        params={"document_number": "529.982.247-25"},
    )
    assert tracking_response.status_code == 200
    assert tracking_response.json()["status"] == "entregue"

    part_detail = client.get(f"/parts/{part_id}", headers=admin_headers)
    assert part_detail.status_code == 200
    assert part_detail.json()["stock_quantity"] == 8

    average_response = client.get("/service-orders/metrics/average-execution-time", headers=admin_headers)
    assert average_response.status_code == 200
    assert average_response.json()["finished_orders"] == 1


def test_service_order_rejection_flow(client: TestClient, admin_headers: dict[str, str]) -> None:
    service_response = client.post(
        "/services",
        json={
            "name": "Revisão elétrica",
            "description": "Diagnóstico do sistema elétrico",
            "base_price": 180.0,
            "estimated_minutes": 60,
            "active": True,
        },
        headers=admin_headers,
    )
    assert service_response.status_code == 201
    service_id = service_response.json()["id"]

    order_response = client.post(
        "/service-orders",
        json={
            "client": {
                "name": "João Pereira",
                "document_number": "529.982.247-25",
                "email": "joao@example.com",
                "phone": "+5511777777777",
            },
            "vehicle": {
                "plate": "GHI1234",
                "brand": "Honda",
                "model": "Fit",
                "year": 2019,
            },
            "problem_description": "Pane intermitente",
            "requested_services": [{"service_id": service_id, "quantity": 1}],
            "requested_parts": [],
        },
        headers=admin_headers,
    )
    assert order_response.status_code == 201
    order_id = order_response.json()["id"]

    quote_response = client.post(
        f"/service-orders/{order_id}/send-quote",
        json={"diagnosis_notes": "Orçamento aguardando retorno do cliente."},
        headers=admin_headers,
    )
    assert quote_response.status_code == 200
    assert quote_response.json()["status"] == "aguardando_aprovacao"
    token = _get_quote_token(order_id)
    assert token is not None

    rejection_response = client.post(
        f"/service-orders/{order_id}/quote-response",
        json={"token": token, "decision": "reject"},
    )
    assert rejection_response.status_code == 200
    assert rejection_response.json()["status"] == "recusada"
    assert _get_quote_token(order_id) is None

    list_orders_response = client.get("/service-orders", headers=admin_headers)
    assert list_orders_response.status_code == 200
    listed_ids = {order["id"] for order in list_orders_response.json()}
    assert order_id not in listed_ids


def test_public_quote_response_approves_with_token(client: TestClient, admin_headers: dict[str, str]) -> None:
    service_response = client.post(
        "/services",
        json={
            "name": "Troca de pastilha",
            "description": "Substituição de pastilhas dianteiras",
            "base_price": 120.0,
            "estimated_minutes": 50,
            "active": True,
        },
        headers=admin_headers,
    )
    assert service_response.status_code == 201
    service_id = service_response.json()["id"]

    part_response = client.post(
        "/parts",
        json={
            "name": "Pastilha de freio",
            "sku": "PAST-FREIO",
            "description": "Jogo dianteiro",
            "unit_price": 90.0,
            "stock_quantity": 3,
            "min_stock_level": 1,
        },
        headers=admin_headers,
    )
    assert part_response.status_code == 201
    part_id = part_response.json()["id"]

    order_response = client.post(
        "/service-orders",
        json={
            "client": {
                "name": "Ana Costa",
                "document_number": "529.982.247-25",
                "email": "ana@example.com",
                "phone": "+5511666666666",
            },
            "vehicle": {
                "plate": "JKL1234",
                "brand": "Toyota",
                "model": "Corolla",
                "year": 2021,
            },
            "problem_description": "Ruído ao frear",
            "requested_services": [{"service_id": service_id, "quantity": 1}],
            "requested_parts": [{"part_id": part_id, "quantity": 1}],
        },
        headers=admin_headers,
    )
    assert order_response.status_code == 201
    order_id = order_response.json()["id"]

    quote_response = client.post(
        f"/service-orders/{order_id}/send-quote",
        json={"diagnosis_notes": "Pastilhas dianteiras no limite de desgaste."},
        headers=admin_headers,
    )
    assert quote_response.status_code == 200
    token = _get_quote_token(order_id)
    assert token is not None

    invalid_token_response = client.post(
        f"/service-orders/{order_id}/quote-response",
        json={"token": "invalid-token-value-with-enough-length", "decision": "approve"},
    )
    assert invalid_token_response.status_code == 403

    approval_response = client.post(
        f"/service-orders/{order_id}/quote-response",
        json={"token": token, "decision": "approve"},
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "em_execucao"

    assert _get_quote_token(order_id) is None

    reuse_response = client.post(
        f"/service-orders/{order_id}/quote-response",
        json={"token": token, "decision": "reject"},
    )
    assert reuse_response.status_code == 403

    part_detail = client.get(f"/parts/{part_id}", headers=admin_headers)
    assert part_detail.status_code == 200
    assert part_detail.json()["stock_quantity"] == 2


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

    vehicle_detail_response = client.get(f"/vehicles/{vehicle_id}", headers=admin_headers)
    assert vehicle_detail_response.status_code == 200

    vehicle_delete_response = client.delete(f"/vehicles/{vehicle_id}", headers=admin_headers)
    assert vehicle_delete_response.status_code == 204

    client_delete_response = client.delete(f"/clients/{created_client['id']}", headers=admin_headers)
    assert client_delete_response.status_code == 204


def test_services_and_parts_crud(client: TestClient, admin_headers: dict[str, str]) -> None:
    service_response = client.post(
        "/services",
        json={
            "name": "Alinhamento",
            "description": "Ajuste de direção",
            "base_price": 90.0,
            "estimated_minutes": 30,
            "active": True,
        },
        headers=admin_headers,
    )
    assert service_response.status_code == 201
    service_id = service_response.json()["id"]

    get_service_response = client.get(f"/services/{service_id}", headers=admin_headers)
    assert get_service_response.status_code == 200

    update_service_response = client.put(
        f"/services/{service_id}",
        json={"base_price": 95.0, "estimated_minutes": 35},
        headers=admin_headers,
    )
    assert update_service_response.status_code == 200
    assert update_service_response.json()["base_price"] == 95.0

    part_response = client.post(
        "/parts",
        json={
            "name": "Filtro de ar",
            "sku": "FILTRO-AR",
            "description": "Filtro do motor",
            "unit_price": 35.0,
            "stock_quantity": 6,
            "min_stock_level": 1,
        },
        headers=admin_headers,
    )
    assert part_response.status_code == 201
    part_id = part_response.json()["id"]

    update_part_response = client.put(
        f"/parts/{part_id}",
        json={"stock_quantity": 8},
        headers=admin_headers,
    )
    assert update_part_response.status_code == 200
    assert update_part_response.json()["stock_quantity"] == 8

    delete_part_response = client.delete(f"/parts/{part_id}", headers=admin_headers)
    assert delete_part_response.status_code == 204

    delete_service_response = client.delete(f"/services/{service_id}", headers=admin_headers)
    assert delete_service_response.status_code == 204


def test_service_order_error_paths(client: TestClient, admin_headers: dict[str, str]) -> None:
    service_response = client.post(
        "/services",
        json={
            "name": "Diagnóstico eletrônico",
            "description": "Leitura via scanner",
            "base_price": 120.0,
            "estimated_minutes": 20,
            "active": True,
        },
        headers=admin_headers,
    )
    service_id = service_response.json()["id"]

    part_response = client.post(
        "/parts",
        json={
            "name": "Sensor ABS",
            "sku": "ABS-001",
            "description": "Sensor de roda",
            "unit_price": 200.0,
            "stock_quantity": 1,
            "min_stock_level": 0,
        },
        headers=admin_headers,
    )
    part_id = part_response.json()["id"]

    insufficient_stock_response = client.post(
        "/service-orders",
        json={
            "client": {
                "name": "Carlos Lima",
                "document_number": "529.982.247-25",
                "email": "carlos@example.com",
                "phone": "+5511888888888",
            },
            "vehicle": {
                "plate": "DEF1234",
                "brand": "Chevrolet",
                "model": "Onix",
                "year": 2020,
            },
            "problem_description": "Falha no freio",
            "requested_services": [{"service_id": service_id, "quantity": 1}],
            "requested_parts": [{"part_id": part_id, "quantity": 2}],
        },
        headers=admin_headers,
    )
    assert insufficient_stock_response.status_code == 409

    valid_order_response = client.post(
        "/service-orders",
        json={
            "client": {
                "name": "Carlos Lima",
                "document_number": "529.982.247-25",
                "email": "carlos@example.com",
                "phone": "+5511888888888",
            },
            "vehicle": {
                "plate": "DEF1234",
                "brand": "Chevrolet",
                "model": "Onix",
                "year": 2020,
            },
            "problem_description": "Falha no freio",
            "requested_services": [{"service_id": service_id, "quantity": 1}],
            "requested_parts": [{"part_id": part_id, "quantity": 1}],
        },
        headers=admin_headers,
    )
    assert valid_order_response.status_code == 201
    order_id = valid_order_response.json()["id"]

    invalid_transition_response = client.post(f"/service-orders/{order_id}/approve", headers=admin_headers)
    assert invalid_transition_response.status_code == 409
