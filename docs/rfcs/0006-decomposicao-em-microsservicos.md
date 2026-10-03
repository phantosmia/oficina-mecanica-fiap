# RFC-0006: Decomposição em microsserviços (Fase 4)

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-10-03 |

## Contexto

A Fase 4 do Tech Challenge parte do cenário em que a oficina atingiu escala nacional, com múltiplas filiais, e exige refatorar o monólito modular das fases anteriores em **no mínimo 3 microsserviços independentes**, cada um com **repositório, infraestrutura e banco de dados próprios**, sem que nenhum serviço acesse o banco de outro. Também é obrigatório usar pelo menos um banco relacional e pelo menos um não relacional.

O monólito já estava organizado por contexto de domínio (`app/clients`, `app/vehicles`, `app/service_catalog`, `app/parts`, `app/service_orders`, ...), com `service_orders` concentrando a orquestração do fluxo e consultando os outros contextos por meio da sua própria interface de repositório (`IServiceOrderRepository`). Essas fronteiras já existentes são o ponto de partida natural para o corte.

Restrições que pesam na decisão:

- **AWS Academy Lab**: a conta é efêmera, então a infraestrutura de todos os serviços precisa ser recriada do zero a cada rotação. Cada serviço a mais significa mais um banco, mais um pipeline e mais um deploy para reprovisionar.
- **Cota de 5 VPCs por região**, que já obrigou a derrubar o ambiente `dev` na Fase 3. Os bancos novos não podem trazer VPCs novas.

## Alternativas consideradas

1. **(Descartada) 3 serviços, exatamente os sugeridos no PDF** (OS, Orçamento & Pagamento, Execução), com catálogo/peças/estoque dentro do OS Service. A baixa de estoque, que é o passo mais sensível do fluxo, ficaria fora da coordenação distribuída, como uma transação local escondida dentro do orquestrador.
2. **(Descartada) 4 serviços, com Catálogo & Estoque num serviço só.** Resolve o problema anterior, mas junta dois dados de natureza oposta num mesmo banco. A ficha da peça e o catálogo de serviços são lidos com frequência, mudam pouco e têm atributos que variam por tipo (pneu tem aro e medida, óleo tem viscosidade). O saldo de estoque é escrito a cada OS e exige transação tudo-ou-nada com reservas concorrentes. Um único banco atenderia mal um dos dois.
3. **(Escolhida) 5 serviços, com Catálogo e Estoque separados.** Cada dado fica no banco que combina com a forma como é usado (ver [ADR-0009](../adrs/0009-persistencia-poliglota-por-servico.md)).
4. **(Descartada) Orquestrador da saga em serviço próprio.** Discutida na [ADR-0008](../adrs/0008-saga-orquestrada-no-os-service.md).

## Decisão

**Cinco microsserviços**, cada um com repositório, pipeline de CI/CD, manifestos Kubernetes, Terraform e banco de dados próprios:

| Serviço | Repositório | Responsabilidade | Banco |
|---|---|---|---|
| **OS Service** | `oficina-mecanica-fiap` (este repositório, refatorado) | Clientes, veículos, abertura de OS, status e histórico, rastreio público, login administrativo e **orquestrador da saga** | PostgreSQL (RDS) |
| **Catálogo** | `oficina-mecanica-catalogo` | Catálogo de serviços (preço, tempo estimado) e fichas de peças (SKU, preço, atributos por tipo) | **DynamoDB** |
| **Estoque** | `oficina-mecanica-estoque` | Saldo por peça, entradas de estoque e **reserva, confirmação e liberação** para as OS | PostgreSQL (RDS) |
| **Orçamento & Pagamento** | `oficina-mecanica-orcamento-pagamento` | Geração do orçamento, envio para aprovação (e-mail + link com token), aprovação/recusa, **cobrança e estorno via Mercado Pago** | PostgreSQL (RDS) |
| **Execução** | `oficina-mecanica-execucao` | Fila de execução das OS, status de diagnóstico e reparo, aviso de finalização | **DynamoDB** |

