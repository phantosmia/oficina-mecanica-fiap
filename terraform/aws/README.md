# Terraform AWS

Infraestrutura AWS para executar a aplicação em Kubernetes com:

- VPC dedicada
- Amazon EKS
- node group gerenciado
- Amazon ECR para a imagem da API
- Amazon RDS PostgreSQL
- AWS Secrets Manager para credenciais sensíveis da API
- External Secrets Operator para sincronizar Secrets Manager com Kubernetes Secret
- IAM Role for Service Accounts (IRSA) para o AWS Load Balancer Controller
- instalação do AWS Load Balancer Controller via Helm
- IAM Role OIDC para GitHub Actions publicar imagens no ECR

## Pré-requisitos

- Terraform >= 1.6
- AWS CLI autenticado
- permissões para criar VPC, EKS, ECR, IAM, EC2, RDS e Secrets Manager

## Uso

Antes de aplicar esta stack, crie o backend remoto em `terraform/backend` e gere o arquivo `backend.hcl` a partir de `backend.hcl.example`.

1. Crie o arquivo de variáveis:

`cp terraform.tfvars.example terraform.tfvars`

2. Revise os valores em `terraform.tfvars`.

3. Provisione a infraestrutura:

`terraform init -backend-config=backend.hcl`

`terraform plan`

`terraform apply`

4. Atualize o kubeconfig local:

`terraform output -raw configure_kubectl_command`

Copie o comando exibido e execute-o.

5. Faça login no ECR:

`terraform output -raw ecr_login_command`

6. Gere a URL do repositório ECR:

`terraform output -raw ecr_repository_url`

7. Build e push da imagem:

`docker build -t oficina-mecanica-fiap:latest ../..`

`docker tag oficina-mecanica-fiap:latest <ECR_REPOSITORY_URL>:latest`

`docker push <ECR_REPOSITORY_URL>:latest`

8. Atualize `k8s/overlays/aws/kustomization.yaml` com a URL do ECR.

9. Atualize os placeholders do overlay AWS:

- `REPLACE_WITH_RDS_ENDPOINT` em `k8s/overlays/aws/patch-configmap-rds.yaml`
- `REPLACE_WITH_AWS_REGION` em `k8s/overlays/aws/external-secret.yaml`
- `REPLACE_WITH_APP_SECRET_NAME` em `k8s/overlays/aws/external-secret.yaml`
- `REPLACE_WITH_API_SECRETS_ROLE_ARN` em `k8s/overlays/aws/service-account.yaml`

Os valores podem ser obtidos com:

`terraform output -raw rds_endpoint`

`terraform output -raw app_secret_name`

`terraform output -raw api_secrets_role_arn`

10. Aplique o overlay AWS:

`kubectl apply -k ../../k8s/overlays/aws`

## GitHub Actions e ECR

O workflow `.github/workflows/publish-ecr.yml` publica a imagem da API no ECR via OIDC.

Configure no GitHub:

- secret `AWS_ROLE_TO_ASSUME`: valor de `terraform output -raw github_actions_ecr_role_arn`
- variable `AWS_REGION`: mesma região usada no Terraform
- variable `ECR_REPOSITORY`: nome do repositório ECR, por padrão `oficina-mecanica-fiap`

## AWS Load Balancer Controller

O Terraform cria a IAM role para o service account `kube-system/aws-load-balancer-controller` e instala o controller via Helm por padrão. Para desabilitar essa instalação, defina `install_aws_load_balancer_controller = false` em `terraform.tfvars`.

## Observações

- O cluster é criado com endpoint público para simplificar o bootstrap inicial.
- No overlay AWS, a aplicação usa RDS e o PostgreSQL interno do Kubernetes é removido por patch.
- Senhas e chaves da API são armazenadas no AWS Secrets Manager e sincronizadas para o Kubernetes pelo External Secrets Operator.
- O overlay AWS usa `Ingress` com `ingressClassName: alb`, então depende do AWS Load Balancer Controller instalado no cluster.
