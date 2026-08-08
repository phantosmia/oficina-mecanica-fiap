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

variable "eks_admin_principal_arn" {
  description = "ARN IAM que receberá acesso administrativo ao EKS. Útil no AWS Academy, onde iam:GetRole da role voclabs pode ser bloqueado."
  type        = string
  default     = ""
}

variable "eks_cluster_role_arn" {
  description = "ARN de uma IAM role existente para o control plane do EKS. Use em labs que bloqueiam iam:CreateRole."
  type        = string
  default     = ""
}

variable "eks_node_role_arn" {
  description = "ARN de uma IAM role existente para o node group do EKS. Use em labs que bloqueiam iam:CreateRole."
  type        = string
  default     = ""
}

variable "enable_irsa_resources" {
  description = "Cria recursos IAM/OIDC/IRSA para controllers e secrets. Desabilite em AWS Academy Labs com IAM restrito."
  type        = bool
  default     = true
}

variable "enable_github_actions_oidc" {
  description = "Cria OIDC provider e role para GitHub Actions publicar no ECR. Desabilite em AWS Academy Labs com IAM restrito."
  type        = bool
  default     = true
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

variable "rds_secret_arn" {
  description = "ARN do secret do Secrets Manager com as credenciais do RDS, provisionado pelo repositório oficina-mecanica-infra-banco-dados."
  type        = string
  default     = ""
}

variable "postgres_password" {
  description = "Senha do RDS PostgreSQL, copiada do output rds_password do repositório oficina-mecanica-infra-banco-dados."
  type        = string
  sensitive   = true
  default     = ""
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
