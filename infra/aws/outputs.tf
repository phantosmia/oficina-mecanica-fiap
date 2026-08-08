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

# Repassados do state remoto dos outros dois repositórios (ver data.terraform_remote_state
# em main.tf), para que o workflow de deploy não precise ler outputs de dois lugares.

output "cluster_name" {
  description = "Nome do cluster EKS, lido via terraform_remote_state do repositório oficina-mecanica-infra-kubernetes."
  value       = local.cluster_name
}

output "ecr_repository_url" {
  description = "URL do repositório ECR, lido via terraform_remote_state do repositório oficina-mecanica-infra-kubernetes."
  value       = data.terraform_remote_state.kubernetes.outputs.ecr_repository_url
}

output "rds_endpoint" {
  description = "Endpoint do RDS, lido via terraform_remote_state do repositório oficina-mecanica-infra-banco-dados."
  value       = data.terraform_remote_state.database.outputs.rds_endpoint
}
