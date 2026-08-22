# RFC-0005: Escolha da ferramenta de monitoramento

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-08-22 |

## Contexto

A Fase 3 do Tech Challenge exige monitoramento da infraestrutura provisionada — necessidade já antecipada, mas deixada em aberto, pelo [RFC-0004](0004-escolha-do-api-gateway.md) e pela [ADR-0004](../adrs/0004-api-gateway-como-ponto-de-entrada.md) ("a disponibilidade da autenticação de clientes passa a depender de dois serviços gerenciados adicionais fora do EKS [...]; isso precisa entrar no escopo de latência, healthcheck e alertas exigido pelo monitoramento da Fase 3").

O sistema hoje é heterogêneo e distribuído em quatro repositórios/componentes com naturezas de execução bem diferentes: um cluster **EKS** rodando a aplicação FastAPI (containers de longa duração), duas **Functions Serverless** (Lambda de autenticação via CPF e Lambda Authorizer), um **API Gateway** gerenciado, e um banco **RDS PostgreSQL** gerenciado. Uma ferramenta de observabilidade única precisa cobrir esse conjunto — métricas de infraestrutura, APM (latência/erros por request), logs e alertas — sem exigir operar mais um componente com estado dentro do cluster, na mesma linha da preferência por **soluções gerenciadas/serverless** já seguida desde o [RFC-0004](0004-escolha-do-api-gateway.md).

O enunciado da Fase 3 cita **Datadog** e **New Relic** como opções de referência para essa etapa.

## Alternativas consideradas

- **Datadog**: plataforma de observabilidade completa (APM, infraestrutura, logs, RUM), com integrações prontas para EKS, RDS, Lambda e API Gateway. O modelo de cobrança (por host monitorado + por GB de log ingerido) escala mal para um ambiente de curso rodado em AWS Academy Lab: o trial gratuito é limitado a 14 dias, após os quais a maior parte dos recursos relevantes (APM, integração com Lambda) passa a exigir plano pago com cartão de crédito — algo que a conta do Lab não tem.
- **New Relic**: escolhido. Cobre o mesmo escopo (APM, infraestrutura, logs, alertas) com integrações nativas para Kubernetes/EKS, AWS Lambda (via layer/extension) e serviços AWS gerenciados como RDS e API Gateway (via a integração de nuvem AWS do New Relic, sobre a API do CloudWatch). Mantém um **free tier perene** (não um trial) de 100 GB/mês de ingestão de dados e um usuário "full platform" sem exigir cartão de crédito — suficiente para o volume de telemetria gerado por este projeto e compatível com a conta do AWS Academy Lab.
- **Prometheus + Grafana auto-hospedados**: descartada por ir contra a mesma direção já tomada no RFC-0004 (preferir gerenciado a operar mais um componente com estado no cluster) — exigiria manter armazenamento de métricas de longo prazo, scraping e alerting dentro do próprio EKS, além de não cobrir nativamente as Lambdas e o API Gateway sem exportadores adicionais.

## Decisão

Adotar o **New Relic** como ferramenta de monitoramento e observabilidade da Fase 3, cobrindo a aplicação principal (APM), o cluster EKS (infraestrutura), as duas Lambdas de autenticação e o RDS/API Gateway (via integrações nativas com CloudWatch). O detalhamento de como cada componente é instrumentado — onde o agente roda, como a license key é distribuída entre os repositórios — fica documentado na [ADR-0007](../adrs/0007-new-relic-como-plataforma-de-observabilidade.md).

## Consequências

- Resolve a lacuna de monitoramento identificada desde o RFC-0004/ADR-0004, com uma única ferramenta cobrindo containers, serverless e serviços gerenciados.
- Introduz um **novo fornecedor terceiro** (além da AWS, já assumida no RFC-0001) do qual o projeto passa a depender para observabilidade — mas sem acoplamento à lógica de negócio: trocar de ferramenta no futuro exige reinstrumentar, não reescrever a aplicação.
- Cada repositório que reporta telemetria precisa de uma **license key do New Relic** como configuração/segredo adicional — mais uma credencial para gerenciar, no mesmo padrão dos segredos já existentes (Secrets Manager, GitHub Actions secrets).
- O free tier tem um teto de ingestão (100 GB/mês); se o volume de telemetria dos ambientes de `homologacao`/`producao` ultrapassar esse limite durante o curso, é necessário revisar a decisão (reduzir amostragem/retenção ou considerar um plano pago).
