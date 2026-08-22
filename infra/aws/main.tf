# Le automaticamente, via terraform_remote_state contra o mesmo backend S3
# compartilhado (ver infra/backend), os outputs dos outros dois repositorios
# Terraform da Fase 3: cluster/ECR/OIDC do oficina-mecanica-infra-kubernetes e
# endpoint/senha do RDS do oficina-mecanica-infra-banco-dados. Isso elimina a
# necessidade de copiar esses valores manualmente para variables/secrets do
# GitHub a cada apply daqueles repositorios.
data "terraform_remote_state" "kubernetes" {
  backend = "s3"

  config = {
    bucket = var.tf_state_bucket
    key    = var.kubernetes_state_key
    region = var.tf_state_region
  }
}

data "terraform_remote_state" "database" {
  backend = "s3"

  config = {
    bucket = var.tf_state_bucket
    key    = var.database_state_key
    region = var.tf_state_region
  }
}

locals {
  cluster_name = data.terraform_remote_state.kubernetes.outputs.cluster_name

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Course      = "FIAP"
    },
    var.tags,
  )
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.cluster_name}/api"
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    ADMIN_PASSWORD        = var.admin_password
    JWT_SECRET_KEY        = var.jwt_secret_key
    POSTGRES_PASSWORD     = data.terraform_remote_state.database.outputs.rds_password
    SMTP_PASSWORD         = var.smtp_password
    NEW_RELIC_LICENSE_KEY = var.new_relic_license_key
  })
}

data "aws_iam_policy_document" "api_secrets" {
  statement {
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]

    resources = [aws_secretsmanager_secret.app.arn]
  }
}

resource "aws_iam_policy" "api_secrets" {
  count = var.enable_irsa_resources ? 1 : 0

  name   = "${local.cluster_name}-api-secrets"
  policy = data.aws_iam_policy_document.api_secrets.json

  tags = local.common_tags
}

# IRSA role usada pelo ServiceAccount "oficina-mecanica-api" (namespace oficina-mecanica)
# para o External Secrets Operator ler este secret via autenticação por ServiceAccount
# (SecretStore.spec.provider.aws.auth.jwt.serviceAccountRef), sem depender da role
# genérica do controller do External Secrets Operator (criada no repositório
# oficina-mecanica-infra-kubernetes).
module "api_secrets_irsa" {
  count = var.enable_irsa_resources ? 1 : 0

  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${local.cluster_name}-api-secrets"

  role_policy_arns = {
    api_secrets = aws_iam_policy.api_secrets[0].arn
  }

  oidc_providers = {
    main = {
      provider_arn               = data.terraform_remote_state.kubernetes.outputs.oidc_provider_arn
      namespace_service_accounts = ["oficina-mecanica:oficina-mecanica-api"]
    }
  }

  tags = local.common_tags
}
