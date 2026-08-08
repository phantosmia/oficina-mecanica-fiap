# Testes, Carga e CI/CD

## Testes automatizados

Os testes utilizam **Testcontainers** para provisionar um PostgreSQL efêmero por execução. Basta ter o Docker disponível e rodar:

```bash
poetry run pytest
```

O fluxo automático é:

1. No início da sessão, `tests/conftest.py` sobe um container `postgres:16-alpine` em uma porta aleatória.
2. A `DATABASE_URL` da aplicação é configurada para apontar para esse container.
3. A cada teste, o schema é resetado por migrations (`alembic downgrade base` + `alembic upgrade head`).
4. Ao final da sessão, o container é destruído.

Caso `DATABASE_URL` já esteja definida no ambiente, o Testcontainers não é acionado e os testes usam a conexão fornecida.

A cobertura mínima configurada é de `80%` para os domínios críticos.

## Teste de carga com Locust

O cenário de carga fica em [k8s/load-test/locustfile.py](../k8s/load-test/locustfile.py). Ele autentica com o usuário admin, consulta endpoints protegidos e mistura chamadas leves (`/health`) com chamadas que acessam o banco (`/db-status`, `/clients`, `/vehicles`, `/service-orders`, `/services` e `/parts`).

As execuções locais usam a imagem Docker oficial do Locust, então não é necessário instalar o Locust no ambiente Poetry da API.

### Interface web local

```bash
mise run load-ui
```

Depois, acesse `http://localhost:8089`, informe o número de usuários, a taxa de spawn e confirme o host da API.

### Headless local

```bash
LOCUST_USERS=100 LOCUST_SPAWN_RATE=10 LOCUST_RUN_TIME=5m mise run load-headless
```

### Carga dentro do Kubernetes

Para simular carga dentro do Kubernetes e observar o HPA escalar os pods da API:

```bash
mise run k8s-load-run
```

Acompanhe o HPA:

```bash
mise run k8s-hpa-watch
```

Acompanhe o resumo do Locust:

```bash
mise run k8s-load-logs
```

O Job Kubernetes fica em [k8s/load-test](../k8s/load-test). Por padrão ele roda `250` usuários, spawn rate `25` e duração de `8m`, chamando o Service interno `http://oficina-mecanica-api:8000`.

Para demonstrações em vídeo, o HPA em [k8s/base/hpa.yaml](../k8s/base/hpa.yaml) usa `scaleUp.stabilizationWindowSeconds=0` e políticas de scale-up a cada `15s`. Assim, depois que CPU ou memória passam do alvo, o HPA não aguarda a janela artificial de 1 minuto antes de criar novas réplicas. Ainda pode existir uma pequena latência natural do ciclo do HPA e do `metrics-server`.

## Pipeline automatizada no GitHub

O repositório possui pipeline de CI em [.github/workflows/ci.yml](../.github/workflows/ci.yml), com execução automática em `push` e `pull_request`.

Etapas do job `tests`:

1. Instalar Python `3.12`, Poetry e dependências do projeto.
2. Executar `poetry run pytest` com cobertura mínima. O Testcontainers provisiona automaticamente um PostgreSQL efêmero no runner.

O job `build` valida o build da imagem Docker com `docker build` e roda após `tests` ser concluído com sucesso.

## Deploy manual AWS/EKS

O workflow [.github/workflows/deploy-aws.yml](../.github/workflows/deploy-aws.yml) executa deploy real no EKS via `workflow_dispatch`. Ele **não** provisiona cluster, node group ou ECR — isso é feito separadamente no repositório [`oficina-mecanica-infra-kubernetes`](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes); este workflow só roda o Terraform de `infra/aws` (secret da API + IRSA do seu service account) e o deploy Kubernetes.

Modos:

- `deployment_mode=aws`: usa OIDC, IRSA e External Secrets Operator, aplicando `k8s/overlays/aws`.
- `deployment_mode=aws-academy`: usa credenciais temporárias do AWS Academy Lab, desabilita a criação da IRSA role deste repositório (`enable_irsa_resources=false`) e aplica `k8s/overlays/aws-academy`, criando a Secret Kubernetes diretamente a partir do Secrets Manager.

Em ambos os modos:

- `terraform_apply=false`: executa `terraform init` e `terraform plan` (de `infra/aws`), lê outputs do Terraform e faz o deploy Kubernetes sem aplicar mudanças de infraestrutura.
- `terraform_apply=true`: roda `terraform plan`, aplica `terraform apply -auto-approve` e depois faz o deploy Kubernetes.

Principais inputs:

