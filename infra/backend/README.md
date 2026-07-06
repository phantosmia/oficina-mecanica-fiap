# Terraform Backend

Este diretório cria os recursos usados pelo backend remoto do Terraform:

- bucket S3 versionado e criptografado para armazenar o state
- tabela DynamoDB para lock concorrente do state

## Uso

1. Copie o exemplo de variáveis:

`cp terraform.tfvars.example terraform.tfvars`

2. Ajuste `state_bucket_name` para um nome globalmente único.

3. Crie o backend remoto:

`terraform init`

`terraform plan`

`terraform apply`

4. Copie o output `backend_config` para `infra/aws/backend.hcl`.

5. Inicialize a stack principal com backend remoto:

`cd ../aws`

`cp backend.hcl.example backend.hcl`

`terraform init -backend-config=backend.hcl`

Se já existir state local, o Terraform perguntará se deseja migrar o state para o S3.
