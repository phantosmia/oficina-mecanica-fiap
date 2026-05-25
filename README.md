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
- SQLite
- Poetry
- Pytest
- JWT

## Justificativa do banco de dados

Foi utilizado **SQLite** por ser um MVP monolítico com foco em simplicidade de setup, baixo custo operacional e facilidade para execução local e em ambiente acadêmico. Para a primeira versão, o banco atende bem ao volume esperado e permite validar rapidamente o domínio antes de uma evolução futura para um banco cliente-servidor, como PostgreSQL.

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
│   └── http_errors.py       # Mapeamento DomainError → HTTPException
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

### 1. Instalar dependências

`poetry install`

### 2. Rodar a API

`poetry run uvicorn app.main:app --reload`

### 3. Acessar a documentação

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Como executar com Docker Compose

`docker compose up --build`

Após subir, acesse:

- `http://localhost:8000/docs`
- `http://localhost:8000/health`
- `http://localhost:8000/db-status`

O container da API agora inclui automaticamente dados de exemplo (clientes, veículos, serviços, peças e ordens de serviço) para facilitar os testes. O serviço da API também possui `healthcheck` no Compose para facilitar validação do container.

Para parar:

`docker compose down`

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

#### Métricas
- `GET /service-orders/metrics/average-execution-time` - Retorna tempo médio de execução das OSs

---

### Notas sobre os endpoints

- **Campos marcados com \*** são opcionais
- **Validações automáticas**: CPF/CNPJ, placa de veículo, email
- **Controle de estoque**: Ao aprovar uma OS, as peças são automaticamente baixadas do estoque
- **Geração de orçamento**: Calculado automaticamente ao adicionar serviços e peças
- **Status da OS**: Fluxo obrigatório: recebida → em_diagnostico → aguardando_aprovacao → em_execucao → finalizada → entregue

## Testes automatizados

Executar:

`poetry run pytest`

Cobertura atual configurada com mínimo de `80%` para os domínios críticos.

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

- o histórico de clientes, veículos, peças e ordens fica persistido no arquivo SQLite em `data/oficina_mecanica.db`
- o estoque é validado na criação e aprovado com baixa automática ao autorizar a OS
- a documentação OpenAPI é gerada automaticamente pelo FastAPI
