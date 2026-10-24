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

## Reprovisionamento de `homologacao` (mesma sessão)

A conta continuava a `340919830422`, mas tudo tinha sido apagado, inclusive o bucket do state do Terraform (mesmo caso de 2026-09-12).

1. **Backend** (`infra/backend`, local): state antigo guardado como `terraform.tfstate.stale-340919830422-20261024.bak`; plano de 6 recursos; apply rodado pela usuária. O `GetBucketObjectLockConfiguration` negado por SCP apareceu de novo: `terraform untaint aws_s3_bucket.terraform_state` e um segundo plano com `-refresh=false` para os 4 sub-recursos. O nome do bucket não mudou, então `TF_STATE_BUCKET` continuou valendo.
2. **Variables e secrets**: a role do cluster do Lab mudou de sufixo (`...FQnEMugyo9Bq` → `...9R2I44obTmLx`) e foi atualizada em `EKS_CLUSTER_ROLE_ARN`; as credenciais foram gravadas pela usuária com `scripts/atualiza-credenciais-aws.sh`.
3. **Workflows na ordem, todos na primeira tentativa**: banco (`workflow_dispatch`, 7m29s) → cluster (`workflow_dispatch`, 15m38s; dessa vez sem a corrida do `helm_release`) → Catálogo → Estoque, Orçamento, Pagamento e Execução em paralelo → OS Service → Lambda. Os serviços foram disparados com push da `main` na `homologacao` (avanço direto nos 5; merge da `main` no OS Service, conteúdo final idêntico).
4. **Seed**: Estoque antes do Catálogo, como em 2026-10-17.

## Verificação da observabilidade na AWS

- Os 6 serviços reportam ao New Relic (APM nas APIs; nos workers, transações `Message/SQS/sqs/<tipo>`).
- OS 1 aberta pela API pública e diagnosticada na Execução: a saga chegou a `AGUARDANDO_APROVACAO` (reserva no Estoque e orçamento gerado). Os logs JSON do OS Service e da Execução trazem os mesmos `saga_id`/`order_id`.
- **Um trace distribuído com 4 apps**: Execução (`complete_diagnosis`, HTTP) → Catálogo (`lookup_items`, REST) → worker do OS Service (`DiagnosticoConcluido`) → worker do Estoque (`ReservarPecas`) → OS Service (`PecasReservadas`), 55 spans.
- A consulta para Claude conferir isso pela API (NerdGraph) usa a User API key do `infra/newrelic-dashboards/terraform.tfvars` local (ignorado pelo git).

## Problema encontrado e corrigido (PRs abertos)

- **A primeira mensagem de cada worker recém-iniciado some do New Relic.** O agente descarta a transação que dispara o registro da aplicação (`startup_timeout` padrão 0). Na OS 1, `EnfileirarDiagnostico` e `GerarOrcamento` não apareceram, e o `OrcamentoGerado` ficou sem trace pai. Correção: `NEW_RELIC_STARTUP_TIMEOUT=10` no Deployment do worker (só nele; na API atrasaria a primeira requisição e as probes): [fiap#50](https://github.com/phantosmia/oficina-mecanica-fiap/pull/50), [estoque#5](https://github.com/phantosmia/oficina-mecanica-estoque/pull/5), [orcamento#5](https://github.com/phantosmia/oficina-mecanica-orcamento/pull/5), [pagamento#7](https://github.com/phantosmia/oficina-mecanica-pagamento/pull/7), [execucao#5](https://github.com/phantosmia/oficina-mecanica-execucao/pull/5).
- **A consulta de exemplo do `docs/saga.md` estava errada**: `order_id` chega como número (`order_id = 42`, sem aspas), e `trace.id` precisa de crases no NRQL. Corrigido no fiap#50.

## Verificação da correção (mesma sessão)

Depois do merge dos 5 PRs e do redeploy, a OS 2 foi aberta e diagnosticada com os workers recém-iniciados. As primeiras mensagens de cada um (`EnfileirarDiagnostico`, `DiagnosticoEnfileirado`, `GerarOrcamento`) apareceram no New Relic, todas com trace pai, e o trace do diagnóstico passou por 5 apps (78 spans), incluindo o Orçamento, que ficava de fora na OS 1.

## Pendente

- Cadastrar `NEW_RELIC_LICENSE_KEY` nos 5 repositórios dos serviços (environment `homologacao`), redeployar e conferir um trace distribuído no New Relic. A chave é a mesma do OS Service.
