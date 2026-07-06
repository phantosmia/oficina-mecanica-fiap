output "cluster_name" {
  description = "Nome final do cluster EKS."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint do cluster EKS."
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group principal do cluster EKS."
  value       = module.eks.cluster_security_group_id
}

output "vpc_id" {
  description = "ID da VPC criada para o EKS."
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Subnets privadas usadas pelos nós do EKS."
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Subnets públicas usadas pelos load balancers do cluster."
  value       = module.vpc.public_subnets
}

output "ecr_repository_name" {
  description = "Nome do repositório ECR da API."
  value       = aws_ecr_repository.api.name
}

output "ecr_repository_url" {
  description = "URL completa do repositório ECR da API."
  value       = aws_ecr_repository.api.repository_url
}

output "configure_kubectl_command" {
  description = "Comando para atualizar o kubeconfig local para o cluster criado."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "ecr_login_command" {
  description = "Comando para autenticar o Docker no ECR."
  value       = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${split("/", aws_ecr_repository.api.repository_url)[0]}"
}

output "rds_endpoint" {
  description = "Endpoint DNS do RDS PostgreSQL."
  value       = aws_db_instance.postgres.address
}

output "rds_port" {
  description = "Porta do RDS PostgreSQL."
  value       = aws_db_instance.postgres.port
}

output "rds_database_name" {
  description = "Nome do database PostgreSQL no RDS."
  value       = aws_db_instance.postgres.db_name
}

output "rds_username" {
  description = "Usuário PostgreSQL no RDS."
  value       = aws_db_instance.postgres.username
}

output "rds_secret_arn" {
  description = "ARN do secret do Secrets Manager com as credenciais do RDS."
  value       = aws_secretsmanager_secret.rds.arn
}

output "app_secret_arn" {
  description = "ARN do secret do Secrets Manager com credenciais sensíveis da API."
  value       = aws_secretsmanager_secret.app.arn
}

output "app_secret_name" {
  description = "Nome do secret do Secrets Manager consumido pelo External Secrets Operator."
  value       = aws_secretsmanager_secret.app.name
}

output "aws_load_balancer_controller_role_arn" {
  description = "Role IRSA para o service account do AWS Load Balancer Controller."
  value       = try(module.aws_load_balancer_controller_irsa[0].iam_role_arn, null)
}

output "github_actions_ecr_role_arn" {
  description = "Role IAM para GitHub Actions publicar a imagem no ECR via OIDC."
  value       = try(aws_iam_role.github_actions_ecr[0].arn, null)
}

output "external_secrets_role_arn" {
  description = "Role IRSA usada pelo External Secrets Operator para ler Secrets Manager."
  value       = try(module.external_secrets_irsa[0].iam_role_arn, null)
}

output "api_secrets_role_arn" {
  description = "Role IRSA usada pelo service account da API para permitir leitura via External Secrets."
  value       = try(module.api_secrets_irsa[0].iam_role_arn, null)
}
