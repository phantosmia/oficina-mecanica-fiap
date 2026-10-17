# ADR-0012: LabRole como role dos nodes do EKS no AWS Academy Lab

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-10-17 |

## Contexto

Com os microsserviços ([RFC-0006](../rfcs/0006-decomposicao-em-microsservicos.md)), os pods passam a chamar APIs da AWS: todos usam SQS e SNS ([RFC-0007](../rfcs/0007-mensageria-sqs-sns.md)), e Catálogo, Execução e Orçamento usam DynamoDB ([ADR-0009](0009-persistencia-poliglota-por-servico.md), [ADR-0011](0011-persistencia-orcamento-e-pagamento.md)). Na Fase 3, a API só falava com o PostgreSQL, que não usa IAM.

Numa conta AWS comum, cada serviço teria a própria role, com só as permissões das filas, tópicos e tabelas dele, ligada ao ServiceAccount do pod por IRSA. É o que o modo `aws` deste repositório faz para o secret da API. No AWS Academy Lab isso não é possível: `iam:CreateRole`, `iam:PutRolePolicy` e `iam:AttachRolePolicy` são negados (conferido com `iam simulate-principal-policy` em 2026-10-17), então não dá para criar roles por serviço nem adicionar permissões à role dos nodes que o Lab fornece (`LabEksNodeRole`). Essa role só tem as políticas padrão de worker node do EKS (CNI, ECR somente leitura e `AmazonEKSWorkerNodePolicy`), sem SQS, SNS nem DynamoDB.

Sem IRSA, um pod usa as credenciais da role da instância EC2 em que roda, pelo serviço de metadados.

## Decisão

No ambiente do Lab, **o node group do EKS usa a `LabRole` em vez da `LabEksNodeRole`**: a variable `EKS_NODE_ROLE_ARN` do `oficina-mecanica-infra-kubernetes` aponta para `arn:aws:iam::<conta>:role/LabRole`.

A `LabRole` é a role ampla que o Lab já oferece para workloads (é a mesma que a Lambda de autenticação usa). Ela confia em `ec2.amazonaws.com` e em `eks.amazonaws.com`, e `iam:PassRole` sobre ela é permitido. A simulação de IAM confirmou que ela cobre o que o node precisa (rede do CNI, como `ec2:AssignPrivateIpAddresses` e `ec2:CreateNetworkInterface`, leitura do ECR e `eks:DescribeCluster`) e o que os serviços usam: `sqs:SendMessage`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sns:Publish`, `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:TransactWriteItems` e `secretsmanager:GetSecretValue`.

Nenhum código muda: os serviços já usam a cadeia de credenciais padrão do boto3, que encontra a role da instância sozinha.

## Alternativas consideradas

- **(Descartada) IRSA ou EKS Pod Identity com uma role por serviço.** É o desenho correto, com privilégio mínimo, mas as duas opções exigem criar roles, o que o Lab bloqueia.
- **(Descartada) Chaves de acesso no Secret Kubernetes.** As credenciais do Lab são temporárias e expiram em poucas horas: os pods parariam de falar com SQS e DynamoDB no meio de uma demonstração, e cada renovação exigiria atualizar o Secret dos 6 serviços. Também poria credenciais de uma conta inteira dentro do cluster.
- **(Descartada) Manter a `LabEksNodeRole`.** Os pods não teriam acesso a SQS, SNS nem DynamoDB.

## Consequências

- **Negativas**: não há isolamento de permissões entre os serviços. Qualquer pod do cluster pode ler ou escrever em qualquer fila, tópico ou tabela da conta, inclusive de outro serviço. O isolamento entre os bancos de dados continua existindo, porque ele vem das credenciais de cada PostgreSQL, que só o serviço dono recebe ([ADR-0009](0009-persistencia-poliglota-por-servico.md)).
- **Positivas**: o deploy funciona no Lab sem nenhuma credencial de longa duração dentro do cluster, e sem passos manuais a cada renovação das credenciais.
- **Fora do Lab**: a decisão vale só para o ambiente do AWS Academy. Numa conta própria, o caminho é uma role por serviço com IRSA, criada pelo Terraform de cada serviço, como o `infra/aws` deste repositório já faz para o secret da API (`enable_irsa_resources`).
