import json
import logging

from fastapi.testclient import TestClient

from app.shared.logging_config import (
    REQUEST_ID_HEADER,
    JSONFormatter,
    _access_logger,
    _RequestIDFilter,
    configure_logging,
    get_request_id,
)


def test_request_id_gerado_quando_nao_informado(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER]


def test_request_id_informado_e_reaproveitado(client: TestClient) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: "meu-id-de-correlacao"})

    assert response.headers[REQUEST_ID_HEADER] == "meu-id-de-correlacao"


def test_requisicoes_diferentes_geram_request_ids_diferentes(client: TestClient) -> None:
    primeiro = client.get("/health").headers[REQUEST_ID_HEADER]
    segundo = client.get("/health").headers[REQUEST_ID_HEADER]

    assert primeiro != segundo


def test_get_request_id_fora_de_uma_requisicao_e_none() -> None:
    assert get_request_id() is None


def test_middleware_loga_request_id_no_texto_da_mensagem(client: TestClient, caplog) -> None:
    # O uvicorn.access roda fora do contexto assíncrono do middleware (o
    # ContextVar não propaga até lá — confirmado ao vivo, o campo request_id
    # simplesmente não aparecia no log daquela linha). E o forwarding
    # automático de log do agente New Relic só encaminha o texto puro da
    # mensagem, ignorando atributos customizados de LogRecord. Por isso este
    # log precisa ser emitido explicitamente pelo próprio middleware, com o
    # request_id já embutido no texto — não só como campo estruturado.
    #
    # `_access_logger.disabled = False` explícito abaixo porque o autouse
    # `reset_database` recria `alembic.config.Config("alembic.ini")` a cada
    # teste, e `Config()` aplica `logging.config.fileConfig(...)` do próprio
    # `alembic.ini` — que por padrão desabilita (`Logger.disabled = True`)
    # todo logger que já existia antes dela (`disable_existing_loggers=True`,
    # default do `fileConfig`). Como `app.request` já existe desde o import
    # do módulo, ele fica desabilitado depois de qualquer `reset_database`.
    # Isso é só do ambiente de teste — em produção o Alembic roda num Job
    # separado, nunca no processo da API.
    _access_logger.disabled = False
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health", headers={REQUEST_ID_HEADER: "meu-id-de-correlacao"})

    assert any(
        "request_id=meu-id-de-correlacao" in record.getMessage() and "path=/health" in record.getMessage()
        for record in caplog.records
    )
    assert response.status_code == 200


def test_json_formatter_produz_json_valido_com_campos_esperados() -> None:
    record = logging.LogRecord(
        name="app.teste",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="mensagem de teste",
        args=(),
        exc_info=None,
    )
    _RequestIDFilter().filter(record)

    formatted = JSONFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.teste"
    assert payload["message"] == "mensagem de teste"
    assert "timestamp" in payload
    # Fora de uma requisição (contexto de teste unitário), não há request_id.
    assert "request_id" not in payload


def test_json_formatter_inclui_request_id_quando_presente_no_record() -> None:
    record = logging.LogRecord(
        name="app.teste",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="mensagem correlacionada",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc-123"

    payload = json.loads(JSONFormatter().format(record))

    assert payload["request_id"] == "abc-123"


def test_configure_logging_aplica_json_formatter_no_root_e_no_uvicorn() -> None:
    # Chama configure_logging() explicitamente (em vez de só confiar no efeito
    # da importação de app.main, em conftest.py) porque o plugin de logging do
    # próprio pytest reconfigura os handlers do root logger entre testes —
    # checar aqui, logo após a chamada, evita depender dessa ordem.
    configure_logging("DEBUG")

    root_handlers = logging.getLogger().handlers
    assert any(isinstance(handler.formatter, JSONFormatter) for handler in root_handlers)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        assert uvicorn_logger.propagate is False
        assert any(isinstance(handler.formatter, JSONFormatter) for handler in uvicorn_logger.handlers)


def test_json_formatter_inclui_exception_quando_ha_exc_info() -> None:
    try:
        raise ValueError("falhou de propósito")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="app.teste",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="erro inesperado",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(JSONFormatter().format(record))

    assert "ValueError: falhou de propósito" in payload["exception"]
