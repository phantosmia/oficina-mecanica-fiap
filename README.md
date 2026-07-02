# oficina-mecanica-fiap

MVP do back-end do Sistema Integrado de Atendimento e Execução de Serviços de uma oficina mecânica.

## Objetivo do MVP

Esta versão atende os principais requisitos do desafio:

- CRUD de clientes
- CRUD de veículos
- CRUD de serviços do catálogo
- CRUD de peças e insumos com controle de estoque
- criação, acompanhamento, listagem e detalhamento de ordens de serviço
- orçamento automático baseado em serviços e peças
- acompanhamento do status da OS
- consulta pública de andamento da OS pelo cliente
- autenticação JWT para APIs administrativas
- validações de CPF/CNPJ e placa
- testes automatizados com cobertura mínima de 80%
- Dockerfile e `docker-compose.yml`

## Stack adotada

- FastAPI
- PostgreSQL 16 (via Docker)
- SQLAlchemy 2 + psycopg 3
- Poetry
- Pytest
- JWT

## Justificativa do banco de dados

A primeira versão do MVP foi implementada com **SQLite** por simplicidade de setup local. Para esta evolução, o banco foi migrado para **PostgreSQL**, motivado por:

- **Modelo cliente-servidor real**: o PostgreSQL é executado em um processo dedicado (no Compose, no CI e em produção), o que se aproxima do cenário operacional final e elimina particularidades do SQLite (banco em arquivo, locking em escrita concorrente, ausência de tipos ricos).
- **Concorrência e integridade**: oficinas mecânicas têm múltiplos usuários e fluxos concorrentes (criação de OS, baixa de estoque, atualização de status). O PostgreSQL oferece MVCC, transações reais e checagem de constraints mais robusta — incluindo `ON DELETE CASCADE` e `ON DELETE RESTRICT` honrados nativamente, sem necessidade de `PRAGMA foreign_keys`.
- **Aderência ao ambiente de execução**: como toda a stack já roda em containers, manter o banco como um serviço separado deixa o ambiente local idêntico ao de CI e ao de produção, evitando o clássico problema de "funciona no SQLite mas quebra no Postgres".
- **Evolução prevista**: a justificativa anterior já apontava o PostgreSQL como destino natural; esta entrega concretiza essa migração sem alterar a Clean Architecture — apenas a configuração de conexão (`DATABASE_URL`) e o adaptador SQLAlchemy mudaram. Domínio, casos de uso e controllers permanecem intactos.
- **CI determinístico**: o pipeline usa **Testcontainers** para provisionar um PostgreSQL `postgres:16-alpine` efêmero diretamente a partir da suíte de testes (o runner `ubuntu-latest` já possui Docker), garantindo paridade exata com o banco usado em desenvolvimento e produção, sem precisar manter um serviço externo ou um passo dedicado no workflow.

## Arquitetura

O projeto adota **Clean Architecture** organizada por **contextos de domínio**. Cada contexto é independente e possui suas próprias quatro camadas internas, com dependências fluindo sempre de fora para dentro (inversão de dependência).

### Regra de dependência

```
controller  →  application  →  domain
    ↓               ↓
adapters    →  domain (implements interface)
```

- **Domínio** não conhece nada externo (sem FastAPI, SQLAlchemy, Pydantic)
- **Application** depende apenas de interfaces abstratas (`IXxxRepository`)
- **Adapters** implementam as interfaces do domínio (SQLAlchemy, etc.)
- **Controller** injeta as implementações concretas via `Depends` do FastAPI

### Estrutura principal

```
app/
├── shared/                  # Infraestrutura transversal
│   ├── models.py            # Modelos SQLAlchemy (ORM)
│   ├── database.py          # Engine, sessão e get_db()
│   ├── security.py          # JWT e autenticação
│   ├── validators.py        # Validações de CPF/CNPJ e placa
│   ├── exceptions.py        # Erros de domínio (DomainError e subclasses)
│   ├── http_errors.py       # Mapeamento DomainError → HTTPException
│   ├── email.py             # Porta IEmailNotifier (ABC) + NullEmailNotifier + templates
│   └── smtp_notifier.py     # Adaptador SMTP concreto (smtplib)
│
├── auth/                    # Autenticação JWT
├── clients/                 # Gestão de clientes
├── vehicles/                # Gestão de veículos
├── service_catalog/         # Catálogo de serviços
├── parts/                   # Peças e insumos
├── service_orders/          # Ordens de serviço
└── system/                  # Healthcheck e status
```

