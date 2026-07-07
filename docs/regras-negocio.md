# Regras de Negócio

## Status da ordem de serviço

- `recebida`
- `em_diagnostico`
- `aguardando_aprovacao`
- `em_execucao`
- `finalizada`
- `entregue`
- `recusada`: orçamento recusado pelo cliente, status terminal

## Fluxo da OS

1. Cadastro do cliente por CPF/CNPJ.
2. Cadastro ou atualização do veículo por placa.
3. Inclusão dos serviços solicitados.
4. Inclusão opcional de peças/insumos.
5. Geração automática do orçamento.
6. Envio do orçamento para aprovação.
7. Aprovação e baixa de estoque.
8. Finalização e entrega.

## Cálculo da Ordem de Serviço

Quando uma OS é criada, o orçamento é calculado automaticamente com base nos serviços e peças inclusos.

### Fórmula de cálculo

```text
labor_total = soma(preco_servico * quantidade_servico)
parts_total = soma(preco_peca * quantidade_peca)
quote_total = labor_total + parts_total
```

### Exemplo prático

Supondo uma OS com:

- Serviços:
  - Troca de óleo: R$ 150,00 x 1 = R$ 150,00
  - Revisão de freios: R$ 200,00 x 1 = R$ 200,00
  - Subtotal de serviços: R$ 350,00
- Peças:
  - Óleo sintético: R$ 45,00 x 4 = R$ 180,00
  - Filtro de óleo: R$ 25,00 x 1 = R$ 25,00
  - Pastilha de freio: R$ 180,00 x 1 = R$ 180,00
  - Subtotal de peças: R$ 385,00
- Orçamento final: R$ 350,00 + R$ 385,00 = **R$ 735,00**

## Validações durante o cálculo

1. Verificação de disponibilidade de serviços: o serviço precisa existir no catálogo e estar ativo.
2. Verificação de estoque: precisa haver quantidade suficiente de peças em estoque no momento da criação.
3. Preços: o orçamento usa os preços atuais do catálogo no momento da criação.

## Baixa de estoque automática

Ao aprovar a OS, na transição para `em_execucao`:

- O sistema verifica novamente se há estoque suficiente.
- Se houver disponibilidade, reduz automaticamente a quantidade em estoque.
- Se não houver estoque, retorna erro `409 Conflict`.

Exemplo com 4 unidades de óleo:

```text
estoque_anterior = 50
estoque_apos_aprovacao = 50 - 4 = 46
```

## Estrutura do cálculo no banco

Cada item, serviço ou peça, dentro da OS armazena:

- `quantity`: quantidade do item
- `unit_price`: preço unitário no momento da criação da OS
- `subtotal`: `quantity * unit_price`, calculado e armazenado para auditoria

## Observações funcionais

- A listagem ativa de ordens retorna apenas OSs não concluídas, excluindo `finalizada`, `entregue` e `recusada`.
- A ordenação prioriza os status `em_execucao`, `aguardando_aprovacao`, `em_diagnostico` e `recebida`.
- A aprovação e a recusa externas usam token público enviado por e-mail.
- O token de orçamento é invalidado após a primeira aprovação ou recusa.
