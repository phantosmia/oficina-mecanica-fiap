# 2026-09-12 — Reprovisiona `homologacao` do zero pra gravar o vídeo

## Contexto / pedido original

"Bora subir o ambiente todo de novo pra gravar o vídeo" — o roteiro da Fase 3 (`docs/roteiro-video-fase3.md`, sessão anterior) já estava escrito, mas o ambiente da AWS Academy Lab precisava ser confirmado/reprovisionado antes de gravar.

## Diagnóstico inicial

Credenciais válidas e conta igual à da sessão de 29/08 (`752800996420`), mas **zero recurso do projeto existia**: nenhum EKS, RDS, VPC própria, bucket S3, tabela DynamoDB, ECR ou API Gateway. O Lab resetou os recursos entre sessões sem trocar o número da conta — cenário não coberto ainda em `docs/proximos-passos.md`, agora documentado lá.

Decisão tomada com a usuária: provisionar **só `homologacao`** (não `producao`/`dev`), confirmando antes que o New Relic (APM + `nri-bundle`) está configurado para esse ambiente — estava.

## O que foi feito, na ordem

1. **Bootstrap do `infra/backend`** (única peça não automatizada via CI): bucket S3 + tabela DynamoDB não existiam mais. `terraform apply` local encontrou um bloqueio novo do Lab — SCP nega `s3:GetBucketObjectLockConfiguration`, o que quebra o refresh do `aws_s3_bucket` logo após criá-lo (o bucket é criado, mas o provider marca o recurso como `tainted` ao falhar a leitura de volta). Contorno: `terraform untaint aws_s3_bucket.terraform_state` + `terraform apply -refresh=false` pra criar os 4 sub-recursos (versioning, SSE, ownership controls, public access block) sem disparar de novo a leitura bloqueada. Documentado em `docs/proximos-passos.md` como gotcha permanente.
2. **Credenciais e roles**: `EKS_CLUSTER_ROLE_ARN`/`EKS_NODE_ROLE_ARN` tinham sufixo antigo (o Lab gera um novo a cada sessão, mesmo sem trocar a conta) — atualizados via `gh variable set`. `AWS_ACCESS_KEY_ID`/`SECRET`/`SESSION_TOKEN` atualizados nos 4 repositórios (Environments `homologacao`/`producao` no `oficina-mecanica-fiap`, secrets de repositório nos outros três).
3. **Deploy em ordem** (banco → cluster → aplicação → lambda), cada um via push real em `homologacao` (não `workflow_dispatch`), acompanhado via `gh run watch`:
   - `oficina-mecanica-infra-banco-dados`: RDS provisionado (~10min).
   - `oficina-mecanica-infra-kubernetes`: EKS provisionado (~15min).
   - `oficina-mecanica-fiap`: **falhou na primeira tentativa** — migration job travava em `ConnectionTimeout` contra o RDS.
   - `oficina-mecanica-lambda-auth`: também falhou na primeira tentativa — `iam:CreateRole` negado.

## Dois bugs de CI encontrados e corrigidos (PRs mergeadas)

Achado do dia, o mesmo padrão nos dois: **a variable Terraform tem um default vazio que só funciona com um valor real, e o workflow de CI nunca passava esse valor** — funcionava só quando alguém aplicava localmente com um `terraform.tfvars` próprio (não usado pela CI).