Cada contexto segue a mesma estrutura interna:

```
<contexto>/
├── domain/
│   ├── entity.py         # Entidades puras (dataclasses) — sem ORM ou HTTP
│   ├── repository.py     # Interface ABC — contrato exigido pelo domínio
│   └── value_objects.py  # (service_orders) Status e regras de transição
├── application/
│   └── use_cases.py      # Casos de uso — orquestram o domínio via interfaces
├── adapters/
│   ├── sqlalchemy_repository.py  # Implementação concreta da interface
│   └── presenter.py              # Converte entidade → schema Pydantic
├── controller.py          # FastAPI router — injeta repositório via Depends
└── schemas.py             # Contratos Pydantic de entrada e saída
```

### Princípios aplicados

| Princípio | Como foi aplicado |
|-----------|-------------------|
| **Inversão de dependência** | `application` depende de `IXxxRepository` (ABC); `adapters` implementa a interface; `controller` injeta a implementação concreta |
| **Isolamento do domínio** | Entidades são `dataclass` puras — nenhum import de FastAPI, SQLAlchemy ou Pydantic no `domain/` |
| **Casos de uso independentes** | `use_cases.py` lança apenas `DomainError`; a conversão para HTTP fica no `controller` via `domain_error_handler()` |
| **Substituibilidade** | Qualquer `SqlAlchemyXxxRepository` pode ser trocado por um mock nos testes sem alterar domínio ou casos de uso |

- `app/shared`: infraestrutura transversal, segurança, configuração e validações
- `app/auth`: autenticação JWT
- `app/clients`: gestão de clientes
- `app/vehicles`: gestão de veículos
- `app/service_catalog`: catálogo de serviços
- `app/parts`: peças e insumos
- `app/service_orders`: ordens de serviço e regras de negócio
- `app/system`: healthcheck e status da aplicação

## Regras principais implementadas

### Status da ordem de serviço

- `recebida`
- `em_diagnostico`
- `aguardando_aprovacao`
- `em_execucao`
- `finalizada`
- `entregue`
- `recusada` — orçamento recusado pelo cliente (terminal)

### Fluxo da OS

1. cadastro do cliente por CPF/CNPJ
2. cadastro ou atualização do veículo por placa
3. inclusão dos serviços solicitados
4. inclusão opcional de peças/insumos
5. geração automática do orçamento
6. envio do orçamento para aprovação
7. aprovação e baixa de estoque
8. finalização e entrega

## Cálculo da Ordem de Serviço

### Geração automática do orçamento

Quando uma OS é criada, o orçamento é calculado **automaticamente** com base nos serviços e peças inclusos:

#### Fórmula de cálculo

```
labor_total = Σ (preço_serviço × quantidade_serviço)
parts_total = Σ (preço_peça × quantidade_peça)
quote_total = labor_total + parts_total
```

#### Exemplo prático

Supondo uma OS com:
- **Serviços**:
  - Troca de óleo: R$ 150,00 × 1 = R$ 150,00
  - Revisão de freios: R$ 200,00 × 1 = R$ 200,00
  - Subtotal de serviços: R$ 350,00

- **Peças**:
  - Óleo sintético: R$ 45,00 × 4 = R$ 180,00
  - Filtro de óleo: R$ 25,00 × 1 = R$ 25,00
  - Pastilha de freio: R$ 180,00 × 1 = R$ 180,00
  - Subtotal de peças: R$ 385,00

- **Orçamento final**: R$ 350,00 + R$ 385,00 = **R$ 735,00**

### Validações durante o cálculo

1. **Verificação de disponibilidade de serviços**: Verifica se o serviço existe no catálogo e está ativo
2. **Verificação de estoque**: Garante que há quantidade suficiente de peças em estoque (na criação)
3. **Preços**: Utiliza os preços atuais do catálogo (serviços e peças) no momento da criação

