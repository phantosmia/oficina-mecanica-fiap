# Kubernetes e AWS

## Kubernetes local

Os manifests Kubernetes estão organizados em base e overlays:

- `k8s/base`: recursos comuns da aplicação
- `k8s/overlays/local`: exposição da API via `NodePort`, útil para Minikube
- `k8s/overlays/aws`: exposição da API via `Ingress` com AWS Load Balancer Controller
- `k8s/overlays/aws-academy`: modo compatível com AWS Academy Lab, usando `Service` `LoadBalancer`

A stack Kubernetes contém:

- `Namespace` dedicado (`oficina-mecanica`)
- `ConfigMap` para variáveis não sensíveis
- `Secret` para senha do banco, senha administrativa, chave JWT e senha SMTP
- `StatefulSet` + `Service` para PostgreSQL 16 no ambiente local
- `Job` para aplicar migrations do Alembic antes da API atender tráfego
- `Deployment` + `Service` para a API FastAPI
- 2 réplicas da API nos overlays
- `HorizontalPodAutoscaler` para escalar a API de 2 a 5 pods por CPU/memória
- probes de startup, readiness e liveness em `/health`

## Build da imagem

Para deploy em AWS ou qualquer cluster remoto, publique a imagem no registry desejado.

```bash
docker login
docker build -t SEU_USUARIO_DOCKERHUB/oficina-mecanica-fiap:latest .
docker push SEU_USUARIO_DOCKERHUB/oficina-mecanica-fiap:latest
```

Os overlays `k8s/overlays/local` e `k8s/overlays/aws` podem ser ajustados pelo `kustomization.yaml` para apontar para a imagem correta.

## Aplicar no Minikube

Antes de testar HPA em Minikube, habilite o metrics-server:

```bash
minikube addons enable metrics-server
```

Remova o Job anterior de migrations e aplique o overlay local:

```bash
kubectl delete job oficina-mecanica-migrations -n oficina-mecanica --ignore-not-found
kubectl apply -k k8s/overlays/local
```

Acompanhe os pods:

```bash
kubectl get pods -n oficina-mecanica -w
```

Verifique migrations:

```bash
kubectl get job oficina-mecanica-migrations -n oficina-mecanica
kubectl logs job/oficina-mecanica-migrations -n oficina-mecanica
```

Verifique Deployment, ReplicaSet e pods da API:

```bash
kubectl get deployment oficina-mecanica-api -n oficina-mecanica
kubectl get replicaset -n oficina-mecanica
kubectl get pods -n oficina-mecanica -l app.kubernetes.io/name=oficina-mecanica-api
```

Verifique o HPA:

```bash
kubectl get hpa oficina-mecanica-api -n oficina-mecanica
```

O `ReplicaSet` não é criado manualmente no projeto: ele é criado e controlado automaticamente pelo `Deployment`. Essa é a prática recomendada porque o `Deployment` gerencia rollout, rollback e substituição gradual dos pods.

## Acessar a API no Minikube

```bash
minikube service oficina-mecanica-api -n oficina-mecanica --url
```

Depois, acesse:

- `<URL_DO_NODEPORT>/docs`
- `<URL_DO_NODEPORT>/health`
- `<URL_DO_NODEPORT>/db-status`

## Infraestrutura AWS

A Fase 3 do Tech Challenge exige repositórios Terraform separados por responsabilidade. Neste projeto:

- [`oficina-mecanica-infra-kubernetes`](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes) provisiona a **VPC**, o **cluster EKS**, o **node group** gerenciado, o **repositório ECR** da imagem da API, o **IRSA** do AWS Load Balancer Controller e do External Secrets Operator, a instalação via Helm desses dois add-ons e do **metrics-server**, e a role OIDC para o GitHub Actions publicar imagens no ECR.
- [`oficina-mecanica-infra-banco-dados`](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados) provisiona o **RDS PostgreSQL** (Terraform próprio, com sua própria VPC).
- Este repositório (`oficina-mecanica-fiap`), em `infra/aws`, provisiona só o que é específico da aplicação: o secret da API no **AWS Secrets Manager** e a **IRSA role** do ServiceAccount `oficina-mecanica-api` usada pelo External Secrets Operator para lê-lo.

