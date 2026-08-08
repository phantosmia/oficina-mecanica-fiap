# Terraform AWS — secrets e identidade da API

Terraform da **aplicação principal** para rodar no cluster Kubernetes:

- AWS Secrets Manager com as credenciais sensíveis da API (senha admin, chave JWT, senha SMTP, senha do Postgres).
- IAM Role for Service Accounts (IRSA) para o ServiceAccount `oficina-mecanica:oficina-mecanica-api` ler esse secret via External Secrets Operator.

**A VPC, o cluster EKS, o node group, o ECR e os add-ons de plataforma (AWS Load Balancer Controller, External Secrets Operator, metrics-server) não são provisionados aqui**: são responsabilidade do repositório [`oficina-mecanica-infra-kubernetes`](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes), conforme a separação de repositórios exigida pela Fase 3 do Tech Challenge. Este Terraform só consome o `oidc_provider_arn` daquele cluster via a variável `eks_oidc_provider_arn`.

O **RDS PostgreSQL também não é provisionado aqui**: é responsabilidade do repositório [`oficina-mecanica-infra-banco-dados`](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados), que expõe o endpoint e as credenciais via Secrets Manager. Este Terraform só consome a senha via a variável `postgres_password`, para incluí-la no secret da API.

## Pré-requisitos

- Terraform >= 1.6
- AWS CLI autenticado
- permissões para criar Secrets Manager e IAM
- cluster EKS já provisionado pelo repositório `oficina-mecanica-infra-kubernetes`, com o output `oidc_provider_arn` em mãos
- RDS já provisionado pelo repositório `oficina-mecanica-infra-banco-dados`, com o output `rds_password` em mãos

## Uso

Antes de aplicar esta stack, crie o backend remoto em `infra/backend` e gere o arquivo `backend.hcl` a partir de `backend.hcl.example`.

1. Crie o arquivo de variáveis:

`cp terraform.tfvars.example terraform.tfvars`

2. Revise os valores em `terraform.tfvars`.

3. Provisione a infraestrutura:

`terraform init -backend-config=backend.hcl`

`terraform plan`

`terraform apply`

4. Atualize os placeholders do overlay AWS em `k8s/overlays/aws`:

- `REPLACE_WITH_RDS_ENDPOINT` em `patch-configmap-rds.yaml` — output `rds_endpoint` do repositório `oficina-mecanica-infra-banco-dados`.
- `REPLACE_WITH_AWS_REGION` em `external-secret.yaml` — região AWS do cluster.
- `REPLACE_WITH_APP_SECRET_NAME` em `external-secret.yaml` — `terraform output -raw app_secret_name` (deste repositório).
- `REPLACE_WITH_API_SECRETS_ROLE_ARN` em `service-account.yaml` — `terraform output -raw api_secrets_role_arn` (deste repositório).
- `REPLACE_WITH_ECR_REPOSITORY_URL` em `kustomization.yaml` — output `ecr_repository_url` do repositório `oficina-mecanica-infra-kubernetes`.

5. Configure o kubeconfig usando o cluster provisionado pelo repositório `oficina-mecanica-infra-kubernetes`:

`aws eks update-kubeconfig --region <região> --name <cluster_name>`

6. Faça login no ECR e publique a imagem, usando a URL do ECR daquele repositório:

`aws ecr get-login-password --region <região> | docker login --username AWS --password-stdin <registry>`

`docker build -t oficina-mecanica-fiap:latest ../..`

`docker tag oficina-mecanica-fiap:latest <ECR_REPOSITORY_URL>:latest`

`docker push <ECR_REPOSITORY_URL>:latest`

7. Aplique o overlay AWS:

`kubectl apply -k ../../k8s/overlays/aws`

## GitHub Actions e ECR

O workflow `.github/workflows/publish-ecr.yml` publica a imagem da API no ECR criado pelo repositório `oficina-mecanica-infra-kubernetes`, via OIDC.

Configure no GitHub:

- secret `AWS_ROLE_TO_ASSUME`: valor de `terraform output -raw github_actions_ecr_role_arn` **do repositório `oficina-mecanica-infra-kubernetes`**
- variable `AWS_REGION`: mesma região usada no Terraform
- variable `ECR_REPOSITORY`: nome do repositório ECR, por padrão `oficina-mecanica-fiap`

