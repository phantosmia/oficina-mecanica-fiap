# 2026-10-17 — Terraform e deploy dos 6 microsserviços na AWS

## Contexto / pedido original

Mesma sessão do [SonarCloud](2026-10-17-sonarcloud.md). Com as credenciais do Lab renovadas, a usuária pediu para atacar a etapa 6 do `docs/proximos-passos.md` (infraestrutura), a maior que faltava.

## Diagnóstico inicial

**A conta do Lab mudou**: agora é `340919830422`; a de 2026-09-12 era `752800996420`. A conta nova estava vazia: sem EKS, RDS, ECR, bucket, filas ou tabelas, só a VPC padrão. As roles do Lab (`LabEksClusterRole`, `LabEksNodeRole`) tinham sufixos novos.

## O que foi feito, na ordem

1. **Backend do Terraform** (`infra/backend`, a única peça local): o state antigo foi guardado como `terraform.tfstate.stale-752800996420-20261017.bak`, e o nome do bucket passou a `oficina-mecanica-fiap-tfstate-340919830422-us-east-1`. Plano revisado (6 recursos a criar, nada a destruir); o apply foi rodado pela usuária, porque o modo automático bloqueia `terraform apply` local.
2. **Variables do GitHub** atualizadas para a conta nova: `TF_STATE_BUCKET` nos 9 repositórios, roles do EKS, `LAMBDA_EXECUTION_ROLE_ARN` e nodes em 3 (mínimo 2, máximo 4, porque eram 1 a 2, pouco para 6 serviços). As credenciais foram gravadas pela usuária com o script novo `scripts/atualiza-credenciais-aws.sh`.
3. **`workflow_dispatch`** no banco ([infra-banco-dados#10](https://github.com/phantosmia/oficina-mecanica-infra-banco-dados/pull/10)) e na Lambda ([lambda-auth#12](https://github.com/phantosmia/oficina-mecanica-lambda-auth/pull/12)): as últimas runs tinham mais de 30 dias, e o GitHub não deixa reexecutá-las.
4. **Banco e cluster** pelos workflows. O cluster falhou na primeira vez nos `helm_release` (`Kubernetes cluster unreachable: the server has asked for the client to provide credentials`), mas cluster e nodes já estavam `ACTIVE` e o access entry existia: era corrida com a propagação da permissão. Um `gh run rerun --failed` resolveu.
5. **Terraform e deploy dos 5 serviços novos**, todos com CI verde e mergeados pela usuária: [catalogo#3](https://github.com/phantosmia/oficina-mecanica-catalogo/pull/3), [estoque#3](https://github.com/phantosmia/oficina-mecanica-estoque/pull/3), [orcamento#3](https://github.com/phantosmia/oficina-mecanica-orcamento/pull/3), [pagamento#4](https://github.com/phantosmia/oficina-mecanica-pagamento/pull/4), [execucao#3](https://github.com/phantosmia/oficina-mecanica-execucao/pull/3). No OS Service, [fiap#46](https://github.com/phantosmia/oficina-mecanica-fiap/pull/46) (fila `os-saga-eventos`, deploy com as filas reais, ADR-0012, script de credenciais).
6. **Deploys na ordem**: Catálogo → Estoque, Orçamento, Pagamento e Execução em paralelo → OS Service → Lambda. Todos passaram na primeira tentativa.

## Estado final, verificado

- 26 pods dos 6 serviços `Running` e as 3 migrations `Completed`. Os LoadBalancers públicos são os do OS Service, do Orçamento e do Pagamento.
- O relay do Catálogo registra `Found credentials from IAM Role: LabRole`. O `/ready` do Catálogo lê a tabela DynamoDB (`ACTIVE`), e as listagens autenticadas respondem 200.
- **A saga funciona na AWS**: a OS 1 (CPF `78181367464`), aberta pela API pública, chegou a `AGUARDANDO_DIAGNOSTICO` em menos de 6 s. Isso exige a volta inteira: comando na fila da Execução, evento no tópico dela, SNS entregando na `os-saga-eventos` e o worker do OS Service processando.
- **Não validado ainda**: o fluxo além do diagnóstico. As tabelas e os bancos novos estão vazios, então é preciso semear o Catálogo e o saldo do Estoque antes. Ficou como item no checklist.

## Fluxo completo validado na AWS (mesma sessão)

- **Seed**: `python -m scripts.seed` dentro dos pods, **primeiro o Estoque** (5 saldos) e depois o Catálogo (5 serviços e 5 peças). Na ordem inversa, o `PecaCadastrada` do Catálogo criaria o saldo zerado antes, e o seed do Estoque não altera peça que já tem saldo.
- **OS 1, fluxo feliz**: diagnóstico na Execução (1 revisão de freios + 2 discos), reserva no Estoque e orçamento gerado em ~4 s (R$ 700,00 = 200 + 2 × 250). O link de aprovação já vem com o endereço do LoadBalancer do Orçamento (o ajuste de `PUBLIC_BASE_URL` do deploy funcionou). A usuária aprovou pela página e pagou no checkout do Mercado Pago (sandbox), e a confirmação veio sozinha (`processed / accredited`). A baixa levou o disco de 15 para 13 e a reserva ficou `confirmada`; depois, reparo e entrega. Histórico: `recebida → em_diagnostico → aguardando_aprovacao → aguardando_pagamento → em_execucao → finalizada → entregue`.
- **Compensações**: OS 2, orçamento recusado pela rota pública: reserva de 3 discos liberada (reservado 3 → 0), status `recusada`. OS 3, 999 discos: `ReservaRecusada`, status `cancelada`.
- **Checkout do Mercado Pago: "Uma das partes com as quais você está tentando efetuar o pagamento é de teste"**. Aparece quando quem paga não é o comprador de teste. Na janela anônima, o checkout entra como convidado (que conta como pessoa real) e não pede login. O que funcionou: na janela anônima, entrar primeiro em mercadopago.com.br com o **comprador de teste** e só então abrir o link de pagamento. Registrado no README do Pagamento.

## Decisões tomadas e por quê

- **[ADR-0012](../adrs/0012-labrole-como-role-dos-nodes-no-lab.md): `LabRole` como role dos nodes.** A `LabEksNodeRole` não tem SQS, SNS nem DynamoDB. `iam:PutRolePolicy`, `AttachRolePolicy` e `CreateRole` são negados, então não há IRSA nem como adicionar permissões a ela. `iam:PassRole` sobre a `LabRole` é permitido, e a simulação de IAM confirmou que ela cobre os nodes (CNI, ECR) e os serviços. Chaves de acesso no Secret foram descartadas porque expiram em horas.
- **Terraform gerado por script, mas explícito por serviço**: os 5 `infra/` saíram do mesmo gerador, mas cada repositório tem arquivos legíveis sozinhos (sem `count` nem condicionais para ligar ou desligar partes). O mesmo vale para o `deploy.yml`.
- **Recursos de outro serviço lidos pelo nome** (`data "aws_sns_topic"`, `data "aws_sqs_queue"`) em vez de `terraform_remote_state` do state de outro serviço: o acoplamento fica no contrato de nomes (`oficina-<ambiente>-<serviço>-eventos`/`-comandos`), e o erro de ordem de apply aparece como "tópico não encontrado".
- **ECR por ambiente** nos serviços novos (`oficina-<ambiente>-<serviço>`, com `force_delete`): evita o problema do ECR gerenciado por dois ambientes ao mesmo tempo que o OS Service tem desde a Fase 3. O ECR do OS Service não foi mexido.
- **O overlay `aws-academy` dos 5 serviços passou a remover o `secret.yaml` da base**, como o do OS Service já fazia. Sem isso, o `kubectl apply -k` sobrescreveria o Secret com as senhas reais criado pelo deploy.
- **A senha do RDS é lida no próprio passo que cria o Secret**: o GitHub descarta outputs de step com valor mascarado, então ela não pode passar de um passo para outro.
- **`homologacao` do OS Service**: tinha 3 commits vazios da gravação da Fase 3 que não estavam na `main`. Foi feito merge da `main` (conteúdo final idêntico ao da `main`) em vez de reescrever a branch.
- **Mercado Pago**: `MERCADO_PAGO_ACCESS_TOKEN` e `MERCADO_PAGO_PAYER_EMAIL_OVERRIDE` foram gravados pela usuária a partir do `.env` local do Pagamento. Sem `MERCADO_PAGO_WEBHOOK_SECRET`: no Lab o webhook não chega (falta HTTPS público), e a confirmação vem da reconciliação e do retorno do comprador.

## Pendências para a próxima sessão

- Exigir o job "Validar Terraform" na proteção da `main` dos 5 serviços.
- `JWT_SECRET_KEY` e `ADMIN_PASSWORD` continuam com os valores padrão do código nos 6 serviços. Funciona, porque todos usam o mesmo valor, mas é o débito técnico que já estava listado.
- Observabilidade (New Relic nos 6 com *trace context*), Postman, vídeo e PDF. Os diagramas ficam por último, a pedido da usuária.
