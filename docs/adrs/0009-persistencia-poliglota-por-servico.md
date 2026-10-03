# ADR-0009: Persistência poliglota, com um banco por serviço

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-10-03 |

## Contexto

A Fase 4 exige que cada microsserviço tenha banco próprio, que nenhum serviço acesse o banco de outro e que o sistema use pelo menos um banco relacional e pelo menos um não relacional. Até a Fase 3, todo o sistema usava um único PostgreSQL ([RFC-0002](../rfcs/0002-escolha-do-banco-de-dados.md), [ADR-0003](0003-postgresql-gerenciado-rds.md)).

A escolha de banco foi feita serviço a serviço, olhando como cada um usa o dado, em vez de impor o mesmo banco a todos ou de escolher um NoSQL só para cumprir o requisito.

## Decisão

| Serviço | Banco | Por quê |
|---|---|---|
| **OS Service** | PostgreSQL (RDS) | O avanço da saga, a mudança de status da OS, o histórico e a outbox precisam ser gravados na **mesma transação** ([ADR-0008](0008-saga-orquestrada-no-os-service.md)). Clientes, veículos e OS são relacionais (cliente → veículos → OS) e consultados com filtros e ordenação (OS ativas por prioridade de status, tempo médio de execução). |
| **Estoque** | PostgreSQL (RDS) | A reserva baixa N peças de uma vez, tudo ou nada, sem deixar o saldo ficar negativo com reservas concorrentes: uma transação com `UPDATE ... SET reservado = reservado + :qtd WHERE disponivel >= :qtd` por peça. É o caso de uso mais clássico de ACID no sistema. |
| **Orçamento & Pagamento** | PostgreSQL (RDS) | Dinheiro. O orçamento e o pagamento mudam de estado juntos (aprovado → cobrado → pago → estornado), e o webhook do Mercado Pago pode chegar repetido: a idempotência depende de uma restrição `UNIQUE` sobre o id do pagamento no Mercado Pago, dentro da mesma transação que atualiza o orçamento. O payload bruto do webhook, que tem formato variável, fica numa coluna `JSONB` para auditoria. |
| **Catálogo** | **DynamoDB** | Muita leitura (toda abertura de OS consulta preços), pouca escrita e acesso sempre por chave (id do serviço ou da peça). As fichas de peças têm atributos que variam por tipo (pneu tem aro e medida, óleo tem viscosidade), o que encaixa num documento sem migração de schema a cada tipo novo. Não há transação entre itens: o catálogo não participa da saga. |
| **Execução** | **DynamoDB** | Cada OS em execução é um documento acessado pela chave (`order_id`) e atualizado pelos mecânicos ao longo do diagnóstico e do reparo (notas, etapas, horários). A fila de execução é lida por status e data de entrada, o que um índice secundário (GSI) resolve. Não há relação com outros dados do serviço. |

Detalhes que valem para todos:

- **Um banco por serviço, sem compartilhar instância lógica.** Cada PostgreSQL é uma instância RDS própria, criada pelo Terraform do serviço dentro da VPC de banco que já existe. Cada tabela DynamoDB é criada pelo Terraform do serviço que a usa. Nenhum serviço recebe credencial do banco de outro.
- **DynamoDB em vez de MongoDB/DocumentDB.** O DynamoDB é *serverless*: não precisa de VPC, instância nem operação, é criado em segundos pelo Terraform e está disponível no AWS Academy Lab, o que pesa muito num ambiente recriado do zero a cada rotação. O DocumentDB exigiria um cluster dentro de uma VPC, e um MongoDB no EKS seria mais um componente com estado no cluster. Localmente, o DynamoDB é emulado pelo LocalStack, o mesmo usado para SQS/SNS.
- **Cobrança sob demanda** (`PAY_PER_REQUEST`) nas tabelas DynamoDB, sem capacidade provisionada para dimensionar.

## Alternativas consideradas

- **(Descartada) PostgreSQL em todos os serviços**: mais uniforme e com uma única tecnologia para dominar, mas não cumpre o requisito de NoSQL do PDF e ignora que o Catálogo e a Execução são, por natureza, acessados por chave e com documentos de formato variável.
- **(Descartada) Banco colunar (Redshift, ClickHouse) ou wide-column (Cassandra, Amazon Keyspaces) em Orçamento & Pagamento**: bancos colunares analíticos são feitos para agregações sobre muitas linhas e lidam mal com atualizações de uma linha só e com transações, que é justamente o que um pagamento faz. Bancos wide-column não têm transação entre linhas, e a idempotência do webhook dependeria de *lightweight transactions*, caras e limitadas. Se surgir a necessidade de análise de faturamento, ela pode ser atendida por um modelo de leitura separado, alimentado pelos eventos de pagamento, sem ser a fonte da verdade.
- **(Descartada) Banco de documentos também no OS Service, Estoque ou Orçamento & Pagamento**: todos eles têm algum dado semiestruturado (histórico de status da OS, payloads de webhook), mas sempre ao lado de algo que exige transação junto. O `JSONB` do PostgreSQL atende esses casos sem um segundo banco por serviço.

## Consequências

- O sistema passa a ter duas tecnologias de banco para manter, testar e monitorar. Nos testes, o PostgreSQL continua vindo do Testcontainers, e o DynamoDB vem do LocalStack (também via Testcontainers).
- Os serviços com DynamoDB não usam Alembic: o schema é só a chave primária e os índices, definidos no Terraform. A validação do formato dos documentos fica no domínio do serviço.
- Sem transações entre serviços, a consistência entre os bancos é **eventual** e coordenada pela saga. Por exemplo, uma OS pode aparecer como `aguardando_pagamento` alguns instantes antes de o Orçamento & Pagamento registrar a cobrança.
- O custo do AWS Academy Lab sobe com três instâncias RDS em vez de uma. Elas usam a menor classe disponível; as tabelas DynamoDB não têm custo fixo.

> **Nota (2026-10-03):** com a [ADR-0010](0010-diagnostico-define-o-orcamento.md), quem consulta os preços do Catálogo é a Execução, a cada diagnóstico concluído, e não mais a abertura da OS. O perfil de acesso (muita leitura por chave, pouca escrita) e a escolha do DynamoDB não mudam.