## GitHub Actions e deploy no EKS

O workflow `.github/workflows/deploy-aws.yml` executa deploy manual no EKS com `workflow_dispatch`. Ele só provisiona os recursos deste diretório (secret + IRSA da API); cluster, node group e ECR já precisam existir, provisionados separadamente pelo repositório `oficina-mecanica-infra-kubernetes`.

Modos de execução:

- `terraform_apply=false`: apenas lê o state remoto deste repositório, prepara o overlay AWS e roda `kubectl apply -k k8s/overlays/aws`
- `terraform_apply=true`: executa `terraform apply -auto-approve` (deste diretório) antes do deploy Kubernetes

Configure no GitHub:

- secret `AWS_DEPLOY_ROLE_TO_ASSUME`: role OIDC com permissões para Terraform (Secrets Manager/IAM) e para o EKS. Se não existir, o workflow usa `AWS_ROLE_TO_ASSUME`.
- secret `TF_BACKEND_CONFIG`: conteúdo completo do `backend.hcl`. Alternativamente, configure as variables `TF_STATE_BUCKET`, `TF_STATE_KEY`, `TF_STATE_REGION` e `TF_LOCK_TABLE`.
- secrets `ADMIN_PASSWORD`, `JWT_SECRET_KEY`, `SMTP_PASSWORD` e `POSTGRES_PASSWORD`: valores gravados em `terraform.auto.tfvars.json` durante o workflow quando estiverem configurados. `POSTGRES_PASSWORD` vem do output `rds_password` do repositório `oficina-mecanica-infra-banco-dados`.
- variable `CLUSTER_NAME`: nome do cluster, output `cluster_name` do repositório `oficina-mecanica-infra-kubernetes`.
- variable `ECR_REPOSITORY_URL`: URL do repositório ECR, output `ecr_repository_url` do mesmo repositório.
- variable `EKS_OIDC_PROVIDER_ARN`: ARN do provider OIDC do cluster, output `oidc_provider_arn` do mesmo repositório — usado para criar a IRSA role do service account da API.
- variable `RDS_ENDPOINT`: endpoint do RDS, output `rds_endpoint` do repositório `oficina-mecanica-infra-banco-dados` — usado para substituir `REPLACE_WITH_RDS_ENDPOINT` no overlay Kubernetes.
- variable `AWS_REGION`: região do EKS/ECR.
- variable `PUBLIC_BASE_URL`: URL pública da API usada nos e-mails, caso o input `public_base_url` não seja informado.

Se nem o input `public_base_url` nem a variable `PUBLIC_BASE_URL` forem informados, o workflow falha antes de aplicar os manifests. O mesmo vale para `CLUSTER_NAME` e `ECR_REPOSITORY_URL`.

O workflow substitui automaticamente no overlay AWS os valores de ECR, RDS, Secrets Manager, IRSA e região. Antes de aplicar o overlay, ele remove o Job `oficina-mecanica-migrations` para garantir que as migrations da nova imagem sejam executadas novamente.

## AWS Academy Lab

No modo `aws-academy`, a IRSA role deste repositório não é criada (`enable_irsa_resources = false`), já que o lab bloqueia os recursos IAM necessários. Nesse modo, o workflow cria a Secret Kubernetes diretamente a partir do AWS Secrets Manager (via `aws secretsmanager get-secret-value` + `kubectl create secret`), sem depender de IRSA/External Secrets Operator — ver [`k8s/overlays/aws-academy`](../../k8s/overlays/aws-academy).

## Observações

- Senhas e chaves da API são armazenadas no AWS Secrets Manager e sincronizadas para o Kubernetes pelo External Secrets Operator (modo `aws`) ou por um Secret criado diretamente pelo workflow (modo `aws-academy`).
- Este diretório depende dos outputs do repositório `oficina-mecanica-infra-kubernetes` (cluster, ECR, OIDC provider) e do repositório `oficina-mecanica-infra-banco-dados` (senha do RDS). A sincronização desses valores entre repositórios é manual, via variables/secrets do GitHub — ver tabela em [docs/testes-carga-ci.md](../../docs/testes-carga-ci.md).
