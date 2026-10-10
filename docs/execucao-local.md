# Execução Local

## Preparar ambiente com mise

O projeto possui um arquivo [.mise.toml](../.mise.toml) com versões de ferramentas, variáveis de ambiente locais e tasks comuns.

Para preparar o ambiente:

```bash
mise install
```

Para carregar as variáveis no shell atual:

```bash
mise activate zsh
```

Ou execute comandos diretamente com `mise run`, por exemplo:

```bash
mise run db-up
mise run migrate
mise run dev
mise run test
mise run aws-whoami
mise run tf-aws-plan
```

O [.mise.toml](../.mise.toml) define defaults locais não sensíveis e carrega `.env` como override. Credenciais reais, senhas SMTP e valores específicos de Terraform devem ficar no `.env`, em `terraform.tfvars`, em `backend.hcl` ou no arquivo `.aws_credentials`, todos ignorados pelo Git.

## Rodar localmente com Poetry

Suba apenas o banco PostgreSQL do Compose:

```bash
docker compose up -d os-db
```

Credenciais padrão:

| Campo | Valor |
|---|---|
| Usuário | `oficina` |
| Senha | `oficina` |
| Database | `oficina_mecanica` |
| Host local | `localhost:5432` |

Instale dependências:

```bash
poetry install
```

Aplique migrations:

```bash
poetry run alembic upgrade head
```

Rode a API:

```bash
poetry run uvicorn app.main:app --reload
```

A aplicação lê a conexão a partir de `DATABASE_URL` ou das variáveis `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`. Os defaults já apontam para o container do Compose em `localhost:5432`.

Acesse:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`
- `http://localhost:8000/health`
- `http://localhost:8000/db-status`

## Rodar o sistema completo com Docker Compose

O `docker-compose.yml` sobe os 6 microsserviços da Fase 4, cada um com API, worker (consumidor das filas) e relay da outbox, mais a infraestrutura compartilhada:

| Componente | O quê | Porta |
|---|---|---|
| `os-api`, `os-worker`, `os-relay`, `os-db` | OS Service (este repositório) e orquestrador da saga, PostgreSQL | 8000 (API), 5432 (banco) |
| `catalogo-*` | Catálogo (DynamoDB) | 8001 |
| `estoque-*` | Estoque (PostgreSQL) | 8002 |
| `execucao-*` | Execução (DynamoDB) | 8003 |
| `orcamento-*` | Orçamento (DynamoDB) | 8004 |
| `pagamento-*` | Pagamento (PostgreSQL + sandbox do Mercado Pago) | 8005 |
| `localstack` | Emula SQS, SNS e DynamoDB | 4566 |
| `mailpit` | Caixa de entrada dos e-mails enviados | 8025 |

Pré-requisitos:

- Os repositórios dos serviços clonados ao lado deste (`../oficina-mecanica-catalogo`, `../oficina-mecanica-estoque`, `../oficina-mecanica-execucao`, `../oficina-mecanica-orcamento`, `../oficina-mecanica-pagamento`): as imagens são construídas a partir deles.
- Para o Pagamento falar com o Mercado Pago: `../oficina-mecanica-pagamento/.env` com as credenciais de **teste** (ver o README do Pagamento). Sem ele, a cobrança falha e a saga compensa.

```bash
docker compose up --build
```

Cada serviço cria as próprias filas, tópicos e tabelas no LocalStack ao subir, e carrega os dados de exemplo (catálogo, saldo de estoque, clientes e veículos). Os prazos da saga ficam curtos no Compose (resposta de participante: 1 min; aprovação: 10 min; pagamento: 15 min) para dar para demonstrar as compensações por prazo.

### Uma OS atravessando os serviços

Com o sistema no ar (os IDs de catálogo e peça abaixo são os dos dados de exemplo):

```bash
TOKEN=$(curl -s -XPOST localhost:8000/auth/token -d 'username=admin&password=Admin@123' | jq -r .access_token)
H="Authorization: Bearer $TOKEN"

# 1. Admin abre a OS (só cliente, veículo e problema)
curl -s -XPOST localhost:8000/service-orders -H "$H" -H 'content-type: application/json' -d '{
  "client": {"name": "Maria Souza", "document_number": "52998224725", "email": "maria@example.com"},
  "vehicle": {"plate": "BRA2E19", "brand": "VW", "model": "Gol", "year": 2018},
  "problem_description": "Luz do óleo acendendo no painel"}'

# 2. A OS aparece na fila do mecânico (Execução)
curl -s localhost:8003/jobs -H "$H"

# 3. Mecânico diagnostica (itens validados no Catálogo)
SERVICO=$(curl -s localhost:8001/services | jq -r '.[] | select(.name=="Troca de óleo") | .id')
OLEO=572e22d4-2e66-527d-a0ca-9ec61bbd1376
curl -s -XPOST localhost:8003/jobs/1/diagnosis/start -H "$H"
curl -s -XPOST localhost:8003/jobs/1/diagnosis/complete -H "$H" -H 'content-type: application/json' \
  -d "{\"notes\": \"Óleo vencido\", \"services\": [{\"id\": \"$SERVICO\", \"quantity\": 1}], \"parts\": [{\"id\": \"$OLEO\", \"quantity\": 4}]}"

# 4. A saga reserva as peças (Estoque) e gera o orçamento (Orçamento): o e-mail
#    chega em http://localhost:8025. O link abre a página para aprovar ou recusar.
curl -s localhost:8000/service-orders/1/saga -H "$H"     # AGUARDANDO_APROVACAO
curl -s localhost:8002/stock/$OLEO -H "$H"               # 4 unidades reservadas

# 5. Depois da aprovação, a cobrança é criada no Mercado Pago e o link de
#    pagamento chega por e-mail. Para pagar no sandbox: entrar com o usuário
#    comprador de teste e usar um cartão de teste com o titular APRO.
curl -s localhost:8005/charges/1 -H "$H"

# 6. Pagamento confirmado → baixa do estoque → fila de reparo; o mecânico conclui:
curl -s -XPOST localhost:8003/jobs/1/repair/start -H "$H"
curl -s -XPOST localhost:8003/jobs/1/repair/finish -H "$H" -H 'content-type: application/json' -d '{"notes": "Troca feita"}'

# 7. Entrega
curl -s -XPOST localhost:8000/service-orders/1/deliver -H "$H"
curl -s localhost:8000/service-orders/1 -H "$H" | jq .status_history
```

Para ver uma compensação: recuse o orçamento pela página do e-mail (a reserva é liberada e a OS termina `recusada`), ou conclua um diagnóstico pedindo mais peças do que há em estoque (a OS termina `cancelada`).

Para parar:

```bash
docker compose down        # mantém os dados
docker compose down -v     # apaga também o volume do banco do OS Service
```

Os containers rodam com usuário sem privilégios (`uid=1001`), não como `root`.

## Popular banco com dados de exemplo

```bash
poetry run python scripts/populate_db.py
```

Cria clientes e veículos de exemplo. Serviços do catálogo, peças e saldo de estoque são dados de exemplo dos serviços de Catálogo e Estoque. Ordens de serviço não são semeadas: toda OS precisa nascer pela API, que inicia a saga.