- **[`oficina-mecanica-infra-banco-dados` #9](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados/pull/9)** — `allowed_cidr_blocks` (`variables.tf`) é `[]` por padrão; sem os CIDRs certos (VPC do banco + VPC do EKS), o security group do RDS fica sem regra de entrada nenhuma, e qualquer conexão (migration job, Lambda Authenticate) falha por timeout, não por credencial. Corrigido: `TF_VAR_allowed_cidr_blocks` no workflow, lido da variable de repositório `ALLOWED_CIDR_BLOCKS`.
- **[`oficina-mecanica-lambda-auth` #11](https://github.com/phantosmia/oficina-mecanica-lambda-auth/pull/11)** — `lambda_execution_role_arn` é vazio por padrão, o que faz o Terraform tentar `aws_iam_role.lambda` (criar role própria) — bloqueado no Academy Lab (`iam:CreateRole`), mesmo bloqueio já conhecido pro EKS. Corrigido: `TF_VAR_lambda_execution_role_arn` no workflow, lido de `LAMBDA_EXECUTION_ROLE_ARN` (aponta pra `LabRole`).

Depois de corrigir o banco de dados, recriei manualmente a migration job travada (`kubectl delete job`) e usei `gh run rerun` no deploy da aplicação em vez de disparar um push novo.

## Um terceiro problema, sem PR — corrigido só no state local

Depois do fix de IAM role, o `terraform plan` do `lambda-auth` ainda falhou: `error creating archive: could not archive missing directory: ./build`. Causa: a tentativa anterior (antes do fix) já tinha deixado `null_resource.build` gravado no state remoto como "aplicado" — mas o `./build` (artefato do `pip install`, gerado via `local-exec`) só existe no filesystem efêmero do runner que rodou aquele apply, não no runner novo. Corrigido rodando `terraform state rm null_resource.build` localmente (contra o state remoto, via `backend.hcl` apontando pra `lambda/homologacao/terraform.tfstate`) — não mexe em infra real, só remove um registro de state que não refletia mais a realidade. Depois disso, `gh run rerun` recriou o build do zero no runner novo e passou.

## Um "falso" erro de rollout, explicado mas não corrigido (não era bug)

Depois dos fixes, o deploy da aplicação falhou de novo, agora em "Aguardar rollout da API": `error: deployment "oficina-mecanica-api" exceeded its progress deadline`. Não era um problema novo — era resíduo da falha anterior: os pods ficaram >10min em `Init:0/1` esperando a migration job (antes do fix do CIDR), e o Kubernetes já tinha marcado a condição `ProgressDeadlineExceeded` no `Deployment`. Como o `gh run rerun` reaplicou o mesmo manifesto (sem mudança de spec), esse relógio interno do Kubernetes não foi resetado — e `kubectl rollout status` falha instantaneamente ao ver essa condição, sem esperar o timeout. Confirmado manualmente segundos depois: rollout completo, 5/5 pods `Running`, `/health` 200. Não precisou de nenhuma correção — só esperar o próximo reconcile do controller.

## Estado final, verificado

- RDS `available`, EKS `ACTIVE`, API respondendo (`curl /health` → 200).
- `POST /auth/cpf` testado: CPF mal formado → 400; CPF válido sem cliente cadastrado → 404 (mesma resposta de propósito, por segurança).
- HPA escalou de 2→5 réplicas sozinho durante o boot (pico de CPU do startup, não de carga real) e depois voltaria a 2 — comportamento esperado, não um problema.
- **Banco já vem semeado automaticamente** no boot do container (catálogo de serviços/peças + 3 clientes de exemplo, incluindo CPF `78181367464` — João Silva) — confirmado via API, não precisou rodar nada manual.
- **Dashboards e alertas do New Relic já existiam** (sessão anterior) — a conta New Relic não reseta junto com a AWS Academy, só o *state* local do Terraform desses dois stacks ficou órfão (apontava pro bucket S3 antigo). Confirmado via NerdGraph (API do New Relic), sem precisar reaplicar: as 3 páginas do dashboard, a policy de alertas, e o app `oficina-mecanica-api` com `reporting: true`. **Cuidado pra próxima sessão**: rodar `terraform apply` em `infra/newrelic-dashboards`/`infra/newrelic-alerts` sem antes importar o state existente vai tentar criar um dashboard/policy **duplicado** — o Terraform local não sabe que o recurso real já existe.
- **Dados de negócio de hoje semeados** pro dashboard "Ordens de Serviço": criada e conduzida uma OS completa via API (`recebida → em_diagnostico → aguardando_aprovacao → em_execucao → finalizada → entregue`), gerando 6 eventos (`ServiceOrderCreated` + 5 `ServiceOrderStatusChanged`) confirmados via NRQL.
- **CI/CD deixado verde de propósito**: o run `Deploy AWS/EKS` que tinha falhado (por causa do `ProgressDeadlineExceeded` explicado acima) foi re-executado (`gh run rerun --failed`) depois que os pods já estavam saudáveis — agora aparece `success` na lista de runs, sem nenhum X recente pra quem for gravar o Bloco 2 do roteiro olhando a aba Actions.

## Decisões tomadas e por quê

- **Só `homologacao`, não `producao`**: economiza tempo e evita a cota de 5 VPCs/região que já bloqueou nesta conta antes; é o único ambiente que o roteiro do vídeo usa.
- **Corrigir os bugs de CI via PR normal (não workaround pontual)**: os dois problemas (`allowed_cidr_blocks`, `lambda_execution_role_arn`) são estruturais — teriam voltado a quebrar em qualquer reprovisionamento futuro, não só neste. Corrigir na CI beneficia qualquer pessoa que rodar esses workflows depois.
- **`terraform state rm` local pro `null_resource.build`**: mesma categoria de exceção já aceita pro `infra/backend` (mexer em state, não em infra real, quando a alternativa via CI não é praticável no momento).

## Pendências para a próxima sessão

- **Gravar o vídeo** — ambiente está no ar agora, mas credenciais/recursos do Lab não duram: gravar o quanto antes, ou reconferir tudo nesta lista de novo se passar muito tempo.
- Ainda falta semear catálogo de serviços/peças e cadastrar um cliente de teste antes de gravar o Bloco 4 do roteiro (autenticação por CPF só funciona com cliente existente e ativo).
- `docs/proximos-passos.md` atualizado com os gotchas novos (SCP do S3 Object Lock, rotação de nomes de IAM role do Lab) — ler antes de reprovisionar de novo no futuro.