### Baixa de estoque automática

Ao **aprovar** a OS (transição para `em_execucao`):
- O sistema verifica novamente se há estoque suficiente
- Se houver disponibilidade, **reduz automaticamente** a quantidade em estoque
- Se não houver estoque, retorna erro 409 Conflict

**Exemplo**: Se aprova uma OS com 4 unidades de óleo:
```
estoque_anterior = 50
estoque_após_aprovação = 50 - 4 = 46
```

### Estrutura do cálculo no banco

Cada item (serviço ou peça) dentro da OS armazena:
- `quantity`: quantidade do item
- `unit_price`: preço unitário no momento da criação da OS
- `subtotal`: quantity × unit_price (calculado e armazenado para auditoria)

## Como executar localmente

### 1. Subir o banco PostgreSQL

O banco roda como um serviço separado em container. Suba apenas o serviço de banco do Compose:

`docker compose up -d db`

Isso expõe o PostgreSQL em `localhost:5432` com as credenciais padrão:

- usuário: `oficina`
- senha: `oficina`
- database: `oficina_mecanica`

### 2. Instalar dependências

`poetry install`

### 3. Rodar a API

`poetry run uvicorn app.main:app --reload`

A aplicação lê a conexão a partir da variável de ambiente `DATABASE_URL` (ou das variáveis `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`). Os defaults já apontam para o container do Compose em `localhost:5432`.

### 4. Acessar a documentação

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Como executar com Docker Compose

`docker compose up --build`

O Compose sobe **dois serviços**:

- `db`: PostgreSQL 16 com healthcheck e volume persistente (`oficina-pgdata`)
- `api`: aplicação FastAPI, que só inicia depois que o `db` está saudável (`depends_on: condition: service_healthy`)

O `docker-entrypoint.sh` aguarda explicitamente o PostgreSQL aceitar conexões antes de criar o schema e popular dados de exemplo.

> **Segurança**: o container da API roda com um usuário sem privilégios (`app`, `uid=1001`), e não como `root`. Isso reduz o impacto de uma eventual escalada de privilégios a partir do processo da aplicação.

Após subir, acesse:

- `http://localhost:8000/docs`
- `http://localhost:8000/health`
- `http://localhost:8000/db-status`

O container da API inclui automaticamente dados de exemplo (clientes, veículos, serviços, peças e ordens de serviço) para facilitar os testes. O serviço da API também possui `healthcheck` no Compose para validação do container.

Para parar:

`docker compose down`

Para remover também o volume de dados do banco:

`docker compose down -v`

## Como executar com Kubernetes

Os manifests Kubernetes ficam em `k8s/` e reproduzem a stack do Compose com:

- `Namespace` dedicado (`oficina-mecanica`)
- `ConfigMap` para variáveis não sensíveis
- `Secret` para senha do banco, senha administrativa, chave JWT e senha SMTP
- `StatefulSet` + `Service` para PostgreSQL 16
- `Deployment` + `Service` para a API FastAPI
- probes de startup, readiness e liveness em `/health`

### 1. Construir a imagem da API

Para deploy em AWS ou qualquer cluster remoto, publique a imagem no Docker Hub. Troque `SEU_USUARIO_DOCKERHUB` pelo seu nome de usuário e rode:

`docker login`

`docker build -t SEU_USUARIO_DOCKERHUB/oficina-mecanica-fiap:latest .`

`docker push SEU_USUARIO_DOCKERHUB/oficina-mecanica-fiap:latest`

O arquivo `k8s/kustomization.yaml` já está preparado para usar esse repositório. Se quiser testar localmente com Minikube, você pode trocar o valor de `newName` para o seu usuário ou usar `minikube image load`.

### 2. Aplicar os manifests

`kubectl apply -k k8s/`

### 3. Aguardar os pods ficarem prontos

`kubectl get pods -n oficina-mecanica -w`

O container da API usa o mesmo `docker-entrypoint.sh` do Docker Compose: ele aguarda o PostgreSQL, inicializa o schema e popula os dados de exemplo de forma idempotente.

