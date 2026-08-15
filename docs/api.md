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

- `GET /service-orders/{order_id}/tracking?document_number={cpf_ou_cnpj}`: consulta pública do andamento de uma OS pelo cliente. Aceita, alternativamente, um header `Authorization: Bearer {token}` com o JWT de cliente emitido pela Lambda de autenticação via CPF (repositório [`oficina-mecanica-lambda-auth`](https://github.com/phantosmia/oficina-mecanica-lambda-auth), ver RFC-0004/ADR-0004) — quando presente, o token tem prioridade sobre `document_number` e dispensa informá-lo. As duas formas coexistem: nenhuma delas foi removida.
- `POST /service-orders/{order_id}/quote-response`: aprova ou recusa orçamento com token público enviado por e-mail

Payload para resposta de orçamento:

```json
{
  "token": "token_recebido_no_email",
  "decision": "approve"
}
```

Use `decision: "approve"` para aprovar o orçamento ou `decision: "reject"` para recusá-lo. O token é gerado quando o endpoint administrativo `POST /service-orders/{order_id}/send-quote` envia o orçamento, fica vinculado à OS e é invalidado após a primeira aprovação ou recusa.

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

### Serviços do Catálogo

- `GET /services`: lista todos os serviços disponíveis
- `POST /services`: cria novo serviço (`name`, `base_price`, `estimated_minutes`, `description*`, `active*`)
- `GET /services/{service_id}`: obtém detalhes de um serviço
- `PUT /services/{service_id}`: atualiza dados de um serviço (`name*`, `base_price*`, `estimated_minutes*`, `description*`, `active*`)
- `DELETE /services/{service_id}`: deleta um serviço do catálogo

### Peças e Insumos

- `GET /parts`: lista todas as peças
- `POST /parts`: cria nova peça (`name`, `sku`, `unit_price`, `description*`, `stock_quantity*`, `min_stock_level*`)
- `GET /parts/{part_id}`: obtém detalhes de uma peça
- `PUT /parts/{part_id}`: atualiza dados de uma peça (`name*`, `sku*`, `unit_price*`, `description*`, `stock_quantity*`, `min_stock_level*`)
- `DELETE /parts/{part_id}`: deleta uma peça

### Ordens de Serviço

- `GET /service-orders`: lista todas as ordens de serviço ativas em formato de resumo
- `POST /service-orders`: cria nova OS (`client_id`, `vehicle_id`, `problem_description`)
- `GET /service-orders/{order_id}`: obtém detalhes completos de uma OS
- `POST /service-orders/{order_id}/diagnosis`: inicia diagnóstico da OS (`diagnosis_notes`)
- `POST /service-orders/{order_id}/send-quote`: envia orçamento para cliente (`diagnosis_notes`)
- `POST /service-orders/{order_id}/approve`: aprova orçamento e baixa estoque automaticamente
- `POST /service-orders/{order_id}/finish`: marca OS como finalizada
- `POST /service-orders/{order_id}/deliver`: marca OS como entregue ao cliente
- `POST /service-orders/{order_id}/reject`: recusa o orçamento (`aguardando_aprovacao` -> `recusada`)

### Métricas

- `GET /service-orders/metrics/average-execution-time`: retorna tempo médio de execução das OSs

## Notas

- Campos marcados com `*` são opcionais.
- CPF/CNPJ, placa de veículo e e-mail são validados automaticamente.
- Ao aprovar uma OS, as peças são baixadas do estoque automaticamente.
- O orçamento é calculado automaticamente ao adicionar serviços e peças.
- O fluxo principal da OS é `recebida` -> `em_diagnostico` -> `aguardando_aprovacao` -> `em_execucao` -> `finalizada` -> `entregue`.
- O orçamento pode ser recusado com a transição `aguardando_aprovacao` -> `recusada`.
- A listagem ativa de OSs exclui `finalizada`, `entregue` e `recusada`.
- Notificações por e-mail são enviadas quando `SMTP_ENABLED=true`.
