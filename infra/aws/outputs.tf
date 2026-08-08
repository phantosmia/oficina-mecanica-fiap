output "app_secret_arn" {
  description = "ARN do secret do Secrets Manager com credenciais sensíveis da API."
  value       = aws_secretsmanager_secret.app.arn
}

output "app_secret_name" {
  description = "Nome do secret do Secrets Manager consumido pelo External Secrets Operator."
  value       = aws_secretsmanager_secret.app.name
}

output "api_secrets_role_arn" {
  description = "Role IRSA usada pelo service account da API para permitir leitura via External Secrets."
  value       = try(module.api_secrets_irsa[0].iam_role_arn, null)
}
