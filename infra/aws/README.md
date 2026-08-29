# Terraform AWS — secrets e identidade da API

Terraform da **aplicação principal** para rodar no cluster Kubernetes:

- AWS Secrets Manager com as credenciais sensíveis da API (senha admin, chave JWT, senha SMTP, senha do Postgres).
- IAM Role for Service Accounts (IRSA) para o ServiceAccount `oficina-mecanica:oficina-mecanica-api` ler esse secret via External Secrets Operator.

**A VPC, o cluster EKS, o node group, o ECR e os add-ons de plataforma (AWS Load Balancer Controller, External Secrets Operator, metrics-server) não são provisionados aqui**: são responsabilidade do repositório [`oficina-mecanica-infra-kubernetes`](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes). O **RDS PostgreSQL também não é provisionado aqui**: é responsabilidade do repositório [`oficina-mecanica-infra-banco-dados`](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados).

## Integração automática via `terraform_remote_state`

Os três repositórios Terraform (este, `oficina-mecanica-infra-kubernetes` e `oficina-mecanica-infra-banco-dados`) compartilham o **mesmo bucket S3** de backend remoto (criado por `infra/backend`), cada um com sua própria `key` de state. Isso permite ler os outputs de um repositório dentro do outro **sem copiar nada manualmente**:

```hcl
data "terraform_remote_state" "kubernetes" {
  backend = "s3"
  config = {
    bucket = var.tf_state_bucket
    key    = var.kubernetes_state_key   # kubernetes/<environment>/terraform.tfstate
    region = var.tf_state_region
  }
}
```

Este Terraform usa isso para obter automaticamente:

| Valor | Origem | Uso aqui |
|---|---|---|
| `cluster_name` | `oficina-mecanica-infra-kubernetes` | nome do secret (`<cluster_name>/api`) e da IRSA role |
| `oidc_provider_arn` | `oficina-mecanica-infra-kubernetes` | `oidc_providers` da IRSA role `api_secrets_irsa` |
| `ecr_repository_url` | `oficina-mecanica-infra-kubernetes` | repassado como output, usado pelo workflow de deploy |
| `rds_password` | `oficina-mecanica-infra-banco-dados` | conteúdo do secret da API (`POSTGRES_PASSWORD`) |
| `rds_endpoint` | `oficina-mecanica-infra-banco-dados` | repassado como output, usado pelo workflow de deploy |

Isso implica uma **ordem de apply**: `oficina-mecanica-infra-banco-dados` → `oficina-mecanica-infra-kubernetes` → este repositório. Se a `key` esperada ainda não existir no bucket (porque o outro repositório nunca foi aplicado naquele ambiente), o `terraform plan`/`apply` falha **imediatamente**, não silenciosamente:

```
Error: Unable to find remote state
No stored state was found for the given workspace in the given backend.
```

