# 2026-11-07 — Roteiro do vídeo da Fase 4 e diagramas como código

## Pedido

1. Roteiro do vídeo a partir do PDF da Fase 4, "o mais sucinto possível".
2. Os diagramas da Fase 4 com a biblioteca Python `diagrams`.

## Entregue

- **Roteiro** em `docs/roteiro-video-fase4.md` (untracked, coberto pelo `.git/info/exclude`). Ele tem um bloco por item que o PDF exige: fluxo completo pelo Postman, compensações (pasta 3), deploy do Estoque (PR com CI → push em `homologacao`) e New Relic (trace distribuído e NRQL por `order_id`). Antes dos blocos vem um checklist curto de preparação. São uns 13 minutos.
- **Diagramas** em `docs/diagramas/` (scripts + README), com os PNGs em `docs/imgs/`:
  - `arquitetura_geral_fase4.png`: entra como seção nova "Visão geral: microsserviços" no topo do `docs/arquitetura.md`.
  - `dependencia_terraform_fase4.png`: substitui o Mermaid com os 4 repositórios da Fase 3, acompanhado de uma tabela com todas as leituras entre os 9 repositórios.

## Decisões

- **Simplificar em vez de detalhar.** A primeira versão dos dois diagramas tinha setas demais e se cruzava, e a usuária pediu para limpar. Na versão final:
  - SQS e SNS aparecem como um nó só;
  - cada serviço fica num quadro com o próprio banco;
  - LoadBalancers do Orçamento e do Pagamento e o SMTP aparecem só nos rótulos;
  - no Terraform, o diagrama mostra só as etapas, e as leituras de longe foram para a tabela.
- **A tabela do Terraform veio dos `.tf`, não da documentação.** O Mermaid antigo dizia que o `infra-kubernetes` só lê o `rds_secret_arn` do banco. Na verdade ele também lê `vpc_id`, `vpc_cidr_block` e `default_route_table_id`, que são usados no peering.
- **`diagrams` fora das dependências do Poetry.** É ferramenta de documentação e precisa do Graphviz. O README de `docs/diagramas/` explica como gerar as imagens num venv à parte.
- **O drawio de infraestrutura não foi mexido.** Ele continua descrevendo a Fase 3. A visão de microsserviços ficou no diagrama novo.
