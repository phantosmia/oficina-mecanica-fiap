# ADRs (Architecture Decision Records)

ADRs registram **decisões arquiteturais permanentes** — escolhas estruturais que moldam como o sistema é construído e operado (padrão de comunicação, uso de HPA, onde o banco roda). Diferem das [RFCs](../rfcs/README.md) por serem mais objetivos: registram a decisão tomada e suas consequências, sem necessariamente detalhar todo o debate entre alternativas.

Uma ADR não é apagada quando a decisão muda — marque o status como **Substituído** e linke a ADR nova, preservando o histórico do porquê a decisão original fazia sentido no seu contexto.

## Índice

| ADR | Título | Status |
|---|---|---|
| [0001](0001-padrao-de-comunicacao-sincrono.md) | Padrão de comunicação síncrono via REST/HTTP | Substituído por [RFC-0007](../rfcs/0007-mensageria-sqs-sns.md) e [ADR-0008](0008-saga-orquestrada-no-os-service.md) |
| [0002](0002-uso-de-hpa-para-escalabilidade.md) | Uso de HPA para escalabilidade automática | Aceito |
| [0003](0003-postgresql-gerenciado-rds.md) | PostgreSQL gerenciado (RDS) em produção | Aceito |
| [0004](0004-api-gateway-como-ponto-de-entrada.md) | API Gateway como ponto único de entrada e autorização | Aceito |
| [0005](0005-lambda-auth-na-vpc-do-banco.md) | Lambda de autenticação implantada na VPC do banco de dados | Aceito |
| [0006](0006-alb-interno-vpc-link.md) | ALB interno + VPC Link como único ponto de entrada público | Aceito |
| [0007](0007-new-relic-como-plataforma-de-observabilidade.md) | New Relic como plataforma de observabilidade | Aceito |
| [0008](0008-saga-orquestrada-no-os-service.md) | Saga orquestrada, com o orquestrador dentro do OS Service | Aceito; fluxo substituído pela [ADR-0010](0010-diagnostico-define-o-orcamento.md) |
| [0009](0009-persistencia-poliglota-por-servico.md) | Persistência poliglota, com um banco por serviço | Aceito; linha de Orçamento & Pagamento substituída pela [RFC-0008](../rfcs/0008-separacao-orcamento-e-pagamento.md) |
| [0010](0010-diagnostico-define-o-orcamento.md) | O diagnóstico define o orçamento | Aceito |

## Template

```markdown
# ADR-000X: Título da decisão

| | |
|---|---|
| **Status** | Proposto / Aceito / Substituído por ADR-000Y |
| **Data** | AAAA-MM-DD |

## Contexto
Qual força arquitetural motivou a decisão?

## Decisão
O que foi decidido, de forma direta.

## Alternativas consideradas
Opções descartadas e por quê, de forma breve.

## Consequências
Impactos positivos e negativos, o que fica mais fácil e o que fica mais difícil.
```
