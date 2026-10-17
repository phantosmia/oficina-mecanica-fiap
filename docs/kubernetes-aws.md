# Kubernetes e AWS

## Kubernetes local

Os manifests Kubernetes estão organizados em base e overlays:

- `k8s/base`: recursos comuns da aplicação
- `k8s/overlays/local`: exposição da API via `NodePort`, útil para Minikube
- `k8s/overlays/aws`: exposição da API via `Ingress` com AWS Load Balancer Controller. O ALB é **interno** (não internet-facing) — o único caminho de entrada público é o AWS API Gateway do repositório `oficina-mecanica-lambda-auth`, via VPC Link (ver [ADR-0006](adrs/0006-alb-interno-vpc-link.md))
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

Este repositório lê os outputs dos outros dois **automaticamente**, via `terraform_remote_state` contra o mesmo bucket S3 do backend remoto (`cluster_name`, `ecr_repository_url` e `oidc_provider_arn` de `oficina-mecanica-infra-kubernetes`; `rds_endpoint` e `rds_password` de `oficina-mecanica-infra-banco-dados`) — não é preciso copiar esses valores em variables/secrets do GitHub. Só a role OIDC do GitHub Actions (`AWS_ROLE_TO_ASSUME`) e o CIDR da VPC para `allowed_cidr_blocks` do banco continuam sendo copiados manualmente, por não serem dado de state — ver [infra/aws/README.md](../infra/aws/README.md).

O backend remoto do Terraform fica em `infra/backend` e cria S3 para state e DynamoDB para lock — os repositórios `oficina-mecanica-infra-kubernetes` e `oficina-mecanica-infra-banco-dados` reaproveitam o mesmo bucket/tabela, só com uma `key` de state diferente cada um.

## Provisionamento completo no AWS Academy Lab

Com os microsserviços, cada um dos outros 5 serviços (`oficina-mecanica-catalogo`, `-estoque`, `-orcamento`, `-pagamento` e `-execucao`) tem um `infra/` próprio e um workflow `deploy.yml` com o mesmo padrão. O Terraform de cada um cria:

- o repositório **ECR** da imagem (`oficina-<ambiente>-<serviço>`);
- a **mensageria** da [RFC-0007](rfcs/0007-mensageria-sqs-sns.md): o tópico SNS de eventos, a fila SQS de comandos e as filas com que o serviço assina tópicos de outros serviços, todas com DLQ;
- o **banco** do serviço: RDS PostgreSQL próprio dentro da VPC de banco que já existe (Estoque e Pagamento) ou tabela DynamoDB (Catálogo, Orçamento e Execução).

O deploy aplica esse Terraform, publica a imagem, cria o Secret Kubernetes com os secrets do GitHub e os outputs do Terraform, e aplica o overlay `aws-academy`. Neste repositório, `infra/aws/messaging.tf` cria a fila `os-saga-eventos`, que assina os tópicos dos 4 participantes.

Os pods acessam SQS, SNS e DynamoDB com a role dos nodes do EKS, que no Lab é a `LabRole`, porque o Lab não permite IRSA ([ADR-0012](adrs/0012-labrole-como-role-dos-nodes-no-lab.md)).

### Ordem de apply

Cada repositório lê o state de quem vem antes, ou recursos que ele cria (tópicos e filas):

1. `oficina-mecanica-infra-banco-dados`: VPC de banco e RDS do OS Service.
2. `oficina-mecanica-infra-kubernetes`: VPC, EKS, peering com a VPC de banco e ECR do OS Service.
3. `oficina-mecanica-catalogo`: o Estoque assina o tópico dele.
4. `oficina-mecanica-estoque`, `-orcamento`, `-pagamento` e `-execucao`, em paralelo.
5. `oficina-mecanica-fiap` (este): assina os tópicos dos 4 participantes e lê as filas de comando deles.
6. `oficina-mecanica-lambda-auth`: lê o state do banco e do cluster.

### Passo a passo depois de um reset do Lab