### 4. Acessar a API

`minikube service oficina-mecanica-api -n oficina-mecanica --url`

O comando retorna a URL de acesso da API (NodePort). Você também pode consultar o NodePort com:

`kubectl get svc oficina-mecanica-api -n oficina-mecanica`

Depois, acesse:

- `<URL_DO_NODEPORT>/docs`
- `<URL_DO_NODEPORT>/health`
- `<URL_DO_NODEPORT>/db-status`

Para remover os recursos:

`kubectl delete -k k8s/`

> **Segurança**: os valores em `k8s/secret.yaml` são os mesmos defaults do ambiente local. Em ambientes reais, substitua esses valores por segredos gerenciados pelo cluster ou por uma ferramenta de secrets antes de aplicar os manifests.

## Autenticação administrativa

Credenciais padrão no `docker-compose.yml`:

- usuário: `admin`
- senha: `Admin@123`

Fluxo:

1. usar `POST /auth/token`
2. informar usuário e senha
3. copiar o `access_token`
4. usar o botão `Authorize` no Swagger

## Endpoints da API

A documentação interativa está disponível em `http://localhost:8000/docs` (Swagger UI) e `http://localhost:8000/redoc` (ReDoc).

### Endpoints públicos (sem autenticação)

#### Sistema
- `GET /` - Retorna mensagem de boas-vindas da API
- `GET /health` - Verifica saúde da aplicação (utilizado pelo healthcheck do Docker)
- `GET /db-status` - Verifica status da conexão com o banco de dados

#### Ordens de Serviço
- `GET /service-orders/{order_id}/tracking?document_number={cpf_ou_cnpj}` - Consulta pública do andamento de uma OS pelo cliente (não requer autenticação)

---

### Endpoints administrativos (requerem JWT)

**Autenticação**: Todos os endpoints abaixo requerem token JWT. Para obter o token, use:
- `POST /auth/token` - Faz login com usuário e senha (padrão: `admin` / `Admin@123`)

#### Clientes
- `GET /clients` - Lista todos os clientes
- `POST /clients` - Cria novo cliente (requer: name, document_number, email*, phone*)
- `GET /clients/{client_id}` - Obtém detalhes de um cliente
- `PUT /clients/{client_id}` - Atualiza dados de um cliente (name*, email*, phone*)
- `DELETE /clients/{client_id}` - Deleta um cliente

#### Veículos
- `GET /vehicles` - Lista todos os veículos
- `POST /vehicles` - Cria novo veículo (requer: client_id, brand, model, year, license_plate)
- `GET /vehicles/{vehicle_id}` - Obtém detalhes de um veículo
- `PUT /vehicles/{vehicle_id}` - Atualiza dados de um veículo (brand*, model*, year*, license_plate*)
- `DELETE /vehicles/{vehicle_id}` - Deleta um veículo

#### Serviços do Catálogo
- `GET /services` - Lista todos os serviços disponíveis
- `POST /services` - Cria novo serviço (requer: name, base_price, estimated_minutes; description*, active*)
- `GET /services/{service_id}` - Obtém detalhes de um serviço
- `PUT /services/{service_id}` - Atualiza dados de um serviço (name*, base_price*, estimated_minutes*, description*, active*)
- `DELETE /services/{service_id}` - Deleta um serviço do catálogo

#### Peças e Insumos
- `GET /parts` - Lista todas as peças
- `POST /parts` - Cria nova peça (requer: name, sku, unit_price; description*, stock_quantity*, min_stock_level*)
- `GET /parts/{part_id}` - Obtém detalhes de uma peça
- `PUT /parts/{part_id}` - Atualiza dados de uma peça (name*, sku*, unit_price*, description*, stock_quantity*, min_stock_level*)
- `DELETE /parts/{part_id}` - Deleta uma peça

