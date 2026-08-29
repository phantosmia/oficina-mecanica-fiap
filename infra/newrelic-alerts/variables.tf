variable "new_relic_account_id" {
  description = "Account ID do New Relic."
  type        = string
}

variable "new_relic_api_key" {
  description = "User API key do New Relic (prefixo NRAK-) — diferente da license key (ingest) usada pelos agentes."
  type        = string
  sensitive   = true
}

variable "new_relic_region" {
  description = "Região da conta New Relic (US ou EU)."
  type        = string
  default     = "US"
}

variable "app_name" {
  description = "NEW_RELIC_APP_NAME configurado na aplicação principal (k8s/base/configmap.yaml, oficina-mecanica-fiap)."
  type        = string
  default     = "oficina-mecanica-api"
}

variable "alert_notification_email" {
  description = "E-mail que recebe as notificações de todos os alertas deste root (canal único, ver README)."
  type        = string
}

variable "service_order_failure_critical_threshold" {
  description = "Nº de TransactionError em rotas /service-orders* na janela de 5 min a partir do qual a condição abre violação crítica."
  type        = number
  default     = 3
}

variable "service_order_failure_warning_threshold" {
  description = "Nº de TransactionError em rotas /service-orders* na janela de 5 min a partir do qual a condição abre violação de warning."
  type        = number
  default     = 1
}

variable "api_error_rate_critical_percent" {
  description = "Taxa de erro (%) da API acima da qual a condição abre violação crítica. Mesmo limiar do widget 'Taxa de erro da API' em newrelic-dashboards, para os dois ficarem consistentes."
  type        = number
  default     = 5
}

variable "api_error_rate_warning_percent" {
  description = "Taxa de erro (%) da API acima da qual a condição abre violação de warning. Mesmo limiar do widget 'Taxa de erro da API' em newrelic-dashboards."
  type        = number
  default     = 1
}

variable "healthcheck_uptime_critical_percent" {
  description = "Uptime (%) do /health abaixo do qual a condição abre violação crítica. Mesmo limiar do widget 'Uptime do healthcheck' em newrelic-dashboards."
  type        = number
  default     = 95
}

variable "healthcheck_uptime_warning_percent" {
  description = "Uptime (%) do /health abaixo do qual a condição abre violação de warning. Mesmo limiar do widget 'Uptime do healthcheck' em newrelic-dashboards."
  type        = number
  default     = 99
}
