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

variable "tf_state_bucket" {
  description = "Bucket S3 do backend remoto do Terraform (o mesmo criado por infra/backend), usado para ler via terraform_remote_state os outputs dos repositórios oficina-mecanica-infra-kubernetes e oficina-mecanica-infra-banco-dados."
  type        = string
  default     = "oficina-mecanica-fiap-terraform-state"
}

variable "tf_state_region" {
  description = "Região do backend S3 do state remoto."
  type        = string
  default     = "us-east-1"
}

variable "kubernetes_state_key" {
  description = "Key do state do repositório oficina-mecanica-infra-kubernetes no backend S3 compartilhado. Ajuste para o ambiente real (ex.: kubernetes/homologacao/terraform.tfstate) se o cluster não estiver em kubernetes/dev."
  type        = string
  default     = "kubernetes/dev/terraform.tfstate"
}

variable "database_state_key" {
  description = "Key do state do repositório oficina-mecanica-infra-banco-dados no backend S3 compartilhado. Ajuste para o ambiente real (ex.: database/homologacao/terraform.tfstate) se o banco não estiver em database/dev."
  type        = string
  default     = "database/dev/terraform.tfstate"
}

variable "enable_irsa_resources" {
  description = "Cria a IRSA role do service account da API (api_secrets_irsa). Desabilite em AWS Academy Labs com IAM restrito."
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

variable "tags" {
  description = "Tags adicionais aplicadas aos recursos AWS."
  type        = map(string)
  default     = {}
}
