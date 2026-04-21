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

O projeto está organizado como um monólito com foco no domínio, usando slices por contexto funcional e camadas simples de `router`, `repository` e, quando necessário, `service`.

Estrutura principal:

- `app/shared`: infraestrutura compartilhada, segurança, configuração e validações
- `app/slices/auth`: autenticação JWT
- `app/slices/clients`: gestão de clientes
- `app/slices/vehicles`: gestão de veículos
- `app/slices/service_catalog`: catálogo de serviços
- `app/slices/parts`: peças e insumos
- `app/slices/service_orders`: ordens de serviço e regras de negócio
- `app/slices/system`: healthcheck e status da aplicação

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

## Endpoints principais

### Públicos

- `GET /`
- `GET /health`
- `GET /db-status`
- `GET /service-orders/{order_id}/tracking?document_number=...`

### Administrativos protegidos por JWT

- `POST /auth/token`
- CRUD de `/clients`
- CRUD de `/vehicles`
- CRUD de `/services`
- CRUD de `/parts`
- `POST /service-orders`
- `GET /service-orders`
- `GET /service-orders/{order_id}`
- `POST /service-orders/{order_id}/diagnosis`
- `POST /service-orders/{order_id}/send-quote`
- `POST /service-orders/{order_id}/approve`
- `POST /service-orders/{order_id}/finish`
- `POST /service-orders/{order_id}/deliver`
- `GET /service-orders/metrics/average-execution-time`

## Testes automatizados

Executar:

`poetry run pytest`

Cobertura atual configurada com mínimo de `80%` para os domínios críticos.

## Observações

- o histórico de clientes, veículos, peças e ordens fica persistido no arquivo SQLite em `data/oficina_mecanica.db`
- o estoque é validado na criação e aprovado com baixa automática ao autorizar a OS
- a documentação OpenAPI é gerada automaticamente pelo FastAPI
