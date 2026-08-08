variable "project_name" {
  description = "Nome lógico do projeto para tags e nomes de recursos."
  type        = string
  default     = "oficina-mecanica-fiap"
}

variable "environment" {
  description = "Identificador do ambiente AWS."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "Região AWS onde os recursos serão provisionados."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Nome do cluster EKS. Deve ser igual ao output cluster_name do repositório oficina-mecanica-infra-kubernetes (ou vazio, para usar <project_name>-<environment>, que é o default daquele repositório também)."
  type        = string
  default     = ""
}

variable "eks_oidc_provider_arn" {
  description = "ARN do provider OIDC do cluster EKS, output oidc_provider_arn do repositório oficina-mecanica-infra-kubernetes. Necessário para criar a IRSA role do service account da API."
  type        = string
  default     = ""
}

variable "enable_irsa_resources" {
  description = "Cria a IRSA role do service account da API (api_secrets_irsa). Desabilite em AWS Academy Labs com IAM restrito ou quando eks_oidc_provider_arn ainda não estiver disponível."
  type        = bool
  default     = true
}

variable "jwt_secret_key" {
  description = "Chave JWT usada pela API no overlay AWS."
  type        = string
  sensitive   = true
  default     = "change-me-in-production"
}

variable "admin_password" {
  description = "Senha administrativa usada pela API no overlay AWS."
  type        = string
  sensitive   = true
  default     = "Admin@123"
}

variable "smtp_password" {
  description = "Senha SMTP usada pela API no overlay AWS."
  type        = string
  sensitive   = true
  default     = ""
}

variable "postgres_password" {
  description = "Senha do RDS PostgreSQL, copiada do output rds_password do repositório oficina-mecanica-infra-banco-dados."
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Tags adicionais aplicadas aos recursos AWS."
  type        = map(string)
  default     = {}
}
