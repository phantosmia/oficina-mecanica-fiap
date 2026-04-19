# oficina-mecanica-fiap
Projeto da Oficina Mecânica criado para o curso de Pós Graduação de Software Architecture solicitado pela FIAP para conclusão do curso

## Setup inicial

O projeto agora utiliza Poetry para gerenciamento de dependências.

### Dependências principais

- FastAPI
- Uvicorn
- SQLite

### Comandos úteis

- Instalar dependências: `poetry install`
- Ativar o ambiente virtual: `poetry shell`
- Executar a API localmente: `poetry run uvicorn app.main:app --reload`
- Subir com Docker Compose: `docker compose up --build`

## Arquitetura

O projeto foi reorganizado em vertical slice:

- `app/shared`: componentes compartilhados, como acesso ao banco
- `app/slices/system`: endpoints sistêmicos, como healthcheck e status do banco
- `app/slices/clients`: schemas, repository e router de clientes
- `app/slices/vehicles`: schemas, repository e router de veículos
