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
  description = "Nome do cluster EKS. Se vazio, usa <project_name>-<environment>."
  type        = string
  default     = ""
}

variable "kubernetes_version" {
  description = "Versão do Kubernetes no EKS."
  type        = string
  default     = "1.30"
}

variable "vpc_cidr" {
  description = "Bloco CIDR da VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_instance_types" {
  description = "Tipos de instância EC2 para os nós gerenciados do EKS."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Quantidade desejada de nós do node group padrão."
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Quantidade mínima de nós do node group padrão."
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Quantidade máxima de nós do node group padrão."
  type        = number
  default     = 3
}

variable "node_disk_size" {
  description = "Tamanho do disco dos nós gerenciados do EKS, em GiB."
  type        = number
  default     = 30
}

variable "ecr_repository_name" {
  description = "Nome do repositório ECR que armazenará a imagem da API."
  type        = string
  default     = "oficina-mecanica-fiap"
}

variable "ecr_force_delete" {
  description = "Remove imagens do ECR ao destruir o repositório."
  type        = bool
  default     = false
}

variable "rds_instance_class" {
  description = "Classe da instância RDS PostgreSQL."
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_allocated_storage" {
  description = "Armazenamento inicial do RDS, em GiB."
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "Armazenamento máximo para autoscaling do RDS, em GiB."
  type        = number
  default     = 100
}

variable "rds_engine_version" {
  description = "Versão do PostgreSQL no RDS."
  type        = string
  default     = "16.3"
}

variable "rds_database_name" {
  description = "Nome do database PostgreSQL usado pela aplicação."
  type        = string
  default     = "oficina_mecanica"
}

variable "rds_username" {
  description = "Usuário master do PostgreSQL no RDS."
  type        = string
  default     = "oficina"
}

variable "rds_backup_retention_period" {
  description = "Retenção de backups automáticos do RDS, em dias."
  type        = number
  default     = 7
}

variable "rds_deletion_protection" {
  description = "Protege a instância RDS contra deleção acidental."
  type        = bool
  default     = false
}

variable "rds_skip_final_snapshot" {
  description = "Pula snapshot final ao destruir o RDS. Use false em produção."
  type        = bool
  default     = true
}

variable "github_repository" {
  description = "Repositório GitHub autorizado a publicar imagens no ECR via OIDC, no formato owner/repo."
  type        = string
  default     = "phantosmia/oficina-mecanica-fiap"
}

variable "github_branch" {
  description = "Branch autorizada a publicar imagens no ECR via OIDC."
  type        = string
  default     = "main"
}

variable "install_aws_load_balancer_controller" {
  description = "Instala o AWS Load Balancer Controller no EKS via Helm."
  type        = bool
  default     = true
}

variable "aws_load_balancer_controller_chart_version" {
  description = "Versão do chart Helm do AWS Load Balancer Controller."
  type        = string
  default     = "1.8.1"
}

variable "install_external_secrets_operator" {
  description = "Instala o External Secrets Operator no EKS via Helm."
  type        = bool
  default     = true
}

variable "external_secrets_chart_version" {
  description = "Versão do chart Helm do External Secrets Operator."
  type        = string
  default     = "0.10.5"
}

variable "install_metrics_server" {
  description = "Instala o metrics-server no EKS via Helm para habilitar HPA por CPU/memória."
  type        = bool
  default     = true
}

variable "metrics_server_chart_version" {
  description = "Versão do chart Helm do metrics-server."
  type        = string
  default     = "3.12.1"
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
