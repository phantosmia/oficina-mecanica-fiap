# API e Autenticação

## Autenticação administrativa

Credenciais padrão no ambiente local e no `docker-compose.yml`:

| Campo | Valor |
|---|---|
| Usuário | `admin` |
| Senha | `Admin@123` |

Fluxo:

1. Usar `POST /auth/token`.
2. Informar usuário e senha.
3. Copiar o `access_token` retornado.
4. Usar o botão `Authorize` no Swagger.

A documentação interativa está disponível em:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Endpoints públicos

### Sistema

- `GET /`: retorna mensagem de boas-vindas da API
- `GET /health`: verifica saúde da aplicação
- `GET /db-status`: verifica status da conexão com o banco de dados

### Ordens de Serviço

- `GET /service-orders/{order_id}/tracking?document_number={cpf_ou_cnpj}`: consulta pública do andamento de uma OS pelo cliente (status, itens do diagnóstico, total e histórico de status). Aceita, alternativamente, um header `Authorization: Bearer {token}` com o JWT de cliente emitido pela Lambda de autenticação via CPF (repositório [`oficina-mecanica-lambda-auth`](https://github.com/phantosmia/oficina-mecanica-lambda-auth), ver RFC-0004/ADR-0004). Quando presente, o token tem prioridade sobre `document_number` e dispensa informá-lo.

A aprovação/recusa do orçamento e o pagamento **não** são mais rotas deste serviço (Fase 4): o cliente aprova pelo link enviado por e-mail pelo serviço de [Orçamento](https://github.com/phantosmia/oficina-mecanica-orcamento) e paga pelo Mercado Pago, via serviço de [Pagamento](https://github.com/phantosmia/oficina-mecanica-pagamento).

## Endpoints administrativos

Todos os endpoints abaixo requerem token JWT. Para obter o token, use `POST /auth/token`.

### Clientes

- `GET /clients`: lista todos os clientes
- `POST /clients`: cria novo cliente (`name`, `document_number`, `email*`, `phone*`)
- `GET /clients/{client_id}`: obtém detalhes de um cliente
- `PUT /clients/{client_id}`: atualiza dados de um cliente (`name*`, `email*`, `phone*`, `status*` — `ativo` ou `inativo`)
- `DELETE /clients/{client_id}`: deleta um cliente

### Veículos

- `GET /vehicles`: lista todos os veículos
- `POST /vehicles`: cria novo veículo (`client_id`, `brand`, `model`, `year`, `license_plate`)
- `GET /vehicles/{vehicle_id}`: obtém detalhes de um veículo
- `PUT /vehicles/{vehicle_id}`: atualiza dados de um veículo (`brand*`, `model*`, `year*`, `license_plate*`)
- `DELETE /vehicles/{vehicle_id}`: deleta um veículo

### Catálogo de serviços e peças

Saíram deste serviço na Fase 4: agora são os microsserviços de [Catálogo](https://github.com/phantosmia/oficina-mecanica-catalogo) (serviços e fichas de peças) e de [Estoque](https://github.com/phantosmia/oficina-mecanica-estoque) (saldo e reservas). O token de admin emitido aqui (`POST /auth/token`) vale nas rotas de admin de todos os serviços.

### Ordens de Serviço

- `POST /service-orders`: abre uma OS e inicia a saga. Payload: `client` (`name`, `document_number`, `email*`, `phone*`), `vehicle` (`plate`, `brand`, `model`, `year`) e `problem_description`. Os serviços e peças **não** vão na abertura: vêm do diagnóstico, feito pelo mecânico no serviço de Execução ([ADR-0010](adrs/0010-diagnostico-define-o-orcamento.md)).
- `GET /service-orders`: OS com trabalho pendente, por prioridade de status
- `GET /service-orders/{order_id}`: detalhes da OS, com itens, totais, datas de cada etapa e histórico de status
- `POST /service-orders/{order_id}/deliver`: entrega do veículo (só a partir de `finalizada`); é a única mudança manual de status
- `GET /service-orders/{order_id}/saga`: estado da saga da OS: etapa, último comando enviado e tentativas, prazo, compensações pendentes e motivo da falha, se houver
- `POST /service-orders/{order_id}/saga/retry`: reenvia o último comando da saga (ex.: compensação parada à espera de intervenção)

Exemplo de abertura:

```json
{
  "client": { "name": "Maria Souza", "document_number": "52998224725", "email": "maria@example.com" },
  "vehicle": { "plate": "BRA2E19", "brand": "VW", "model": "Gol", "year": 2018 },
  "problem_description": "Luz do óleo acendendo no painel"
}
```

### Métricas

- `GET /service-orders/metrics/average-execution-time`: retorna tempo médio de execução das OSs

## Notas

- Campos marcados com `*` são opcionais.
- CPF/CNPJ, placa de veículo e e-mail são validados automaticamente.
- O status da OS é mudado pela saga, a partir dos eventos dos outros serviços (ver [Regras de negócio](regras-negocio.md) e [`docs/saga.md`](saga.md)); a única transição manual é a entrega.
- O fluxo principal é `recebida` → `em_diagnostico` → `aguardando_aprovacao` → `aguardando_pagamento` → `em_execucao` → `finalizada` → `entregue`, com `recusada` e `cancelada` como saídas terminais.
- A listagem de OS exclui `finalizada`, `entregue`, `recusada` e `cancelada`.
- Este serviço envia por e-mail só o aviso de OS finalizada (quando `SMTP_ENABLED=true`); os e-mails de orçamento e de pagamento são dos serviços de Orçamento e de Pagamento.
