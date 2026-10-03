# RFC-0008: Orçamento e Pagamento como microsserviços separados

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-10-03 |

## Contexto

A [RFC-0006](0006-decomposicao-em-microsservicos.md) dividiu o sistema em 5 microsserviços, com **Orçamento & Pagamento** num serviço só, como o PDF da Fase 4 sugere ("Orçamento e Pagamento (Billing Service)"). Ao chegar a hora de implementá-lo, com a integração com o Mercado Pago já definida (Checkout Pro via API de Orders), a junção foi reavaliada.

Os dois lados têm naturezas diferentes:

- **Orçamento** é regra da oficina: monta o orçamento a partir do diagnóstico, envia ao cliente um link com token, registra a aprovação ou a recusa. Muda quando muda a forma de a oficina orçar e se relacionar com o cliente.
- **Pagamento** é integração com um provedor externo: cria a cobrança no Mercado Pago, recebe o webhook, consulta o resultado, cancela ou estorna. Muda quando muda o provedor ou a API dele.

## Alternativas consideradas

1. **(Descartada) Manter um serviço, com os dois contextos separados por dentro** (módulos `quote/` e `payment/`, com o Mercado Pago atrás de uma interface). Dava a separação de responsabilidades no código sem um serviço a mais para operar, e o contrato da saga já tratava orçamento e pagamento como passos distintos, o que tornaria uma extração futura simples. Descartada porque deixa juntos o que tem motivos diferentes para mudar e para falhar: uma indisponibilidade do Mercado Pago, um pico de webhooks ou uma troca de provedor afetariam também a aprovação de orçamentos.
2. **(Escolhida) Dois microsserviços**, cada um com repositório, pipeline, infraestrutura e banco próprios.

## Decisão

**Orçamento** e **Pagamento** passam a ser microsserviços separados. O sistema fica com **6 microsserviços**.

| Serviço | Repositório | Responsabilidade | Banco |
|---|---|---|---|
| **Orçamento** | `oficina-mecanica-orcamento` (o antigo `oficina-mecanica-orcamento-pagamento`, renomeado ainda vazio) | Gera o orçamento a partir do `DiagnosticoConcluido`, envia ao cliente o link de aprovação com token, registra aprovação/recusa (pelo link ou pelo admin), cancela | DynamoDB ([ADR-0011](../adrs/0011-persistencia-orcamento-e-pagamento.md)) |
| **Pagamento** | `oficina-mecanica-pagamento` | Cria a cobrança no Mercado Pago (Checkout Pro via API de Orders) e envia o link de pagamento, recebe o webhook e confirma o resultado consultando o Mercado Pago, cancela cobrança não paga, estorna pagamento feito | PostgreSQL ([ADR-0011](../adrs/0011-persistencia-orcamento-e-pagamento.md)) |

### Bancos

A escolha do banco de cada um está na [ADR-0011](../adrs/0011-persistencia-orcamento-e-pagamento.md): **Orçamento em DynamoDB** e **Pagamento em PostgreSQL**.

### Mudanças no contrato da saga

O orquestrador já tratava orçamento e pagamento como passos distintos. Com a separação, [`docs/saga.md`](../saga.md) muda assim:

- **Filas e tópicos**: `orcamento-comandos`/`orcamento-eventos` e `pagamento-comandos`/`pagamento-eventos` no lugar de `orcamento-pagamento-*`.
- **`CriarCobranca` vai para o Pagamento.** Como o Pagamento não lê o banco do Orçamento, o comando carrega tudo o que ele precisa: valor total, descrição dos itens e e-mail do cliente. O orquestrador já tem esses dados, vindos do `OrcamentoGerado`.
- **Nova compensação `CancelarCobranca`** (Pagamento), para uma cobrança criada e ainda não paga. Antes, cancelar o orçamento também invalidava o link de pagamento, porque os dois estavam no mesmo serviço. Agora, cancelar o orçamento e cancelar a cobrança são passos separados.
- **`CancelarOrcamento` passa a fazer parte das compensações depois da aprovação**, para o orçamento não ficar como "aprovado" numa OS cancelada.

## Consequências

- **Positivas**: uma indisponibilidade do Mercado Pago não afeta a geração nem a aprovação de orçamentos (a saga só espera ou compensa no passo da cobrança). O webhook público e as credenciais do Mercado Pago ficam isolados num serviço pequeno. Trocar de provedor de pagamento não toca no Orçamento.
- **Negativas**: um sexto serviço, com repositório, pipeline, deploy e infraestrutura (fila, tópico, RDS) para recriar a cada rotação do AWS Academy Lab. A saga ganha uma compensação a mais (`CancelarCobranca`), e o comando `CriarCobranca` passa a carregar uma cópia dos dados do orçamento.
- A [RFC-0006](0006-decomposicao-em-microsservicos.md) e a [RFC-0007](0007-mensageria-sqs-sns.md) ganham notas de revisão apontando para esta RFC. A [ADR-0009](../adrs/0009-persistencia-poliglota-por-servico.md) fica parcialmente substituída pela [ADR-0011](../adrs/0011-persistencia-orcamento-e-pagamento.md).
