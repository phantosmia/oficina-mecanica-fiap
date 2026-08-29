# newrelic-alerts

Terraform root **separado** de [`../aws`](../aws), [`../newrelic-dashboards`](../newrelic-dashboards) e [`../newrelic-aws-integration`](../newrelic-aws-integration) — mesmo motivo dos outros dois: o provider `newrelic` precisa de config própria (`account_id`/`api_key`/`region`), incompatível com `count`/`for_each` num `module`.

Cria os alertas exigidos pelo PDF da Fase 3 ("Monitoramento e Observabilidade" → "Alertas para falhas no processamento de ordens de serviço"), mais dois alertas que cobrem os outros itens da mesma seção ("Healthchecks e uptime" e uma leitura geral de degradação/erro da API, como sinal de gargalo em tempo real).

Vive aqui, e não em `oficina-mecanica-lambda-auth`, pelo mesmo motivo de `newrelic-dashboards`: alertas são uma preocupação de sistema inteiro, e este é o repositório "hub" do projeto.

## O que este root cria

- **Uma policy** (`newrelic_alert_policy`) agrupando as três condições abaixo.
- **Um canal de notificação por e-mail** (`newrelic_notification_destination` + `newrelic_notification_channel` + `newrelic_workflow`), usando o modelo atual de alertas do New Relic (workflows), não o modelo legado (`newrelic_alert_channel`).
- **Três condições NRQL** (`newrelic_nrql_alert_condition`), todas sobre dado que a APM (agente New Relic Python, ADR-0007) já captura sozinha em `Transaction`/`TransactionError` — nenhuma exige evento customizado novo em `app/shared/telemetry.py`:
  1. **Falhas no processamento de ordens de serviço** — `TransactionError` nas rotas `/service-orders*` (diagnóstico, orçamento, aprovação, execução, finalização, entrega). Requisito literal do PDF.
  2. **Taxa de erro geral da API elevada** — mesma query e limiares (critical 5%, warning 1%) do widget "Taxa de erro da API" em `newrelic-dashboards`, para os dois ficarem consistentes.
  3. **Healthcheck `/health` abaixo do uptime esperado** — mesma query e limiares (critical 95%, warning 99%) do widget "Uptime do healthcheck" em `newrelic-dashboards`.

## Pré-requisito

A APM da aplicação principal (`../aws`, `NEW_RELIC_LICENSE_KEY`) precisa estar aplicada e reportando dados — sem isso, `Transaction`/`TransactionError` não existem e as condições nunca disparam (nem geram erro; só ficam sem dado, igual aos widgets do dashboard).

## Uso

```bash
cp backend.hcl.example backend.hcl       # mesmo backend do ../aws
cp terraform.tfvars.example terraform.tfvars
# preencha new_relic_account_id, new_relic_api_key e alert_notification_email

terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

## Variáveis e outputs

Ver [`variables.tf`](variables.tf) e [`outputs.tf`](outputs.tf).
