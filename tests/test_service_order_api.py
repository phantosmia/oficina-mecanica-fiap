from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from jose import jwt

from tests.conftest import outbox
from tests.saga_helpers import ORDER_INPUT, Participants, make_orchestrator, open_order


def test_admin_routes_require_authentication(client: TestClient) -> None:
    for method, path in [("get", "/service-orders"), ("post", "/service-orders"), ("get", "/service-orders/1"), ("post", "/service-orders/1/deliver"), ("get", "/service-orders/1/saga")]:
        assert getattr(client, method)(path).status_code == 401


def test_opening_an_order_starts_the_saga_in_the_same_transaction(client: TestClient, admin_headers: dict[str, str]) -> None:
    order = open_order(client, admin_headers)

    assert order["status"] == "recebida"
    assert (order["items"], order["quote_total"]) == ([], 0)
    assert [(h["from_status"], h["to_status"], h["reason"]) for h in order["status_history"]] == [(None, "recebida", "OS aberta")]

    [command] = outbox()
    assert (command["destination"], command["type"], command["order_id"]) == ("execucao", "EnfileirarDiagnostico", order["id"])
    assert command["payload"] == {
        "problem_description": "Luz do óleo acendendo no painel",
        "vehicle": {"plate": "BRA2E19", "brand": "VW", "model": "Gol", "year": 2018},
    }
    saga = client.get(f"/service-orders/{order['id']}/saga", headers=admin_headers).json()
    assert (saga["state"], saga["waiting_for"], saga["saga_id"]) == ("ENFILEIRANDO_DIAGNOSTICO", "EnfileirarDiagnostico", command["saga_id"])
    assert saga["data"]["customer"] == {"name": "Maria Souza", "email": "maria@example.com"}


def test_opening_validates_input(client: TestClient, admin_headers: dict[str, str]) -> None:
    bad_document = {**ORDER_INPUT, "client": {**ORDER_INPUT["client"], "document_number": "123"}}
    assert client.post("/service-orders", json=bad_document, headers=admin_headers).status_code == 422
    assert client.post("/service-orders", json={**ORDER_INPUT, "problem_description": ""}, headers=admin_headers).status_code == 422
    assert outbox() == []


def test_items_from_the_diagnosis_appear_in_the_order(client: TestClient, admin_headers: dict[str, str]) -> None:
    order = open_order(client, admin_headers)
    Participants(make_orchestrator(), order["id"]).until_quote_approved()

    body = client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()
    assert body["status"] == "aguardando_pagamento"
    assert [(i["kind"], i["name"], i["quantity"], i["subtotal"]) for i in body["items"]] == [
        ("servico", "Troca de óleo", 1, 150.0), ("peca", "Óleo 5W30", 4, 180.0), ("peca", "Filtro de óleo", 1, 25.5),
    ]
    assert (body["labor_total"], body["parts_total"], body["quote_total"]) == (150.0, 205.5, 355.5)
    assert body["diagnosis_notes"] == "Óleo vencido e filtro saturado"
    assert body["approved_at"] is not None and body["quote_sent_at"] is not None
    assert [h["to_status"] for h in body["status_history"]] == ["recebida", "em_diagnostico", "aguardando_aprovacao", "aguardando_pagamento"]


def test_listing_prioritizes_active_orders(client: TestClient, admin_headers: dict[str, str]) -> None:
    first = open_order(client, admin_headers)
    second = open_order(client, admin_headers, vehicle={**ORDER_INPUT["vehicle"], "plate": "ABC1D23"})
    Participants(make_orchestrator(), second["id"]).until_quote_approved()

    listed = client.get("/service-orders", headers=admin_headers).json()
    assert [o["id"] for o in listed] == [second["id"], first["id"]]  # aguardando_pagamento antes de recebida


def test_deliver_only_after_finished(client: TestClient, admin_headers: dict[str, str]) -> None:
    order = open_order(client, admin_headers)
    assert client.post(f"/service-orders/{order['id']}/deliver", headers=admin_headers).status_code == 409

    participants = Participants(make_orchestrator(), order["id"])
    participants.until_paid()
    for event in ("BaixaConfirmada", "ReparoEnfileirado", "ReparoIniciado", "ExecucaoFinalizada"):
        participants.emit(event)

    delivered = client.post(f"/service-orders/{order['id']}/deliver", headers=admin_headers).json()
    assert delivered["status"] == "entregue" and delivered["delivered_at"] is not None
    assert client.get("/service-orders", headers=admin_headers).json() == []  # entregue sai da lista
    metrics = client.get("/service-orders/metrics/average-execution-time", headers=admin_headers).json()
    assert metrics["finished_orders"] == 1


def test_not_found(client: TestClient, admin_headers: dict[str, str]) -> None:
    for method, path in [("get", "/service-orders/999"), ("post", "/service-orders/999/deliver"), ("get", "/service-orders/999/saga"), ("post", "/service-orders/999/saga/retry")]:
        assert getattr(client, method)(path, headers=admin_headers).status_code == 404


def test_public_tracking_by_document_or_client_token(client: TestClient, admin_headers: dict[str, str]) -> None:
    order = open_order(client, admin_headers)
    Participants(make_orchestrator(), order["id"]).until_quote_approved()

    by_document = client.get(f"/service-orders/{order['id']}/tracking", params={"document_number": "52998224725"})
    assert by_document.status_code == 200
    assert by_document.json()["status"] == "aguardando_pagamento"
    assert len(by_document.json()["items"]) == 3
    assert [h["to_status"] for h in by_document.json()["status_history"]][-1] == "aguardando_pagamento"

    token = jwt.encode({"sub": "52998224725", "type": "client", "exp": datetime.now(UTC) + timedelta(minutes=5)}, "test-secret-key", algorithm="HS256")
    by_token = client.get(f"/service-orders/{order['id']}/tracking", headers={"Authorization": f"Bearer {token}"})
    assert by_token.json()["id"] == order["id"]

    assert client.get(f"/service-orders/{order['id']}/tracking", params={"document_number": "11144477735"}).status_code == 404
    assert client.get(f"/service-orders/{order['id']}/tracking").status_code == 422
