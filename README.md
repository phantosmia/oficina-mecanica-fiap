# oficina-mecanica-fiap

MVP do back-end do Sistema Integrado de Atendimento e Execução de Serviços de uma oficina mecânica, desenvolvido em FastAPI com PostgreSQL, autenticação JWT, migrations Alembic, Docker, Kubernetes, Terraform AWS/EKS e pipeline GitHub Actions.

## Índice

- [Documentação complementar](#documentação-complementar)
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
| [Arquitetura](docs/arquitetura.md) | Clean Architecture, estrutura de pastas, PostgreSQL, princípios aplicados e diagramas (componentes C4, infraestrutura AWS e fluxo de deploy) |
| [Regras de negócio](docs/regras-negocio.md) | Fluxo da OS, status, cálculo de orçamento e baixa de estoque |
| [Execução local](docs/execucao-local.md) | Mise, Poetry, Docker Compose, migrations e dados de exemplo |
| [Kubernetes e AWS](docs/kubernetes-aws.md) | Manifests, overlays, HPA, Terraform, EKS, ECR, RDS e Secrets Manager |
| [API e autenticação](docs/api.md) | JWT, endpoints públicos, endpoints administrativos e notas de uso |
| [Notificações por e-mail](docs/email.md) | SMTP, provedores compatíveis e configuração de envio |
| [Testes, carga e CI/CD](docs/testes-carga-ci.md) | Pytest, Testcontainers, Locust, HPA e GitHub Actions |
| [Segurança](docs/seguranca.md) | Bandit, pip-audit, Trivy e relatórios gerados |
| [RFCs](docs/rfcs/README.md) | Decisões técnicas relevantes: escolha da nuvem, do banco e da estratégia de autenticação |
| [ADRs](docs/adrs/README.md) | Decisões arquiteturais permanentes: padrão de comunicação, HPA e banco gerenciado |
| [Terraform AWS](infra/aws/README.md) | Stack AWS principal |
| [Terraform backend](infra/backend/README.md) | Backend remoto em S3 com lock em DynamoDB |

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
- diagramas de arquitetura (componentes C4, infraestrutura AWS e fluxo de deploy) em [docs/arquitetura.md](docs/arquitetura.md)

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
- AWS EKS, ECR, RDS, Secrets Manager e S3 backend
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
- Terraform AWS: [infra/aws/README.md](infra/aws/README.md)
- Terraform backend S3/DynamoDB: [infra/backend/README.md](infra/backend/README.md)
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
