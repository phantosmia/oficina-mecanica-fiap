"""Mensageria do orquestrador com SQS simulado (moto)."""

import json

import boto3
from fastapi.testclient import TestClient

from app.messaging.dispatcher import Dispatcher, parse_body
from app.messaging.sqs_consumer import SqsConsumer
from app.shared.database import get_session_factory
from app.shared.events import Envelope
from app.shared.outbox import OutboxRelay, SqsCommandSender
from app.shared.settings import settings
from tests.saga_helpers import make_orchestrator, open_order

sqs = lambda: boto3.client("sqs", region_name="us-east-1")  # noqa: E731


def receive(queue_url: str) -> list[dict]:
    return sqs().receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, MessageAttributeNames=["All"]).get("Messages", [])


def test_relay_sends_each_command_to_its_participant_queue(client: TestClient, admin_headers: dict[str, str]) -> None:
    order = open_order(client, admin_headers)

    relay = OutboxRelay(get_session_factory(), SqsCommandSender(settings.command_queue_urls))
    assert relay.run_once() == 1
    assert relay.run_once() == 0

    [message] = receive(settings.command_queue_urls["execucao"])
    body = json.loads(message["Body"])
    assert (body["type"], body["order_id"]) == ("EnfileirarDiagnostico", order["id"])
    attributes = {k: v["StringValue"] for k, v in message["MessageAttributes"].items()}
    assert attributes == {"type": "EnfileirarDiagnostico", "saga_id": body["saga_id"], "correlation_id": body["saga_id"], "order_id": str(order["id"])}
    assert receive(settings.command_queue_urls["estoque"]) == []


def test_participant_events_arrive_through_the_subscribed_topic(client: TestClient, admin_headers: dict[str, str]) -> None:
    """A Execução publica no tópico dela; a fila os-saga-eventos (assinante) entrega ao orquestrador."""
    order = open_order(client, admin_headers)
    orchestrator = make_orchestrator()
    saga_id = orchestrator.get(order["id"]).id
    topic = boto3.client("sns", region_name="us-east-1").create_topic(Name="execucao-eventos")["TopicArn"]
    event = Envelope(type="DiagnosticoIniciado", payload={}, saga_id=saga_id, order_id=order["id"])
    boto3.client("sns", region_name="us-east-1").publish(TopicArn=topic, Message=json.dumps(event.to_dict()))

    consumer = SqsConsumer([settings.saga_events_queue_url], Dispatcher(orchestrator), wait_seconds=0)
    assert consumer.poll_once() == 1
    assert client.get(f"/service-orders/{order['id']}", headers=admin_headers).json()["status"] == "em_diagnostico"


def test_malformed_event_stays_in_queue(client: TestClient) -> None:
    sqs().send_message(QueueUrl=settings.saga_events_queue_url, MessageBody="{}")
    assert SqsConsumer([settings.saga_events_queue_url], Dispatcher(make_orchestrator()), wait_seconds=0).poll_once() == 0


def test_parse_body_unwraps_sns_notification() -> None:
    inner = Envelope(type="PecasReservadas", payload={"reservation_id": "r"}, saga_id="s", order_id=1).to_dict()
    assert parse_body(json.dumps({"Type": "Notification", "Message": json.dumps(inner)})).to_dict() == inner
