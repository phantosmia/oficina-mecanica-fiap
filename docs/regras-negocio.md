# Regras de Negócio

A partir da Fase 4, o fluxo da OS atravessa seis microsserviços e é coordenado pela saga orquestrada no OS Service. O contrato completo (comandos, eventos, compensações, prazos e payloads) está em [`docs/saga.md`](saga.md); aqui ficam as regras do ponto de vista do negócio.

## Status da ordem de serviço

| Status | Significado | Quem leva a OS para ele |
|---|---|---|
| `recebida` | OS aberta, aguardando o diagnóstico | Admin, na abertura (`POST /service-orders`) |
| `em_diagnostico` | O mecânico está examinando o veículo; depois do diagnóstico, as peças são reservadas e o orçamento é gerado | Saga, quando a Execução publica `DiagnosticoIniciado` |
| `aguardando_aprovacao` | Orçamento enviado ao cliente por e-mail | Saga, quando o Orçamento publica `OrcamentoGerado` |
| `aguardando_pagamento` | Orçamento aprovado; cobrança criada no Mercado Pago e link enviado ao cliente | Saga, quando o Orçamento publica `OrcamentoAprovado` |
| `em_execucao` | Pago, peças baixadas do estoque, OS na fila de reparo | Saga, quando a Execução publica `ReparoEnfileirado` |
| `finalizada` | Reparo concluído; cliente avisado por e-mail | Saga, quando a Execução publica `ExecucaoFinalizada` |
| `entregue` | Veículo entregue ao cliente | Admin (`POST /service-orders/{id}/deliver`), só a partir de `finalizada` |
| `recusada` | Cliente recusou o orçamento (terminal) | Saga, depois de liberar as peças reservadas |
| `cancelada` | Qualquer outra falha: estoque insuficiente, prazo de aprovação ou pagamento vencido, pagamento recusado, participante sem resposta (terminal) | Saga, depois de concluir as compensações |

Cada mudança de status fica registrada no histórico da OS, com o motivo (ex.: "orçamento recusado (cliente)", "prazo de pagamento expirado").

## Fluxo da OS

1. **Abertura** (admin): cliente por CPF/CNPJ, veículo por placa e o problema relatado. Os serviços e peças **não** são informados na abertura ([ADR-0010](adrs/0010-diagnostico-define-o-orcamento.md)).
2. **Diagnóstico** (mecânico, serviço de Execução): examina o veículo e escolhe os serviços e peças necessários. Os itens são validados no Catálogo e os preços copiados de lá.
3. **Reserva de peças** (Estoque): tudo ou nada. Se faltar alguma peça, a OS é cancelada.
4. **Orçamento** (serviço de Orçamento): gerado a partir dos itens do diagnóstico e enviado ao cliente por e-mail, com um link para aprovar ou recusar.
5. **Pagamento** (serviço de Pagamento): depois da aprovação, a cobrança é criada no Mercado Pago e o link de pagamento é enviado ao cliente.
6. **Baixa do estoque** (Estoque): com o pagamento confirmado, a reserva vira baixa definitiva.
7. **Reparo** (mecânico, Execução): a OS entra na fila de reparo; o mecânico inicia e conclui.
8. **Entrega** (admin).

Se algo falhar entre os passos 3 e 7, a saga desfaz o que já foi feito, na ordem inversa (ver "Compensações" abaixo). A partir do passo 7 (OS na fila de reparo) não há mais compensação automática: as peças já estão sendo usadas no veículo.

## Status do cliente

Todo cliente tem um `status`: `ativo` (padrão na criação) ou `inativo`. Um admin altera o status via `PUT /clients/{client_id}`; não há regra de transição (diferente do status da OS) — um cliente inativo pode ser reativado livremente.

