# ADR-0005: Lambda de autenticação implantada na VPC do banco de dados

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-08-15 |

## Contexto

O [RFC-0004](../rfcs/0004-escolha-do-api-gateway.md) e a [ADR-0004](0004-api-gateway-como-ponto-de-entrada.md) decidiram que uma AWS Lambda (repositório [`oficina-mecanica-lambda-auth`](https://github.com/phantosmia/oficina-mecanica-lambda-auth)) valida o CPF, consulta a existência do cliente no RDS e emite o JWT. Falta decidir **como essa Lambda alcança o RDS**: o banco (`oficina-mecanica-infra-banco-dados`) não é publicamente acessível (`publicly_accessible = false`) e sua VPC não tem Internet Gateway nem NAT Gateway — o security group do RDS libera a porta 5432 apenas para blocos CIDR específicos (`allowed_cidr_blocks`), não publicamente.

Uma Lambda sem `vpc_config` roda numa rede gerenciada pela AWS com saída livre para a internet (bom para chamar Secrets Manager), mas sem nenhum caminho de rede privado até o RDS. Uma Lambda com `vpc_config` ganha um caminho privado até o RDS, mas perde a saída padrão para a internet — e, sem NAT/IGW na VPC de destino, também perde acesso a qualquer API pública da AWS (Secrets Manager incluso), a menos que algo mais seja provisionado.

## Decisão

1. A função `authenticate` (a única que consulta o RDS) é implantada com `vpc_config` apontando para as mesmas subnets privadas do banco (`private_subnet_ids`, lido via `terraform_remote_state` de `oficina-mecanica-infra-banco-dados`), com um security group próprio (`aws_security_group.lambda_authenticate`) liberando apenas saída.
2. Em vez de a Lambda buscar segredos do Secrets Manager em tempo de execução (o que exigiria alcançar uma API pública da AWS de dentro de uma VPC sem NAT — ver "Alternativas consideradas"), o **Terraform deste repositório** lê os valores em tempo de `apply` (`data.aws_secretsmanager_secret_version` sobre o `rds_secret_arn` de `oficina-mecanica-infra-banco-dados` e o `app_secret_arn` de `oficina-mecanica-fiap`/`infra/aws`) e injeta host/porta/banco/usuário/senha do RDS e o `JWT_SECRET_KEY` como variável de ambiente da função. O mesmo padrão já usado em `infra/aws/main.tf` do repositório principal, que grava `POSTGRES_PASSWORD` (lido do state remoto do banco) diretamente no secret da API.
3. A função `authorizer` (Lambda Authorizer do API Gateway) não consulta o RDS — só valida o JWT com o segredo já recebido via variável de ambiente — e por isso **não** roda dentro de VPC, evitando o custo/latência de ENI sem necessidade.

## Alternativas consideradas

- **VPC Interface Endpoint para Secrets Manager dentro da VPC do banco**: resolveria o acesso do Secrets Manager em tempo de execução sem NAT/IGW, mas adiciona um recurso com custo por hora por AZ e complexidade de rede (security group do endpoint, DNS privado) só para evitar o padrão de injeção em tempo de `apply` que o próprio repositório principal já usa e aceita. Descartada por ora.
- **NAT Gateway na VPC do banco**: resolveria a saída para a internet, mas contraria a decisão original daquele repositório de não ter NAT/IGW porque "o RDS não precisa de saída para a internet" — adicionar um NAT só para esta Lambda inverteria essa premissa e tem custo recorrente.
- **Lambda na VPC do cluster Kubernetes (`oficina-mecanica-infra-kubernetes`), com VPC Peering até a VPC do banco**: essa VPC já tem saída para a internet (resolveria o Secrets Manager em tempo de execução), mas exigiria criar e manter um VPC Peering novo entre dois repositórios que hoje não têm essa relação, mais uma terceira leitura de `terraform_remote_state` (rede do cluster) só para este propósito. Mais infraestrutura para o mesmo resultado que a injeção em tempo de `apply` já entrega.
- **Lambda sem VPC, banco publicamente acessível**: descartada de imediato — reverteria a decisão de segurança de rede já tomada por `oficina-mecanica-infra-banco-dados` (`publicly_accessible = false`).

## Consequências

- Os valores sensíveis (senha do RDS, `JWT_SECRET_KEY`) passam a existir no state do Terraform deste repositório em texto puro (mitigado: o provider AWS marca o atributo `secret_string` de `data.aws_secretsmanager_secret_version` como sensível, então não aparecem em texto puro na saída de `plan`/`apply`; a proteção do state em si continua sendo o controle de acesso ao bucket S3, o mesmo trade-off já aceito por `infra/aws/main.tf`).
- Passa a existir um passo manual obrigatório fora deste repositório: `allowed_cidr_blocks` em `oficina-mecanica-infra-banco-dados` precisa incluir o CIDR da própria VPC do banco (`vpc_cidr` daquele repositório) para que o security group do RDS aceite conexões vindas da função `authenticate` — sem isso, a conexão falha por timeout, não por erro de credencial.
- Se o `JWT_SECRET_KEY` for rotacionado (novo `apply` em `infra/aws`), esta Lambda só passa a usar o novo valor no seu **próprio** próximo `apply` — não há sincronização automática em tempo de execução, ao contrário de uma busca ao Secrets Manager a cada invocação. Aceitável hoje porque não há rotação periódica definida para esse segredo.
- A função `authenticate` paga o custo de cold start de uma Lambda com ENI de VPC; a função `authorizer`, chamada a cada requisição em rota protegida, deliberadamente não paga esse custo por não precisar de rede alguma.