#### Ordens de Serviço
- `GET /service-orders` - Lista todas as ordens de serviço (resumo)
- `POST /service-orders` - Cria nova OS (requer: client_id, vehicle_id, problem_description)
- `GET /service-orders/{order_id}` - Obtém detalhes completos de uma OS
- `POST /service-orders/{order_id}/diagnosis` - Inicia diagnóstico da OS (requer: diagnosis_notes)
- `POST /service-orders/{order_id}/send-quote` - Envia orçamento para cliente (requer: diagnosis_notes)
- `POST /service-orders/{order_id}/approve` - Aprova orçamento e baixa estoque automaticamente
- `POST /service-orders/{order_id}/finish` - Marca OS como finalizada
- `POST /service-orders/{order_id}/deliver` - Marca OS como entregue ao cliente
- `POST /service-orders/{order_id}/reject` - Recusa o orçamento (transição de `aguardando_aprovacao` → `recusada`)

#### Métricas
- `GET /service-orders/metrics/average-execution-time` - Retorna tempo médio de execução das OSs

---

### Notas sobre os endpoints

- **Campos marcados com \*** são opcionais
- **Validações automáticas**: CPF/CNPJ, placa de veículo, email
- **Controle de estoque**: Ao aprovar uma OS, as peças são automaticamente baixadas do estoque
- **Geração de orçamento**: Calculado automaticamente ao adicionar serviços e peças
- **Status da OS**: Fluxo principal: recebida → em_diagnostico → aguardando_aprovacao → em_execucao → finalizada → entregue; orçamento pode ser recusado: aguardando_aprovacao → recusada (terminal)
- **Listagem ativa** (`GET /service-orders`): retorna apenas OSs não concluídas (exclui `finalizada`, `entregue` e `recusada`), ordenadas por prioridade de status: `em_execucao` → `aguardando_aprovacao` → `em_diagnostico` → `recebida`
- **Notificações por e-mail**: enviadas automaticamente ao cliente (quando `SMTP_ENABLED=true`) nas transições de status que geram comunicação: envio de orçamento, aprovação, recusa e finalização

## Notificações por e-mail

A API envia e-mails automaticamente ao cliente nas seguintes transições de status:

| Evento | Assunto enviado |
|---|---|
| Orçamento enviado (`aguardando_aprovacao`) | Orçamento disponível para aprovação |
| Orçamento aprovado (`em_execucao`) | Orçamento aprovado — serviço iniciado |
| Orçamento recusado (`recusada`) | Orçamento recusado |
| OS finalizada (`finalizada`) | Veículo pronto para retirada |

As notificações são desabilitadas por padrão (`SMTP_ENABLED=false`). Para habilitar, configure as variáveis de ambiente abaixo.

### Variáveis de ambiente SMTP

| Variável | Padrão | Descrição |
|---|---|---|
| `SMTP_ENABLED` | `false` | Habilita o envio de e-mails |
| `SMTP_HOST` | `""` | Endereço do servidor SMTP |
| `SMTP_PORT` | `587` | Porta SMTP (587 = STARTTLS) |
| `SMTP_FROM` | `""` | Endereço de origem dos e-mails |
| `SMTP_USERNAME` | `""` | Usuário de autenticação SMTP |
| `SMTP_PASSWORD` | `""` | Senha ou senha de app SMTP |

### Provedores compatíveis

| Provedor | `SMTP_HOST` | `SMTP_PORT` |
|---|---|---|
| Gmail | `smtp.gmail.com` | `587` |
| Outlook / Hotmail | `smtp.office365.com` | `587` |
| SendGrid | `smtp.sendgrid.net` | `587` |
| Mailtrap (sandbox) | `sandbox.smtp.mailtrap.io` | `587` |

> **Gmail**: é necessário gerar uma **senha de app** em [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requer 2FA ativo). Não use a senha normal da conta.

> **Mailtrap**: recomendado para testes — intercepta os e-mails sem entregá-los, permitindo validar os templates sem risco de spam.

### Configuração local (`.env`)