Os três repositórios de infraestrutura e autenticação da Fase 3 (`oficina-mecanica-infra-banco-dados`, `oficina-mecanica-infra-kubernetes` e `oficina-mecanica-lambda-auth`) continuam existindo como **plataforma compartilhada**. Cada serviço faz o próprio deploy no mesmo cluster EKS, e os bancos relacionais novos são criados pelo Terraform de cada serviço dentro da VPC de banco que já existe (lida via `terraform_remote_state`), sem criar VPC nova. As tabelas DynamoDB não usam VPC.

Critérios usados no corte:

- **Dono do dado = dono da regra.** Quem decide se há estoque é quem guarda o estoque; quem decide se o pagamento foi aprovado é quem conversa com o Mercado Pago. Nenhuma regra de negócio depende de ler o banco de outro serviço.
- **Ciclos de vida distintos.** Cadastro (catálogo), saldo (estoque), dinheiro (orçamento/pagamento), operação de chão de oficina (execução) e o agregado central (OS) mudam por motivos e em ritmos diferentes.
- **Snapshot em vez de referência viva.** A regra das fases anteriores, de gravar `unit_price`/`subtotal` na criação da OS para auditoria, já tornava a OS independente de mudanças futuras de preço. Na Fase 4 ela vira o contrato entre os serviços: o OS Service copia os preços do Catálogo na abertura, e o orçamento é gerado a partir dessa cópia.

### Como os serviços se integram

- **Catálogo fora da saga, via REST síncrono.** Na abertura da OS, o OS Service consulta o Catálogo para validar os serviços e peças pedidos e copiar os preços. É uma leitura sem efeito colateral, então não há o que compensar, e o cliente da API precisa da resposta na hora: item inexistente continua resultando em 404 imediato, como nas fases anteriores. É o caso de "REST síncrono quando necessário" previsto no PDF.
- **Estoque, Orçamento & Pagamento e Execução como participantes da saga, via mensageria.** Esses passos têm efeito colateral (reservar saldo, cobrar, enfileirar) e precisam de compensação em caso de falha. Ver [ADR-0008](../adrs/0008-saga-orquestrada-no-os-service.md) e [RFC-0007](0007-mensageria-sqs-sns.md).
- **Catálogo → Estoque por evento.** Quando uma peça é cadastrada no Catálogo, ele publica `PecaCadastrada`; o Estoque reage criando o saldo zerado daquela peça. O Estoque nunca consulta o banco do Catálogo.

## Consequências

- **Positivas**: cada serviço é deployado, testado e escalado de forma independente. Uma indisponibilidade do Mercado Pago, por exemplo, afeta só Orçamento & Pagamento, e a saga apenas espera ou compensa, sem derrubar a abertura de OS. As fronteiras ficam explícitas nos contratos de mensagens ([`docs/saga.md`](../saga.md)) em vez de implícitas em imports.
- **Negativas**: perde-se a atomicidade do banco único. A aprovação, que antes decrementava o estoque e mudava o status numa transação só, agora exige uma saga com compensações. Consultas que cruzam domínios (por exemplo, "OS com os nomes das peças") passam a depender dos snapshots gravados na própria OS, sem join.
- **Operacionais**: cinco pipelines, cinco deploys, três instâncias RDS e duas tabelas DynamoDB para reprovisionar a cada rotação do AWS Academy Lab. Para limitar o custo, as instâncias RDS usam a menor classe disponível no Lab, e as tabelas DynamoDB usam cobrança sob demanda.
- **Em aberto**: extrair o orquestrador para um serviço próprio, caso o número de sagas cresça (ver ADR-0008).

## Revisão (2026-10-03): quem consulta o Catálogo

Com a [ADR-0010](../adrs/0010-diagnostico-define-o-orcamento.md), os serviços e peças da OS deixam de ser informados na abertura e passam a ser escolhidos pelo mecânico no diagnóstico, dentro da Execução. Com isso, dois pontos desta RFC mudam:

- **Quem consulta o Catálogo por REST síncrono é a Execução**, ao concluir o diagnóstico, e não o OS Service na abertura da OS. Continua sendo uma leitura sem efeito colateral, fora da saga, e continua sendo o caso de "REST síncrono quando necessário": o mecânico precisa da resposta na hora, e item inexistente ou desativado vira erro imediato na tela do diagnóstico.
- **O snapshot de preços é copiado pela Execução**, que o envia no evento `DiagnosticoConcluido`. O orçamento é gerado a partir dessa cópia.

A divisão em 5 serviços e os critérios de corte não mudam.
