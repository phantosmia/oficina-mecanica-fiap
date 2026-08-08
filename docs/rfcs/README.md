# RFCs (Request for Comments)

RFCs registram **decisões técnicas relevantes** que envolvem trade-offs entre alternativas concretas — geralmente escolhas de tecnologia ou de estratégia que impactam todo o projeto (nuvem, banco de dados, autenticação). Diferem dos ADRs por documentarem também as alternativas descartadas e o raciocínio de comparação entre elas, não só a decisão final.

Uma RFC pode ser revisitada se o contexto mudar (por exemplo, migrar de AWS Academy para uma conta AWS própria). Quando isso acontecer, adicione uma seção "Revisão" no próprio documento em vez de apagar o histórico.

## Índice

| RFC | Título | Status |
|---|---|---|
| [0001](0001-escolha-da-nuvem.md) | Escolha da nuvem (AWS) | Aceito |
| [0002](0002-escolha-do-banco-de-dados.md) | Escolha do banco de dados (PostgreSQL) | Aceito |
| [0003](0003-estrategia-de-autenticacao.md) | Estratégia de autenticação | Aceito |

## Template

```markdown
# RFC-000X: Título da decisão

| | |
|---|---|
| **Status** | Proposto / Aceito / Substituído |
| **Data** | AAAA-MM-DD |

## Contexto
Qual problema motivou a decisão? Quais restrições existiam (prazo, curso, custo, equipe)?

## Alternativas consideradas
Liste as opções avaliadas, com prós e contras de cada uma.

## Decisão
O que foi escolhido e por quê, de forma direta.

## Consequências
O que essa escolha implica — positivo e negativo — e o que fica em aberto para revisão futura.
```
