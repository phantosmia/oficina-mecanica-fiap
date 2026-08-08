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

A infraestrutura Terraform fica em `infra/aws` e provisiona:

- VPC dedicada
- cluster EKS
- node group gerenciado
- repositório ECR para a imagem da API
- IAM/IRSA para o AWS Load Balancer Controller
- AWS Secrets Manager + External Secrets Operator para informações sensíveis da API
- metrics-server para o HPA coletar CPU/memória no EKS
- role OIDC para o GitHub Actions publicar imagens no ECR

O banco PostgreSQL em Amazon RDS **não** é provisionado aqui: é responsabilidade do repositório separado [`oficina-mecanica-infra-banco-dados`](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados) (Terraform próprio, com sua própria VPC), conforme a separação de repositórios exigida pela Fase 3 do Tech Challenge. Este repositório consome o endpoint e as credenciais do RDS via as variables/secrets `RDS_ENDPOINT`, `RDS_SECRET_ARN` e `POSTGRES_PASSWORD` (ver tabela em [testes-carga-ci.md](testes-carga-ci.md)).

O backend remoto do Terraform fica em `infra/backend` e cria S3 para state e DynamoDB para lock — o repositório `oficina-mecanica-infra-banco-dados` reaproveita o mesmo bucket/tabela, só com uma `key` de state diferente.

## Fluxo Terraform sugerido

1. Criar o backend remoto em `infra/backend`.
2. Copiar `infra/aws/backend.hcl.example` para `infra/aws/backend.hcl` e ajustar bucket, região e tabela.
3. Copiar `infra/aws/terraform.tfvars.example` para `infra/aws/terraform.tfvars`.
4. Ajustar região, nome do cluster e tamanho do node group.
5. Executar `terraform init -backend-config=backend.hcl`, `terraform plan` e `terraform apply` em `infra/aws`.
6. Configurar o kubeconfig usando o comando retornado pelo Terraform.
7. Autenticar no ECR usando `terraform output ecr_login_command`.
8. Buildar e publicar a imagem no ECR retornado em `terraform output ecr_repository_url`.
9. Atualizar o overlay AWS com outputs de ECR, RDS, Secrets Manager e IRSA.
10. Remover o Job antigo de migrations e aplicar o overlay AWS.

Exemplo:

```bash
cd infra/backend
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply

cd ../aws
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

Configure o acesso ao cluster:

```bash
aws eks update-kubeconfig --region us-east-1 --name oficina-mecanica-dev
```

Publique a imagem no ECR:

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
