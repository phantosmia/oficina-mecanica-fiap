# 2026-10-24 — Correlação de logs e traces pela saga

## O que foi pedido

Continuar o projeto. Pela ordem combinada para a Fase 4 (observabilidade → Postman → justificativa da saga no README → diagramas → vídeo → PDF), o próximo item era a observabilidade.

## O que já existia (auditoria)

- O agente New Relic já sobe nos 6 serviços quando `NEW_RELIC_LICENSE_KEY` está definida (`newrelic-admin run-program` no `docker-entrypoint.sh`, para API, worker e relay), configurado só por variáveis de ambiente.
- A propagação de *trace context* também já existia: os cabeçalhos são capturados ao gravar na outbox (`current_trace_headers`), viajam como `MessageAttributes` e o consumidor continua o trace (`consume_trace`, transação `Message/SQS`).
- **O que faltava no código**: `saga_id`/`order_id` nos logs estruturados.
- **O que faltava na configuração**: o secret `NEW_RELIC_LICENSE_KEY` só existe no OS Service. Nos outros 5 repositórios ele não está cadastrado (nem no repositório, nem em environment), então a APM não sobe neles na AWS.

## O que foi entregue

PRs iguais nos 6 repositórios (`feat/correlacao-logs-saga`): [fiap#49](https://github.com/phantosmia/oficina-mecanica-fiap/pull/49), [catalogo#4](https://github.com/phantosmia/oficina-mecanica-catalogo/pull/4), [estoque#4](https://github.com/phantosmia/oficina-mecanica-estoque/pull/4), [orcamento#4](https://github.com/phantosmia/oficina-mecanica-orcamento/pull/4), [pagamento#6](https://github.com/phantosmia/oficina-mecanica-pagamento/pull/6), [execucao#4](https://github.com/phantosmia/oficina-mecanica-execucao/pull/4).

- `saga_log_context(saga_id, order_id)` (`ContextVar`) em `app/shared/logging_config.py`; o `JSONFormatter` inclui os dois campos em cada linha emitida dentro do contexto.
- Consumidor SQS e relay da outbox processam cada mensagem dentro desse contexto; no OS Service, a verificação de prazos também.
- `consume_trace` grava `saga_id`/`order_id` como atributos customizados da transação, para achar no New Relic todos os traces de uma OS (`FROM Transaction SELECT * WHERE order_id = '42'`). Documentado em `docs/saga.md`.

## Decisões

- O valor também já aparece no texto da maioria das mensagens de log da saga. Isso importa porque o encaminhamento de logs do agente New Relic só leva o texto da mensagem, sem atributos extras (mesma razão do `request_id`, ver `logging_config.py`). Os campos JSON novos servem para o stdout/`kubectl logs` e para qualquer agregador que leia JSON.
- O módulo `logging_config.py` continua idêntico nos 6 serviços. Por isso o Catálogo, que não participa da saga, também recebeu a mudança.

## Pendente

- Redeployar os 5 serviços e conferir um trace distribuído no New Relic. O secret `NEW_RELIC_LICENSE_KEY` já foi cadastrado neles (environment `homologacao`). Como o New Relic só mostra a chave inteira quando ela é criada, a usuária criou uma license key nova (*Ingest - License*) na mesma conta; o OS Service continua com a dele. A cópia local está em `.new-relic`, excluída do git via `.git/info/exclude`.
