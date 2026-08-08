# ADR-0003: PostgreSQL gerenciado (RDS) em produção

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-07-03 |

## Contexto

O [RFC-0002](../rfcs/0002-escolha-do-banco-de-dados.md) decidiu o **motor** de banco (PostgreSQL). Faltava decidir **onde** ele roda em cada ambiente: local/CI usam containers descartáveis (Docker Compose e Testcontainers), mas em produção AWS era preciso escolher entre manter o Postgres dentro do próprio cluster EKS ou usar um serviço gerenciado.

## Decisão

Rodar o PostgreSQL como:

- **`StatefulSet` dentro do cluster** nos overlays `local` e Minikube (`k8s/overlays/local`) — adequado para desenvolvimento, sem exigir infraestrutura externa.
- **Amazon RDS**, fora do cluster EKS, nos overlays `aws` e `aws-academy` — o `StatefulSet` de Postgres é removido nesses overlays e a API/o Job de migrations apontam para o endpoint do RDS provisionado pelo Terraform (`infra/aws`).

## Alternativas consideradas

- **Postgres self-hosted no EKS via `StatefulSet` também em produção**: rejeitado. Exigiria gerenciar manualmente backup, failover, patching de versão e volumes persistentes (EBS) dentro do próprio cluster — trabalho que o RDS já resolve nativamente, e que não é o foco do desafio (orquestração de aplicação, não administração de banco de dados).
- **RDS também em ambiente local/CI**: rejeitado por custo e por dependência de rede/credenciais AWS para simplesmente rodar os testes ou subir a API localmente — quebraria o fluxo de desenvolvimento offline e o isolamento do CI via Testcontainers.

## Consequências

- Produção ganha backup automatizado, patching gerenciado e separação clara entre ciclo de vida do banco e do cluster — o EKS pode ser recriado sem afetar os dados.
- Isso introduz **assimetria entre ambientes**: o overlay local roda Postgres no cluster, o overlay AWS não. Qualquer mudança nos manifests de banco precisa ser avaliada nos dois lugares (`k8s/base` vs. remoção nos overlays AWS).
- O `Job` de migrations e a API em produção dependem de conectividade de rede da VPC até o endpoint do RDS — uma falha de rede ou de Security Group nesse caminho impede totalmente o deploy, diferente do ambiente local onde o banco é um pod na mesma rede do cluster.
- Escalar a API via HPA (ver [ADR-0002](0002-uso-de-hpa-para-escalabilidade.md)) não escala o RDS: o número de conexões simultâneas ao banco cresce com o número de réplicas da API, e o RDS tem um teto de conexões próprio que não é gerenciado por este HPA.