Crie um arquivo `.env` na raiz do projeto (não commitar — já listado no `.gitignore`):

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=seuemail@gmail.com
SMTP_USERNAME=seuemail@gmail.com
SMTP_PASSWORD=sua_senha_de_app
```

### Configuração via Docker Compose

Edite as variáveis no `docker-compose.yml`:

```yaml
SMTP_ENABLED: "true"
SMTP_HOST: "smtp.gmail.com"
SMTP_PORT: "587"
SMTP_FROM: "seuemail@gmail.com"
SMTP_USERNAME: "seuemail@gmail.com"
SMTP_PASSWORD: "sua_senha_de_app"
```

---

## Testes automatizados

Os testes utilizam **Testcontainers** para provisionar um PostgreSQL efêmero por execução, eliminando a necessidade de subir o banco manualmente. Basta ter o Docker disponível na máquina e rodar:

`poetry run pytest`

O fluxo automático é:

1. No início da sessão, o `tests/conftest.py` sobe um container `postgres:16-alpine` em uma porta aleatória.
2. A `DATABASE_URL` da aplicação é configurada para apontar para esse container.
3. A cada teste, o schema é recriado (`drop_all` + `create_all`) garantindo isolamento.
4. Ao final da sessão, o container é destruído.

Caso `DATABASE_URL` já esteja definida no ambiente (por exemplo, ao apontar para um banco local existente durante debug), o Testcontainers **não** é acionado e os testes usam a conexão fornecida.

Cobertura mínima configurada: `80%` para os domínios críticos.

## Pipeline automatizada no GitHub

O repositório possui uma pipeline de CI em [.github/workflows/ci.yml](.github/workflows/ci.yml) com execução automática em `push` e `pull_request`.

Etapas executadas no job `tests`:

1. Instalar Python `3.12`, Poetry e dependências do projeto.
2. Executar `poetry run pytest` com a cobertura mínima configurada. O **Testcontainers** provisiona automaticamente um PostgreSQL `postgres:16-alpine` efêmero no início da sessão de testes (o runner `ubuntu-latest` já possui Docker disponível) e o destrói ao final, dispensando um passo dedicado para gerenciar o banco.

O job `build` valida o build da imagem Docker com `docker build` e roda após `tests` ser concluído com sucesso.

## Popular banco com dados de exemplo

Para testar a aplicação com uma base de dados completa, execute:

`poetry run python scripts/populate_db.py`

Isso criará dados de exemplo incluindo clientes, veículos, serviços do catálogo, peças e ordens de serviço em diferentes status.

## Relatório de vulnerabilidades

O projeto foi preparado para gerar relatórios de segurança com:

- `Bandit`: análise estática de segurança do código Python
- `pip-audit`: análise de vulnerabilidades nas dependências Python
- `Trivy`: análise complementar de filesystem e container

### Instalação

As ferramentas `Bandit` e `pip-audit` já estão configuradas nas dependências de desenvolvimento do projeto.

### Gerar relatório local

Executar:

`bash scripts/security_scan.sh`

Os relatórios serão gerados em:

- `reports/security/bandit-report.json`
- `reports/security/pip-audit-report.json`
- `reports/security/trivy-fs-report.json` (quando o Trivy estiver instalado na máquina)
- `reports/security/security-report.md`
- `reports/security/security-report.pdf`

### Executar manualmente

- `poetry run bandit -r app`
- `poetry run pip-audit`
- `trivy fs .`

### Relatório amigável

O script também consolida os achados em formatos mais fáceis de compartilhar com time e gestão:

- Markdown: `reports/security/security-report.md`
- PDF: `reports/security/security-report.pdf`

Isso facilita anexar o relatório em entregas, documentação e evidências do projeto.

### Observações

- `pip-audit` pode retornar código diferente de zero quando encontrar vulnerabilidades; isso indica achados, não falha da configuração
- `Trivy` não é instalado pelo Poetry; ele deve ser instalado no sistema para complementar a análise
- os relatórios JSON gerados ficam ignorados no Git

## Observações

- o histórico de clientes, veículos, peças e ordens fica persistido no PostgreSQL (volume `oficina-pgdata` do Compose)
- a conexão com o banco é configurada via `DATABASE_URL` ou pelas variáveis `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`
- o estoque é validado na criação e aprovado com baixa automática ao autorizar a OS
- a documentação OpenAPI é gerada automaticamente pelo FastAPI
