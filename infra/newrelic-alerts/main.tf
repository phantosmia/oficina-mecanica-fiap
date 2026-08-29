# Alertas exigidos pela Fase 3 do Tech Challenge (PDF, seção "Monitoramento
# e Observabilidade" → "Alertas para falhas no processamento de ordens de
# serviço"), mais dois alertas que cobrem os outros itens da mesma seção
# ("Healthchecks e uptime" e uma leitura geral de "Latência das APIs" via
# taxa de erro) — os três usam dado que a APM (agente New Relic Python,
# ADR-0007) já captura sozinha em `Transaction`/`TransactionError`, sem
# exigir nenhum evento customizado novo em app/shared/telemetry.py.
#
# Os limiares de "Taxa de erro geral" e "Healthcheck" replicam de propósito
# os mesmos números já usados nos widgets de newrelic-dashboards (critical/
# warning dos widget_billboard) — os dois roots ficam consistentes entre si.
resource "newrelic_alert_policy" "oficina_mecanica" {
  name                = "Oficina Mecânica — Alertas (Fase 3)"
  incident_preference = "PER_POLICY"
}

# --- Canal de notificação (e-mail único para todas as condições) ----------

resource "newrelic_notification_destination" "email" {
  account_id = var.new_relic_account_id
  name       = "Oficina Mecânica — E-mail"
  type       = "EMAIL"

  property {
    key   = "email"
    value = var.alert_notification_email
  }
}

resource "newrelic_notification_channel" "email" {
  account_id     = var.new_relic_account_id
  name           = "Oficina Mecânica — E-mail"
  type           = "EMAIL"
  product        = "IINT"
  destination_id = newrelic_notification_destination.email.id

  property {
    key   = "subject"
    value = "[Oficina Mecânica] {{ issueTitle }}"
  }
}

resource "newrelic_workflow" "oficina_mecanica" {
  account_id            = var.new_relic_account_id
  name                  = "Oficina Mecânica — Alertas (Fase 3)"
  muting_rules_handling = "NOTIFY_ALL_ISSUES"

  issues_filter {
    name = "filter-by-policy"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values    = [newrelic_alert_policy.oficina_mecanica.id]
    }
  }

  destination {
    channel_id = newrelic_notification_channel.email.id
  }
}

# --- Condição 1: falhas no processamento de ordens de serviço -------------
# Requisito literal do PDF. TransactionError já é capturado pela APM para
# qualquer exceção não tratada / resposta 5xx nas rotas /service-orders*
# (diagnóstico, orçamento, aprovação, execução, finalização, entrega).
resource "newrelic_nrql_alert_condition" "service_order_failures" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.oficina_mecanica.id
  type                         = "static"
  name                         = "Falhas no processamento de ordens de serviço"
  description                  = "Dispara quando rotas /service-orders* (diagnóstico, orçamento, aprovação, execução, finalização, entrega) retornam erro."
  enabled                      = true
  violation_time_limit_seconds = 3600

  nrql {
    query = "SELECT count(*) FROM TransactionError WHERE appName = '${var.app_name}' AND request.uri LIKE '/service-orders%'"
  }

  critical {
    operator              = "above"
    threshold             = var.service_order_failure_critical_threshold
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = var.service_order_failure_warning_threshold
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
}

# --- Condição 2: taxa de erro geral da API elevada -------------------------
# Mesma query/limiares do widget "Taxa de erro da API" (newrelic-dashboards),
# como sinal amplo de gargalo/degradação em tempo real (desafio da Fase 3).
resource "newrelic_nrql_alert_condition" "api_error_rate" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.oficina_mecanica.id
  type                         = "static"
  name                         = "Taxa de erro geral da API elevada"
  description                  = "Dispara quando a taxa de erro de todas as rotas da API ultrapassa o limiar."
  enabled                      = true
  violation_time_limit_seconds = 3600

  nrql {
    query = "SELECT percentage(count(*), WHERE error is true) FROM Transaction WHERE appName = '${var.app_name}'"
  }

  critical {
    operator              = "above"
    threshold             = var.api_error_rate_critical_percent
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = var.api_error_rate_warning_percent
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
}

# --- Condição 3: healthcheck/uptime abaixo do limiar -----------------------
# Mesma query/limiares do widget "Uptime do healthcheck" (newrelic-dashboards).
resource "newrelic_nrql_alert_condition" "healthcheck_uptime" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.oficina_mecanica.id
  type                         = "static"
  name                         = "Healthcheck /health abaixo do uptime esperado"
  description                  = "Dispara quando o uptime do /health cai abaixo do limiar."
  enabled                      = true
  violation_time_limit_seconds = 3600

  nrql {
    query = "SELECT percentage(count(*), WHERE httpResponseCode < '400') FROM Transaction WHERE appName = '${var.app_name}' AND request.uri = '/health'"
  }

  critical {
    operator              = "below"
    threshold             = var.healthcheck_uptime_critical_percent
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "below"
    threshold             = var.healthcheck_uptime_warning_percent
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
}
