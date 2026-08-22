"""Eventos customizados do New Relic (ADR-0007).

O agente APM (docker-entrypoint.sh) captura automaticamente latência e erro
por rota HTTP, mas não sabe nada sobre o domínio de negócio — quanto tempo
uma ordem de serviço passa em cada status é informação que só existe aqui,
na camada de use case. Sem esse evento customizado, o dashboard exigido
("tempo médio de execução por status: Diagnóstico, Execução, Finalização")
não tem como ser construído a partir de dados que a APM já coleta sozinha.

`record_custom_event` é seguro chamar mesmo sem o agente ativo (dev local,
testes) — vira um no-op, não levanta exceção nem loga erro.
"""

import newrelic.agent


def record_service_order_created(*, order_id: int, client_id: int, quote_total: float) -> None:
    newrelic.agent.record_custom_event(
        "ServiceOrderCreated",
        {"order_id": order_id, "client_id": client_id, "quote_total": quote_total},
    )


def record_service_order_status_changed(
    *,
    order_id: int,
    from_status: str,
    to_status: str,
    seconds_in_previous_status: float | None = None,
) -> None:
    params: dict[str, object] = {
        "order_id": order_id,
        "from_status": from_status,
        "to_status": to_status,
    }
    if seconds_in_previous_status is not None:
        params["seconds_in_previous_status"] = seconds_in_previous_status
    newrelic.agent.record_custom_event("ServiceOrderStatusChanged", params)