A correção é sempre aplicar primeiro o repositório de origem da leitura que falhou, no mesmo ambiente (`dev`/`homologacao`/`producao`) que este repositório está tentando ler (`kubernetes_state_key`/`database_state_key`, ou o input `infra_environment` do workflow `deploy-aws.yml`). Ver o [diagrama de dependência entre os repositórios](../../docs/arquitetura.md#diagrama-de-dependência-entre-os-repositórios-terraform) para a visão completa. O workflow `deploy-aws.yml` já detecta esse erro específico e imprime qual repositório aplicar primeiro.

As variáveis `kubernetes_state_key` e `database_state_key` controlam qual ambiente de cada repositório é lido (default `dev` nos dois); ajuste-as (ou o input `infra_environment` do workflow `deploy-aws.yml`) para consumir `homologacao`/`producao` quando necessário.

Dois valores continuam manuais por não serem dado de state (credenciais de CI e uma decisão explícita de rede, não algo que o Terraform deveria sincronizar sozinho) — ver README do `oficina-mecanica-infra-kubernetes`: a role OIDC do GitHub Actions (`AWS_ROLE_TO_ASSUME`) e o CIDR da VPC do EKS para `allowed_cidr_blocks` no repositório do banco.

## Pré-requisitos

- Terraform >= 1.6
- AWS CLI autenticado
- permissões para criar Secrets Manager e IAM, além de leitura (`s3:GetObject`) no bucket do backend remoto
- cluster EKS já provisionado pelo repositório `oficina-mecanica-infra-kubernetes` no ambiente apontado por `kubernetes_state_key`
- RDS já provisionado pelo repositório `oficina-mecanica-infra-banco-dados` no ambiente apontado por `database_state_key`

## Uso

Antes de aplicar esta stack, crie o backend remoto em `infra/backend` e gere o arquivo `backend.hcl` a partir de `backend.hcl.example`.

1. Crie o arquivo de variáveis:

`cp terraform.tfvars.example terraform.tfvars`

2. Revise os valores em `terraform.tfvars` (os defaults já cobrem o ambiente `dev`).

3. Provisione a infraestrutura:

`terraform init -backend-config=backend.hcl`

`terraform plan`

`terraform apply`

4. Atualize os placeholders do overlay AWS em `k8s/overlays/aws`:

- `REPLACE_WITH_RDS_ENDPOINT` em `patch-configmap-rds.yaml` — `terraform output -raw rds_endpoint` (deste repositório, repassado do repositório do banco).
- `REPLACE_WITH_AWS_REGION` em `external-secret.yaml` — região AWS do cluster.
- `REPLACE_WITH_APP_SECRET_NAME` em `external-secret.yaml` — `terraform output -raw app_secret_name`.
- `REPLACE_WITH_API_SECRETS_ROLE_ARN` em `service-account.yaml` — `terraform output -raw api_secrets_role_arn`.
- `REPLACE_WITH_ECR_REPOSITORY_URL` em `kustomization.yaml` — `terraform output -raw ecr_repository_url` (repassado do repositório de Kubernetes).

5. Configure o kubeconfig usando o cluster provisionado pelo repositório `oficina-mecanica-infra-kubernetes`:

`aws eks update-kubeconfig --region <região> --name $(terraform output -raw cluster_name)`

6. Faça login no ECR e publique a imagem:

`aws ecr get-login-password --region <região> | docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url | cut -d/ -f1)`

`docker build -t oficina-mecanica-fiap:latest ../..`

`docker tag oficina-mecanica-fiap:latest $(terraform output -raw ecr_repository_url):latest`

`docker push $(terraform output -raw ecr_repository_url):latest`

7. Aplique o overlay AWS:

`kubectl apply -k ../../k8s/overlays/aws`

## GitHub Actions e ECR

O workflow `.github/workflows/publish-ecr.yml` publica a imagem da API no ECR criado pelo repositório `oficina-mecanica-infra-kubernetes`, via OIDC.

Configure no GitHub:

- secret `AWS_ROLE_TO_ASSUME`: valor de `terraform output -raw github_actions_ecr_role_arn` **do repositório `oficina-mecanica-infra-kubernetes`** (não pode ser lido via remote state porque é uma credencial de CI, não dado de infraestrutura)
- variable `AWS_REGION`: mesma região usada no Terraform
- variable `ECR_REPOSITORY`: nome do repositório ECR, por padrão `oficina-mecanica-fiap`

## GitHub Actions e deploy no EKS

O workflow `.github/workflows/deploy-aws.yml` executa o deploy no EKS. Ele só provisiona os recursos deste diretório (secret + IRSA da API); cluster, node group e ECR já precisam existir, provisionados separadamente pelo repositório `oficina-mecanica-infra-kubernetes`. Todos os valores de integração (`cluster_name`, `ecr_repository_url`, `oidc_provider_arn`, `rds_endpoint`, `rds_password`) são lidos automaticamente via `terraform_remote_state` — não há mais variables `CLUSTER_NAME`, `ECR_REPOSITORY_URL`, `EKS_OIDC_PROVIDER_ARN`, `RDS_ENDPOINT` ou secret `POSTGRES_PASSWORD` no GitHub.

Dois modos de disparo:

- **Automático**: push nas branches `homologacao` ou `producao` (deploy automático exigido pelo PDF da Fase 3, mesmo padrão dos outros 3 repositórios do projeto). O ambiente GitHub usado é o nome da branch (`homologacao`/`producao`), `infra_environment` vira o nome da branch, o modo de autenticação é `aws-academy` (via variable `AWS_AUTH_MODE`, default `aws-academy`) e a imagem é taggeada com o SHA do commit. `terraform apply` roda sempre (necessário para criar secret/IRSA na primeira execução em um ambiente novo).
- **Manual**: `workflow_dispatch`, com os inputs abaixo (comportamento inalterado, ambiente GitHub fixo `aws`):
  - `terraform_apply=false`: apenas lê o state remoto deste repositório, prepara o overlay AWS e roda `kubectl apply -k k8s/overlays/aws`
  - `terraform_apply=true`: executa `terraform apply -auto-approve` (deste diretório) antes do deploy Kubernetes
  - `infra_environment` (default `dev`): controla qual ambiente do cluster/banco é lido via remote state (`kubernetes/<infra_environment>/terraform.tfstate` e `database/<infra_environment>/terraform.tfstate`). Use `homologacao`/`producao` para apontar para esses ambientes.

> **Antes do primeiro push automático em `homologacao`/`producao`**: configure os secrets abaixo no [GitHub Environment](https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment) com o mesmo nome da branch (ou no repositório, se preferir compartilhar entre ambientes) — hoje eles só existem no ambiente `aws`, usado pelo fluxo manual. Sem isso, o job falha logo nos primeiros steps (credenciais AWS ausentes).

Configure no GitHub (no ambiente `aws` para o fluxo manual; em `homologacao`/`producao` — ou no repositório — para o fluxo automático):

- secret `AWS_DEPLOY_ROLE_TO_ASSUME`: role OIDC com permissões para Terraform (Secrets Manager/IAM), leitura do backend S3 dos outros dois repositórios e para o EKS. Se não existir, o workflow usa `AWS_ROLE_TO_ASSUME`. Não se aplica ao modo `aws-academy` (usado automaticamente por `homologacao`/`producao`).
- secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`: credenciais temporárias do AWS Academy Lab, usadas no modo `aws-academy`. Expiram em poucas horas — atualize-as antes de cada push que deva disparar um deploy real.
- secret `TF_BACKEND_CONFIG`: conteúdo completo do `backend.hcl`. Alternativamente, configure as variables `TF_STATE_BUCKET`, `TF_STATE_REGION` e `TF_LOCK_TABLE` (a `key` já é calculada automaticamente como `aws/<ambiente>/terraform.tfstate`).
- secrets `ADMIN_PASSWORD`, `JWT_SECRET_KEY`, `SMTP_PASSWORD` e `NEW_RELIC_LICENSE_KEY` (ADR-0007): valores gravados em `terraform.auto.tfvars.json` durante o workflow quando estiverem configurados. `NEW_RELIC_LICENSE_KEY` vazia desabilita o agente APM sem quebrar a aplicação.
- variable `AWS_REGION`: região do EKS/ECR.
- variable `PUBLIC_BASE_URL`: URL pública da API usada nos e-mails, caso o input `public_base_url` não seja informado (só é exigida no modo `aws`; `aws-academy` usa o hostname do LoadBalancer automaticamente).

Se nem o input `public_base_url` nem a variable `PUBLIC_BASE_URL` forem informados no modo `aws`, o workflow falha antes de aplicar os manifests.

O workflow substitui automaticamente no overlay AWS os valores de ECR, RDS, Secrets Manager, IRSA e região. Antes de aplicar o overlay, ele remove o Job `oficina-mecanica-migrations` para garantir que as migrations da nova imagem sejam executadas novamente.

## AWS Academy Lab

No modo `aws-academy`, a IRSA role deste repositório não é criada (`enable_irsa_resources = false`), já que o lab bloqueia os recursos IAM necessários. Nesse modo, o workflow cria a Secret Kubernetes diretamente a partir do AWS Secrets Manager (via `aws secretsmanager get-secret-value` + `kubectl create secret`), sem depender de IRSA/External Secrets Operator — ver [`k8s/overlays/aws-academy`](../../k8s/overlays/aws-academy). A leitura de `cluster_name`, `ecr_repository_url` e `rds_endpoint` via remote state continua funcionando normalmente em ambos os modos.

## Observações

- Senhas e chaves da API são armazenadas no AWS Secrets Manager e sincronizadas para o Kubernetes pelo External Secrets Operator (modo `aws`) ou por um Secret criado diretamente pelo workflow (modo `aws-academy`).
- Este diretório depende dos outputs dos outros dois repositórios Terraform via `terraform_remote_state` (não por cópia manual de variables/secrets do GitHub). A ordem de apply importa: banco → cluster → este repositório.