A Lambda de autenticação via CPF (repositório [`oficina-mecanica-lambda-auth`](https://github.com/phantosmia/oficina-mecanica-lambda-auth), RFC-0004/ADR-0004) recusa a emissão de JWT para um cliente com `status = inativo`, tratando esse caso como equivalente a "cliente inexistente" (mesma resposta HTTP) — evita confirmar a um solicitante não autenticado se um CPF pertence a um cliente inativo ou simplesmente não existe. Fora desse ponto de entrada, hoje o status **não é** verificado em nenhum outro fluxo (ex.: criação de OS para um cliente inativo continua permitida) — é informativo por enquanto.

## Cálculo do orçamento

O orçamento é calculado a partir dos itens definidos no **diagnóstico**, com os preços copiados do Catálogo naquele momento (snapshot: mudanças de preço posteriores não alteram a OS):

```
subtotal do item = preço unitário × quantidade
mão de obra      = soma dos subtotais dos serviços
peças            = soma dos subtotais das peças
total            = mão de obra + peças
```

Exemplo: 1 "Troca de óleo" a R$ 150,00 e 4 "Óleo 5W30" a R$ 45,00 → mão de obra R$ 150,00, peças R$ 180,00, total R$ 330,00.

Cada serviço recalcula os totais a partir dos itens, em vez de confiar num total recebido pronto: a OS, o Orçamento e o Pagamento (que exige que o valor cobrado no Mercado Pago seja exatamente a soma dos itens).

## Estoque: reserva antes da baixa

A baixa de estoque deixou de ser uma operação única na aprovação (Fases 2 e 3). Agora ela acontece em dois tempos, no serviço de Estoque:

- **Reserva**, logo depois do diagnóstico: as peças ficam prometidas à OS (não podem ser reservadas por outra), mas continuam em estoque.
- **Baixa**, depois do pagamento: a reserva vira saída definitiva.

Se a OS for recusada ou cancelada antes do pagamento, a reserva é liberada; se for cancelada depois da baixa, as peças voltam ao estoque.

## Compensações

| Falha | O que é desfeito (em ordem) | Status final |
|---|---|---|
| Estoque insuficiente na reserva | nada | `cancelada` |
| Cliente recusa o orçamento | libera as peças | `recusada` |
| Prazo de aprovação vencido | cancela o orçamento, libera as peças | `cancelada` |
| Pagamento recusado ou prazo de pagamento vencido | cancela a cobrança, cancela o orçamento, libera as peças | `cancelada` |
| Falha na baixa do estoque | estorna o pagamento, cancela o orçamento, libera as peças | `cancelada` |
| Execução não aceita a OS na fila de reparo | estorna o pagamento, cancela o orçamento, devolve as peças | `cancelada` |

As compensações são feitas uma de cada vez; a próxima só começa depois da confirmação da anterior. Se uma delas não for confirmada depois de todas as tentativas, a saga fica parada em `COMPENSANDO`, visível em `GET /service-orders/{id}/saga`, até um admin reenviar (`POST /service-orders/{id}/saga/retry`).

## Prazos

| Espera | Padrão | Ao vencer |
|---|---|---|
| Resposta de um serviço a um comando | 5 minutos | Reenvia o comando (até 3 tentativas); depois, compensa |
| Aprovação do orçamento pelo cliente | 7 dias | Compensa |
| Pagamento | 4 dias (a cobrança no Mercado Pago expira em 3) | Compensa |

## Observações funcionais

- A listagem de OS (`GET /service-orders`) mostra só as com trabalho pendente: exclui `finalizada`, `entregue`, `recusada` e `cancelada`.
- A ordenação prioriza `em_execucao`, depois `aguardando_pagamento`, `aguardando_aprovacao`, `em_diagnostico` e `recebida`; dentro de cada status, as mais antigas primeiro.
- O cliente acompanha a OS pelo rastreio público (`GET /service-orders/{id}/tracking`), com status, itens e histórico.
- A aprovação do orçamento (link do e-mail, sem login) e o pagamento (Mercado Pago) acontecem nos serviços de Orçamento e de Pagamento, não no OS Service.
