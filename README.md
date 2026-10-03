# oficina-mecanica-fiap

MVP do back-end do Sistema Integrado de Atendimento e Execução de Serviços de uma oficina mecânica, desenvolvido em FastAPI com PostgreSQL, autenticação JWT, migrations Alembic, Docker, Kubernetes, Terraform AWS/EKS e pipeline GitHub Actions.

## Índice

- [Documentação complementar](#documentação-complementar)
- [Repositórios do projeto](#repositórios-do-projeto)
- [Visão geral](#visão-geral)
- [Stack](#stack)
- [Como rodar rápido](#como-rodar-rápido)
- [Kubernetes e AWS](#kubernetes-e-aws)
- [Testes e qualidade](#testes-e-qualidade)
- [Observações](#observações)

## Documentação complementar

Os detalhes foram separados em artigos complementares para manter este README enxuto:

| Artigo | Conteúdo |
|---|---|
| [Arquitetura](docs/arquitetura.md) | Clean Architecture, estrutura de pastas, PostgreSQL, princípios aplicados e diagramas (ER, componentes C4, infraestrutura AWS, dependência entre repositórios, fluxo de deploy e sequência) |
| [Regras de negócio](docs/regras-negocio.md) | Fluxo da OS, status, cálculo de orçamento e baixa de estoque |
| [Execução local](docs/execucao-local.md) | Mise, Poetry, Docker Compose, migrations e dados de exemplo |
| [Kubernetes e AWS](docs/kubernetes-aws.md) | Manifests, overlays, HPA, Terraform, EKS, ECR e Secrets Manager |
| [API e autenticação](docs/api.md) | JWT, endpoints públicos, endpoints administrativos e notas de uso |
| [Notificações por e-mail](docs/email.md) | SMTP, provedores compatíveis e configuração de envio |
| [Testes, carga e CI/CD](docs/testes-carga-ci.md) | Pytest, Testcontainers, Locust, HPA e GitHub Actions |
| [Segurança](docs/seguranca.md) | Bandit, pip-audit, Trivy e relatórios gerados |
| [Saga da ordem de serviço](docs/saga.md) | Fase 4: contratos entre os microsserviços (comandos, eventos, compensações, prazos e envelope das mensagens) |
| [RFCs](docs/rfcs/README.md) | Decisões técnicas relevantes: nuvem, banco, autenticação, API Gateway, monitoramento, decomposição em microsserviços e mensageria |
| [ADRs](docs/adrs/README.md) | Decisões arquiteturais permanentes: padrão de comunicação, HPA, banco gerenciado, saga orquestrada e persistência poliglota |
| [Terraform AWS](infra/aws/README.md) | Stack AWS principal |
| [Terraform backend](infra/backend/README.md) | Backend remoto em S3 com lock em DynamoDB |

## Repositórios do projeto

O projeto é composto por 8 repositórios, cada um com CI/CD e regras de proteção próprias. Este repositório é a **aplicação principal** e, a partir da Fase 4, passa a ser o **OS Service**, que hospeda o orquestrador da saga.

### Fase 3: plataforma compartilhada

Infraestrutura e autenticação criadas na Fase 3. Na Fase 4 elas continuam em uso por todos os microsserviços ([RFC-0006](docs/rfcs/0006-decomposicao-em-microsservicos.md)).

| Repositório | Papel | Status |
|---|---|---|
| [oficina-mecanica-infra-banco-dados](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados) | Infraestrutura do Banco de Dados Gerenciado (Terraform, RDS PostgreSQL) | Implementado |
| [oficina-mecanica-infra-kubernetes](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes) | Infraestrutura Kubernetes (Terraform, VPC, EKS, ECR, add-ons) | Implementado |
| [oficina-mecanica-lambda-auth](https://github.com/phantosmia/oficina-mecanica-lambda-auth) | Function Serverless de autenticação via CPF | Implementado |

### Fase 4: microsserviços

Divisão e justificativa em [RFC-0006](docs/rfcs/0006-decomposicao-em-microsservicos.md); contrato entre os serviços em [`docs/saga.md`](docs/saga.md).

| Repositório | Papel | Banco | Status |
|---|---|---|---|
| [oficina-mecanica-fiap](https://github.com/phantosmia/oficina-mecanica-fiap) (este) | OS Service: clientes, veículos, ordens de serviço e orquestrador da saga | PostgreSQL | Em refatoração |
| [oficina-mecanica-catalogo](https://github.com/phantosmia/oficina-mecanica-catalogo) | Catálogo de serviços e fichas de peças (consultado por REST síncrono, fora da saga) | DynamoDB | Em desenvolvimento |
| [oficina-mecanica-estoque](https://github.com/phantosmia/oficina-mecanica-estoque) | Saldo e reservas de peças (participante da saga) | PostgreSQL | Em desenvolvimento |
| [oficina-mecanica-orcamento-pagamento](https://github.com/phantosmia/oficina-mecanica-orcamento-pagamento) | Orçamento, aprovação e pagamento via Mercado Pago (participante da saga) | PostgreSQL | Em desenvolvimento |
| [oficina-mecanica-execucao](https://github.com/phantosmia/oficina-mecanica-execucao) | Fila de execução, diagnóstico e reparo (participante da saga) | DynamoDB | Em desenvolvimento |

## Visão geral

Esta versão atende os principais requisitos do desafio:

- CRUD de clientes, veículos, serviços do catálogo, peças e insumos
- criação, acompanhamento, listagem e detalhamento de ordens de serviço
- orçamento automático baseado em serviços e peças
- baixa automática de estoque na aprovação da OS
- acompanhamento do status da OS
- consulta pública de andamento da OS pelo cliente
- aprovação ou recusa pública de orçamento por token enviado por e-mail
- autenticação JWT para APIs administrativas
- validações de CPF/CNPJ, placa e e-mail
- migrations Alembic para versionamento do banco
- testes automatizados com Testcontainers e cobertura mínima
- Docker Compose, Kubernetes, HPA, Locust, Terraform AWS/EKS e CI/CD
- logs estruturados em JSON, correlacionados por requisição (`X-Request-ID`) e por trace/span da APM (New Relic)
- diagramas de arquitetura (ER, componentes C4, infraestrutura AWS, dependência entre repositórios, fluxo de deploy e sequência) em [docs/arquitetura.md](docs/arquitetura.md)

## Stack

- FastAPI
- PostgreSQL 16
- SQLAlchemy 2 + psycopg 3
- Alembic
- Poetry
- Pytest + Testcontainers
- Docker e Docker Compose
- Kubernetes + Kustomize + HPA
- Locust
- Terraform
- AWS EKS, ECR, RDS, Secrets Manager e S3 backend (EKS/ECR provisionados pelo repositório `oficina-mecanica-infra-kubernetes`; RDS pelo repositório `oficina-mecanica-infra-banco-dados`)
- GitHub Actions

## Como rodar rápido

Com Docker Compose:

```bash
docker compose up --build
```

Depois acesse:

- `http://localhost:8000/docs`
- `http://localhost:8000/health`
- `http://localhost:8000/db-status`

Para parar:

```bash
docker compose down
```

Para rodar localmente com Poetry:

```bash
docker compose up -d db
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Credenciais administrativas padrão para ambiente local:

| Campo | Valor |
|---|---|
| Usuário | `admin` |
| Senha | `Admin@123` |

O projeto também possui tasks no [.mise.toml](.mise.toml):

```bash
mise install
mise run db-up
mise run migrate
mise run dev
mise run test
```

Mais detalhes ficam em [docs/execucao-local.md](docs/execucao-local.md).

## Kubernetes e AWS

Aplicar Kubernetes local:

```bash
kubectl apply -k k8s/overlays/local
```

Aplicar no AWS Academy Lab:

```bash
kubectl apply -k k8s/overlays/aws-academy
```

Aplicar no AWS/EKS completo:

```bash
kubectl apply -k k8s/overlays/aws
```

O HPA escala a API entre 2 e 5 pods por CPU/memória. Para demonstrações, o scale-up foi configurado sem janela artificial de 1 minuto.

Para simular carga com Locust dentro do cluster:

```bash
mise run k8s-load-run
mise run k8s-hpa-watch
mise run k8s-load-logs
```

Detalhes operacionais:

- Kubernetes e AWS: [docs/kubernetes-aws.md](docs/kubernetes-aws.md)
- Terraform AWS (secret + IRSA da API): [infra/aws/README.md](infra/aws/README.md)
- Terraform backend S3/DynamoDB: [infra/backend/README.md](infra/backend/README.md)
- Terraform do cluster EKS/VPC/ECR: [oficina-mecanica-infra-kubernetes](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes)
- Terraform do RDS: [oficina-mecanica-infra-banco-dados](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados)
- Teste de carga e HPA: [docs/testes-carga-ci.md](docs/testes-carga-ci.md)

## Testes e qualidade

Rodar testes:

```bash
poetry run pytest
```

Gerar relatório de segurança:

```bash
bash scripts/security_scan.sh
```

O pipeline de CI executa testes com PostgreSQL efêmero via Testcontainers, valida build Docker e valida Terraform/Kustomize.

Mais detalhes:

- Testes, Locust e CI/CD: [docs/testes-carga-ci.md](docs/testes-carga-ci.md)
- Segurança e relatórios: [docs/seguranca.md](docs/seguranca.md)

## Observações

- O histórico de clientes, veículos, peças e ordens fica persistido no PostgreSQL.
- A conexão com o banco é configurada por `DATABASE_URL` ou pelas variáveis `POSTGRES_*`.
- Segredos reais devem ficar fora do Git, em `.env`, `.aws_credentials`, `terraform.tfvars`, `backend.hcl`, GitHub Secrets ou AWS Secrets Manager.
- A documentação OpenAPI é gerada automaticamente pelo FastAPI em `/docs` e `/redoc`.