1. Copiar as credenciais do painel "AWS Details" do Lab para `.aws_credentials` e conferir a conta com `aws sts get-caller-identity`.
2. Se o bucket de state não existir, recriar o backend em `infra/backend` (a única peça aplicada localmente; ver a seção "Coisas que dependem do estado do AWS Academy Lab" de `docs/proximos-passos.md`). O nome do bucket tem o número da conta: se a conta mudou, atualize `TF_STATE_BUCKET` nos 9 repositórios.
3. Atualizar as variables de IAM, que mudam a cada sessão do Lab: `EKS_CLUSTER_ROLE_ARN` (sufixo aleatório, conferir com `aws iam list-roles`), `EKS_NODE_ROLE_ARN` e `LAMBDA_EXECUTION_ROLE_ARN` (ambas apontando para a `LabRole`) e `EKS_ADMIN_PRINCIPAL_ARN` (a role `voclabs`).
4. Copiar as credenciais para os secrets dos 9 repositórios: `bash scripts/atualiza-credenciais-aws.sh`.
5. Disparar os workflows na branch `homologacao`, na ordem acima: com um push da `main` para a `homologacao` ou com `workflow_dispatch` nessa branch.

Problemas já vistos e o que fazer:

- **`Kubernetes cluster unreachable: the server has asked for the client to provide credentials`** no apply do cluster, nos `helm_release`: a permissão de acesso ao cluster recém-criado ainda não tinha propagado. Basta reexecutar o job (`gh run rerun <id> --failed`).
- **O GitHub não reexecuta runs com mais de 30 dias**: use `workflow_dispatch` na branch do ambiente.

## Fluxo Terraform sugerido

Os três repositórios Terraform compartilham o mesmo backend S3 e se conectam via `terraform_remote_state` (ver [infra/aws/README.md](../infra/aws/README.md) e o [diagrama de dependência em arquitetura.md](arquitetura.md#diagrama-de-dependência-entre-os-repositórios-terraform)), então a única coisa que importa é a **ordem de apply**: banco → cluster → aplicação. Nenhum output precisa ser copiado manualmente entre eles.

> **Atenção à ordem:** rodar `terraform plan`/`apply` de um repositório antes do outro já ter sido aplicado no mesmo ambiente (`dev`, `homologacao` ou `producao`) falha imediatamente com `Error: Unable to find remote state`. Isso vale tanto localmente quanto nos workflows de CI/CD — o `deploy-aws.yml` deste repositório e o `terraform.yml` do `oficina-mecanica-infra-kubernetes` já detectam esse erro e imprimem uma dica de qual repositório aplicar primeiro, mas a causa é sempre a mesma: ordem errada de apply, ou `infra_environment`/branch apontando para um ambiente que nenhum dos outros dois repositórios aplicou ainda.

1. Criar o backend remoto em `infra/backend` (uma única vez, compartilhado pelos três repositórios Terraform).
2. Provisionar o banco no repositório `oficina-mecanica-infra-banco-dados`.
3. Provisionar o cluster no repositório `oficina-mecanica-infra-kubernetes` (lê `rds_secret_arn` do passo 2 automaticamente).
4. Copiar `infra/aws/backend.hcl.example` para `infra/aws/backend.hcl` (neste repositório) e `infra/aws/terraform.tfvars.example` para `infra/aws/terraform.tfvars` — os defaults já apontam para o ambiente `dev` dos outros dois repositórios.
5. Executar `terraform init -backend-config=backend.hcl`, `terraform plan` e `terraform apply` em `infra/aws` (lê `cluster_name`, `oidc_provider_arn` e `ecr_repository_url` do passo 3, e `rds_password` do passo 2, automaticamente).
6. Configurar o kubeconfig: `aws eks update-kubeconfig --region <região> --name $(terraform output -raw cluster_name)`.
7. Autenticar no ECR e publicar a imagem, usando `terraform output -raw ecr_repository_url` (deste repositório, repassado do repositório de Kubernetes).
8. Atualizar o overlay AWS com os outputs de ECR, RDS, Secrets Manager e IRSA.
9. Remover o Job antigo de migrations e aplicar o overlay AWS.

Exemplo:

```bash
cd infra/backend
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply

# Em um checkout separado do repositório oficina-mecanica-infra-banco-dados:
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
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
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

Configure o acesso ao cluster e publique a imagem no ECR, usando os outputs deste repositório (já repassados via remote state):

```bash
aws eks update-kubeconfig --region us-east-1 --name $(terraform output -raw cluster_name)

docker build -t oficina-mecanica-fiap:latest .
docker tag oficina-mecanica-fiap:latest $(terraform output -raw ecr_repository_url):latest
docker push $(terraform output -raw ecr_repository_url):latest
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