Este repositório consome os outputs dos outros dois via variables/secrets do GitHub: `CLUSTER_NAME`, `ECR_REPOSITORY_URL` e `EKS_OIDC_PROVIDER_ARN` (de `oficina-mecanica-infra-kubernetes`) e `RDS_ENDPOINT`, `RDS_SECRET_ARN` e `POSTGRES_PASSWORD` (de `oficina-mecanica-infra-banco-dados`) — ver tabela em [testes-carga-ci.md](testes-carga-ci.md).

O backend remoto do Terraform fica em `infra/backend` e cria S3 para state e DynamoDB para lock — os repositórios `oficina-mecanica-infra-kubernetes` e `oficina-mecanica-infra-banco-dados` reaproveitam o mesmo bucket/tabela, só com uma `key` de state diferente cada um.

## Fluxo Terraform sugerido

1. Criar o backend remoto em `infra/backend` (uma única vez, compartilhado pelos três repositórios Terraform).
2. Provisionar o cluster no repositório `oficina-mecanica-infra-kubernetes` e anotar os outputs `cluster_name`, `ecr_repository_url` e `oidc_provider_arn`.
3. Provisionar o banco no repositório `oficina-mecanica-infra-banco-dados` e anotar os outputs `rds_endpoint`, `rds_secret_arn` e `rds_password`.
4. Copiar `infra/aws/backend.hcl.example` para `infra/aws/backend.hcl` e ajustar bucket, região e tabela (neste repositório).
5. Copiar `infra/aws/terraform.tfvars.example` para `infra/aws/terraform.tfvars` e preencher `cluster_name`, `eks_oidc_provider_arn` e `postgres_password` com os outputs anotados nos passos 2 e 3.
6. Executar `terraform init -backend-config=backend.hcl`, `terraform plan` e `terraform apply` em `infra/aws`.
7. Configurar o kubeconfig usando o comando retornado pelo Terraform do repositório `oficina-mecanica-infra-kubernetes` (`terraform output -raw configure_kubectl_command`).
8. Autenticar no ECR e publicar a imagem, usando `terraform output -raw ecr_login_command` e `terraform output -raw ecr_repository_url` do mesmo repositório.
9. Atualizar o overlay AWS com outputs de ECR, RDS, Secrets Manager e IRSA.
10. Remover o Job antigo de migrations e aplicar o overlay AWS.

Exemplo:

```bash
cd infra/backend
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply

# Em um checkout separado do repositório oficina-mecanica-infra-kubernetes:
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform plan
terraform apply

# De volta neste repositório:
cd infra/aws
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars   # preencha cluster_name, eks_oidc_provider_arn, postgres_password
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

Configure o acesso ao cluster:

```bash
aws eks update-kubeconfig --region us-east-1 --name oficina-mecanica-dev
```

Publique a imagem no ECR (URL obtida no repositório `oficina-mecanica-infra-kubernetes`):

```bash
docker build -t oficina-mecanica-fiap:latest .
docker tag oficina-mecanica-fiap:latest <ECR_REPOSITORY_URL>:latest
docker push <ECR_REPOSITORY_URL>:latest
```

Aplique o overlay AWS:

```bash
kubectl delete job oficina-mecanica-migrations -n oficina-mecanica --ignore-not-found
kubectl apply -k k8s/overlays/aws
```

Obtenha o endpoint externo:

```bash
kubectl get ingress oficina-mecanica-api -n oficina-mecanica
```

Quando `ADDRESS` estiver preenchido, acesse:

- `http://<ADDRESS>/docs`
- `http://<ADDRESS>/health`
- `http://<ADDRESS>/db-status`

## Remover recursos Kubernetes

```bash
kubectl delete -k k8s/overlays/local
```

ou:

```bash
kubectl delete -k k8s/overlays/aws
```

## Segurança

Os valores em `k8s/base/secret.yaml` são defaults do ambiente local. Em ambientes reais, substitua esses valores por segredos gerenciados pelo cluster, External Secrets ou AWS Secrets Manager antes de aplicar os manifests.

No overlay local, o PostgreSQL roda no cluster via `StatefulSet`. No overlay AWS, o PostgreSQL interno é removido e a API aponta para o Amazon RDS criado pelo Terraform do repositório `oficina-mecanica-infra-banco-dados`.