| Input | Padrão | Descrição |
|---|---|---|
| `deployment_mode` | `aws-academy` | Modo de deploy: `aws` ou `aws-academy` |
| `infra_environment` | `dev` | Ambiente do state remoto do cluster/banco a consumir via `terraform_remote_state` (`kubernetes/<env>` e `database/<env>`) |
| `terraform_apply` | `false` | Executa `terraform apply` antes do deploy |
| `build_image` | `true` | Builda e publica a imagem no ECR antes de aplicar o deploy |
| `image_tag` | `latest` | Tag da imagem no ECR |
| `public_base_url` | `""` | URL pública da API usada nos e-mails |
| `wait_timeout` | `10m` | Timeout para migrations e rollout |

Principais secrets e variables:

| Tipo | Nome | Descrição |
|---|---|---|
| Secret | `AWS_DEPLOY_ROLE_TO_ASSUME` | Modo `aws`: role OIDC com permissão para Terraform (Secrets Manager/IAM) e EKS |
| Secret | `AWS_ACCESS_KEY_ID` | Modo `aws-academy`: access key temporária |
| Secret | `AWS_SECRET_ACCESS_KEY` | Modo `aws-academy`: secret key temporária |
| Secret | `AWS_SESSION_TOKEN` | Modo `aws-academy`: session token temporário |
| Secret | `TF_BACKEND_CONFIG` | Conteúdo completo do `backend.hcl` |
| Secret | `ADMIN_PASSWORD` | Senha admin gravada no tfvars gerado |
| Secret | `JWT_SECRET_KEY` | Chave JWT gravada no tfvars gerado |
| Secret | `SMTP_PASSWORD` | Senha SMTP gravada no tfvars gerado |
| Variable | `AWS_REGION` | Região AWS do EKS/ECR |
| Variable | `TF_STATE_BUCKET` | Bucket S3 do state |
| Variable | `TF_STATE_KEY` | Chave do state (deste repositório; padrão `aws/dev/terraform.tfstate`) |
| Variable | `TF_STATE_REGION` | Região do backend S3 |
| Variable | `TF_LOCK_TABLE` | Tabela DynamoDB de lock |
| Variable | `PUBLIC_BASE_URL` | URL pública da API |

Não há mais variables `CLUSTER_NAME`, `ECR_REPOSITORY_URL`, `EKS_OIDC_PROVIDER_ARN`, `RDS_ENDPOINT` nem secret `POSTGRES_PASSWORD`: esses valores são lidos automaticamente via `terraform_remote_state` a partir dos outputs de `oficina-mecanica-infra-kubernetes` e `oficina-mecanica-infra-banco-dados`, controlados pelo input `infra_environment` (ver [infra/aws/README.md](../infra/aws/README.md)).

O deploy faz, em ordem:

1. Autenticação AWS via OIDC ou credenciais temporárias.
2. `terraform init` com backend remoto (só o Terraform de `infra/aws`: secret da API + IRSA).
3. `terraform plan` — nesse momento o Terraform já lê `cluster_name`, `ecr_repository_url`, `oidc_provider_arn`, `rds_endpoint` e `rds_password` via `terraform_remote_state` — e, opcionalmente, `terraform apply`.
4. Leitura dos outputs `app_secret_name`, `api_secrets_role_arn`, `cluster_name`, `ecr_repository_url` e `rds_endpoint`.
5. Build e push da imagem no ECR, quando `build_image=true`.
6. `aws eks update-kubeconfig` usando o `cluster_name` lido no passo 3.
7. Substituição dos placeholders do overlay selecionado.
8. Criação da Secret Kubernetes a partir do AWS Secrets Manager no modo `aws-academy`.
9. Remoção do Job antigo de migrations.
10. `kubectl apply -k k8s/overlays/<deployment_mode>`.
11. Espera do Job de migrations e rollout da API.

O cluster, o node group e o repositório ECR são provisionados e mantidos pelo workflow [`.github/workflows/terraform.yml`](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes/blob/main/.github/workflows/terraform.yml) do repositório `oficina-mecanica-infra-kubernetes`, não por este.

**Ordem de apply obrigatória:** como o passo 3 lê o state de `oficina-mecanica-infra-kubernetes` e `oficina-mecanica-infra-banco-dados` via `terraform_remote_state`, rodar este workflow com `infra_environment` apontando para um ambiente em que aqueles dois repositórios nunca foram aplicados falha imediatamente no `terraform plan` (`Unable to find remote state`). O workflow já detecta esse erro e aponta qual repositório aplicar primeiro — ver o [diagrama de dependência em arquitetura.md](arquitetura.md#diagrama-de-dependência-entre-os-repositórios-terraform).

O workflow [.github/workflows/publish-ecr.yml](../.github/workflows/publish-ecr.yml) também suporta o lab e usa o environment `aws`.
