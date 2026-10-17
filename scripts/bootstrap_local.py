"""Cria no LocalStack as filas usadas pelo orquestrador (docker-compose).

Na AWS, filas, tópicos e assinaturas vêm do Terraform de cada serviço. Aqui,
o OS Service cria a sua fila de eventos (`os-saga-eventos`), assina nela os
tópicos de eventos dos quatro participantes e garante que as filas de
comandos deles existam (cada participante também as cria ao subir; criar de
novo é idempotente). Idempotente.

Uso: `python -m scripts.bootstrap_local`
"""

import json
import logging

import boto3

from app.shared.settings import settings

PARTICIPANT_TOPICS = ["estoque-eventos", "execucao-eventos", "orcamento-eventos", "pagamento-eventos"]


def _name(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def bootstrap() -> dict[str, object]:
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    sns = boto3.client("sns", region_name=settings.aws_region)

    for url in settings.command_queue_urls.values():
        if url:
            sqs.create_queue(QueueName=_name(url))

    events_queue = sqs.create_queue(QueueName=_name(settings.saga_events_queue_url))["QueueUrl"]
    events_arn = sqs.get_queue_attributes(QueueUrl=events_queue, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    topic_arns = [sns.create_topic(Name=name)["TopicArn"] for name in PARTICIPANT_TOPICS]
    sqs.set_queue_attributes(
        QueueUrl=events_queue,
        Attributes={
            "Policy": json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "sns.amazonaws.com"},
                            "Action": "sqs:SendMessage",
                            "Resource": events_arn,
                            "Condition": {"ArnEquals": {"aws:SourceArn": topic_arns}},
                        }
                    ],
                }
            )
        },
    )
    for topic_arn in topic_arns:
        sns.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=events_arn, Attributes={"RawMessageDelivery": "true"})
    return {"events_queue": events_queue, "subscribed_topics": topic_arns}


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("bootstrap").info("recursos locais prontos: %s", bootstrap())
