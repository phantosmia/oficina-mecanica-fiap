# Terraform Backend

Este diretório cria os recursos usados pelo backend remoto do Terraform:

- bucket S3 versionado e criptografado para armazenar o state
- tabela DynamoDB para lock concorrente do state

Esse mesmo bucket/tabela é reaproveitado pelos três repositórios Terraform do projeto — este (`oficina-mecanica-fiap`, em `infra/aws`), [`oficina-mecanica-infra-kubernetes`](https://github.com/phantosmia/oficina-mecanica-infra-kubernetes) e [`oficina-mecanica-infra-banco-dados`](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados) — cada um usando uma `key` de state diferente (`aws/<env>/terraform.tfstate`, `kubernetes/<env>/terraform.tfstate` e `database/<env>/terraform.tfstate`, respectivamente). Nenhum dos outros dois repositórios cria bucket/tabela próprios.

## Uso

1. Copie o exemplo de variáveis:

`cp terraform.tfvars.example terraform.tfvars`

2. Ajuste `state_bucket_name` para um nome globalmente único.

3. Crie o backend remoto:

`terraform init`

`terraform plan`

`terraform apply`

4. Copie o output `backend_config` para `infra/aws/backend.hcl` (e, nos outros dois repositórios Terraform, para seus respectivos `backend.hcl`, ajustando apenas a `key`).

5. Inicialize a stack deste repositório com backend remoto:

`cd ../aws`

`cp backend.hcl.example backend.hcl`

`terraform init -backend-config=backend.hcl`

Se já existir state local, o Terraform perguntará se deseja migrar o state para o S3.
