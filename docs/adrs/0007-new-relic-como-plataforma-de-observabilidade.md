# ADR-0007: New Relic como plataforma de observabilidade

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-08-22 |

## Contexto

O [RFC-0005](../rfcs/0005-escolha-da-ferramenta-de-monitoramento.md) escolheu o New Relic como ferramenta de monitoramento da Fase 3, em vez do Datadog. Falta decidir **como** essa observabilidade é instrumentada num sistema distribuído em quatro repositórios com naturezas de execução diferentes: aplicação FastAPI de longa duração no EKS, duas Functions Serverless (Lambda), e dois serviços gerenciados da AWS (RDS, API Gateway) que não aceitam a instalação de um agente.

## Decisão

Um mecanismo de instrumentação por tipo de componente, em vez de um agente único genérico:

1. **Aplicação principal (`oficina-mecanica-fiap`)**: agente **New Relic APM para Python** (`newrelic`) instrumentando o processo FastAPI/uvicorn, para visibilidade de latência, erros e trace por rota — o mesmo tipo de dado que a [ADR-0004](0004-api-gateway-como-ponto-de-entrada.md) já previa como necessário para cobrir a autenticação via CPF. A license key chega ao pod pela mesma via já usada pelos demais segredos da aplicação (`oficina-mecanica-secret`/Secrets Manager → variável de ambiente), como uma nova chave `NEW_RELIC_LICENSE_KEY`, em vez de um mecanismo de configuração próprio.
2. **Cluster EKS (`oficina-mecanica-infra-kubernetes`)**: **New Relic Kubernetes integration** (chart `nri-bundle`), instalada via `helm_release` — mesmo padrão já usado neste repositório para o AWS Load Balancer Controller, o External Secrets Operator e o metrics-server — cobrindo métricas de nodes, pods e deployments independentemente do que roda dentro deles.
3. **Lambdas de autenticação (`oficina-mecanica-lambda-auth`)**: **New Relic Lambda layer** (extension), anexada às duas funções via Terraform, em vez de importar um SDK no código Python (`src/handler.py`). Evita acoplar a lógica de autenticação/autorização a um vendor de observabilidade específico — trocar de ferramenta no futuro não exige tocar em `src/`.
4. **RDS e API Gateway**: sem agente — cobertos pela **integração nativa AWS do New Relic** (CloudWatch Metric Streams), que já lê as métricas que esses dois serviços gerenciados publicam no CloudWatch por padrão.

## Alternativas consideradas

- **OpenTelemetry (OTLP) para todos os componentes, com o New Relic só como backend**: mais portável entre vendors — trocar de ferramenta de observabilidade no futuro exigiria só reapontar o exporter, não reinstrumentar. Descartada por exigir operar um Collector (mais um componente com estado) e configurar exporters manualmente em cada um dos quatro repositórios, sem necessidade real de portabilidade de vendor no momento atual do projeto.
- **Um único agente de infraestrutura, sem APM de aplicação**: mais simples de instalar (só o passo 2 acima), mas perde justamente o dado que motivou o RFC-0005 — latência e taxa de erro por rota da aplicação, que métricas de infraestrutura (CPU/memória dos pods) não mostram.
- **SDK do New Relic embutido no código da Lambda** (em vez da layer): mais controle sobre o que é instrumentado, mas acopla `src/handler.py` — hoje sem nenhuma dependência de observabilidade — a uma biblioteca de vendor específico, só pelo benefício de configuração que a layer já resolve sem mudança de código.

## Consequências

- Cada um dos quatro repositórios ganha uma dependência de configuração nova (license key do New Relic), na mesma linha dos segredos já existentes — não é um mecanismo de distribuição de segredo inédito no projeto.
- Ganha-se visibilidade unificada (um único painel) sobre um sistema que hoje só tem telemetria isolada por componente (CloudWatch Logs/Metrics de cada serviço, sem cruzamento). Rastrear um problema que atravessa Lambda → API Gateway → EKS → RDS deixa de exigir correlacionar logs manualmente em quatro lugares diferentes.
- A aplicação principal passa a ter uma dependência de biblioteca nova (`newrelic`) no ambiente de execução — precisa entrar no `pyproject.toml`/imagem Docker, e o agente adiciona alguma sobrecarga de CPU/memória ao processo (tipicamente pequena, mas real).
- A observabilidade do sistema passa a depender da disponibilidade do New Relic (SaaS terceiro): uma indisponibilidade do New Relic tira a visibilidade, mas não derruba a aplicação — os agentes reportam de forma assíncrona/best-effort e não bloqueiam requests em caso de falha no envio de telemetria.
