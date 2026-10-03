# ADR-0011: Orçamento em DynamoDB e Pagamento em PostgreSQL

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-10-03 |

## Contexto

A [ADR-0009](0009-persistencia-poliglota-por-servico.md) escolheu PostgreSQL para o serviço **Orçamento & Pagamento**. O motivo era o pagamento: o orçamento e o pagamento mudavam de estado juntos, e a idempotência do webhook do Mercado Pago dependia de uma restrição `UNIQUE` na mesma transação que atualizava o orçamento.

A [RFC-0008](../rfcs/0008-separacao-orcamento-e-pagamento.md) separou os dois em microsserviços próprios, cada um com o seu banco. O motivo da escolha original deixa de valer para o Orçamento: ele não guarda mais dinheiro nem recebe webhook. Era preciso decidir o banco de cada um de novo.

## Decisão

| Serviço | Banco | Por quê |
|---|---|---|
| **Orçamento** | **DynamoDB** | Um orçamento é um **documento** autocontido: os itens com os preços copiados do diagnóstico, os totais, o status, o token do link de aprovação e o prazo. Não há relação com outros dados do serviço. É sempre lido por chave: pelo ID do orçamento, pela OS (o orquestrador e o admin consultam assim) e pelo token do link (o cliente aprova assim), os dois últimos por índice secundário. As mudanças de status (aguardando aprovação → aprovado, recusado, cancelado ou expirado) são feitas com **escrita condicional** ("só aprova se ainda estiver aguardando aprovação"), o que impede, por exemplo, aprovar e recusar o mesmo orçamento ao mesmo tempo. É o mesmo padrão já usado na Execução. |
| **Pagamento** | **PostgreSQL** (RDS) | Dinheiro. O webhook do Mercado Pago pode chegar repetido ou fora de ordem, e o mesmo pagamento passa por criado → pago → estornado. A idempotência depende de uma restrição `UNIQUE` sobre o ID da order no Mercado Pago, na mesma transação que muda o status do pagamento e grava a resposta na outbox. O payload bruto de cada webhook vai para uma coluna `JSONB`, para auditoria. Os argumentos da ADR-0009 para o serviço combinado continuam valendo aqui, agora sem o orçamento junto. |

Com isso, o sistema fica com **três bancos PostgreSQL** (OS Service, Estoque e Pagamento) e **três tabelas DynamoDB** (Catálogo, Execução e Orçamento). O motivo de usar DynamoDB em vez de MongoDB ou DocumentDB como banco de documentos é o mesmo da ADR-0009: é *serverless*, não precisa de VPC nem de instância, e é recriado em segundos a cada rotação do AWS Academy Lab.

## Alternativas consideradas

- **(Descartada) Orçamento em PostgreSQL.** Era a continuação natural da ADR-0009 e deixaria Orçamento e Pagamento com a mesma tecnologia. Mas o orçamento não usa nada de relacional (nenhum join, nenhuma transação entre várias linhas), e seria uma **quarta instância RDS** para recriar a cada rotação do Lab, com custo e tempo de provisionamento, além do risco de esbarrar no limite de instâncias da conta.
- **(Descartada) Pagamento em DynamoDB.** Daria para garantir a idempotência com escrita condicional, mas o pagamento precisa registrar de forma consistente várias coisas ligadas entre si: a cobrança, cada notificação recebida, o estorno e a mensagem de resposta. Em PostgreSQL isso é uma transação comum; em DynamoDB, uma `TransactWriteItems` com limites de tamanho e sem consultas ad hoc para auditoria e conciliação com o Mercado Pago. É o dado em que um erro custa dinheiro, então vale ficar com o banco mais conservador.

## Consequências

- **Substitui parcialmente a ADR-0009**: a linha "Orçamento & Pagamento" de lá deixa de valer. As outras linhas não mudam.
- O Orçamento segue o mesmo modelo já usado no Catálogo e na Execução: *single-table design*, índice secundário para as consultas por OS e por token, outbox e idempotência na mesma `TransactWriteItems`, testes com moto. Não há Alembic nesse serviço.
- O Pagamento segue o modelo do Estoque: SQLAlchemy, Alembic, Unit of Work com outbox e idempotência na mesma transação, testes contra PostgreSQL real (Testcontainers).
- O token do link de aprovação precisa ser único. No DynamoDB não há `UNIQUE`: o token é gerado com `secrets.token_urlsafe` (256 bits, colisão desprezível), e a consulta pelo índice confere que encontrou exatamente um orçamento.
