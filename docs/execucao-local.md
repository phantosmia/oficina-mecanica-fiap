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
docker compose up -d db
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

## Rodar com Docker Compose

```bash
docker compose up --build
```

O Compose sobe dois serviços:

- `db`: PostgreSQL 16 com healthcheck e volume persistente `oficina-pgdata`
- `api`: aplicação FastAPI, que só inicia depois que o `db` está saudável

O `docker-entrypoint.sh` aguarda o PostgreSQL aceitar conexões, aplica as migrations com Alembic e popula dados de exemplo.

O container da API roda com um usuário sem privilégios (`app`, `uid=1001`), e não como `root`.

Após subir, acesse:

- `http://localhost:8000/docs`
- `http://localhost:8000/health`
- `http://localhost:8000/db-status`

Para parar:

```bash
docker compose down
```

Para remover também o volume de dados do banco:

```bash
docker compose down -v
```

## Popular banco com dados de exemplo

Para testar a aplicação com uma base de dados completa, execute:

```bash
poetry run python scripts/populate_db.py
```

Isso cria dados de exemplo incluindo clientes, veículos, serviços do catálogo, peças e ordens de serviço em diferentes status.
