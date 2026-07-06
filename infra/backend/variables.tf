variable "aws_region" {
  description = "Região AWS onde o backend remoto será criado."
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Nome globalmente único do bucket S3 para o state do Terraform."
  type        = string
}

variable "lock_table_name" {
  description = "Nome da tabela DynamoDB usada para lock do state."
  type        = string
  default     = "oficina-mecanica-fiap-terraform-locks"
}

variable "force_destroy" {
  description = "Permite destruir o bucket mesmo com objetos dentro. Use false em ambientes reais."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags aplicadas ao bucket e à tabela de lock."
  type        = map(string)
  default = {
    Project   = "oficina-mecanica-fiap"
    ManagedBy = "Terraform"
  }
}
