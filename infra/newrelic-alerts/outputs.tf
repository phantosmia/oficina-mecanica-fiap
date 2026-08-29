output "alert_policy_id" {
  description = "ID da policy de alertas (útil pra linkar de outros lugares, ex.: dashboards)."
  value       = newrelic_alert_policy.oficina_mecanica.id
}

output "workflow_id" {
  description = "ID do workflow de notificação (e-mail)."
  value       = newrelic_workflow.oficina_mecanica.id
}
