# RFC-0002: Escolha do banco de dados (PostgreSQL)

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-06-17 |

## Contexto

A primeira versão do MVP foi implementada com **SQLite**, por simplicidade de setup local durante a fase inicial do projeto. Com a evolução do sistema — múltiplos usuários administrativos, fluxos concorrentes de criação de OS, baixa de estoque na aprovação de orçamento e atualização de status — o banco em arquivo passou a ser uma limitação real, tanto para a integridade dos dados quanto para a fidelidade entre ambiente local, CI e produção.

## Alternativas consideradas

- **Manter SQLite**: descartado. Banco em arquivo com locking em escrita concorrente não é adequado a uma oficina com múltiplos usuários operando OS em paralelo; também não existe como serviço gerenciado equivalente em produção (RDS não oferece SQLite), quebrando a paridade local/produção.
- **MySQL**: alternativa cliente-servidor viável, mas sem vantagem concreta sobre PostgreSQL para os requisitos do projeto (constraints, MVCC, tipos), e com suporte nativo no RDS equivalente ao do PostgreSQL — não havia motivo para preferi-lo.
- **PostgreSQL**: escolhido.

## Decisão

Migrar para **PostgreSQL 16**, executado como processo dedicado em todos os ambientes (Docker Compose local, Testcontainers no CI, RDS em produção AWS), motivado por:

- **Modelo cliente-servidor real**, aproximando local/CI/produção e eliminando particularidades do SQLite.
- **Concorrência e integridade**: MVCC, transações reais e constraints (`ON DELETE CASCADE`/`RESTRICT`) honradas nativamente — necessário para os fluxos concorrentes de OS e estoque.
- **CI determinístico**: Testcontainers provisiona um `postgres:16-alpine` efêmero por execução de teste, sem exigir infraestrutura externa no pipeline.
- **Aderência ao ambiente de execução**: como toda a stack já roda em containers, manter o banco como serviço separado deixa o ambiente local idêntico ao de CI e ao de produção.

A migração foi feita sem alterar a Clean Architecture: domínio, casos de uso e controllers permanecem intactos, já que o acesso a dados está isolado nos adapters de repositório (`app/<contexto>/adapters/sqlalchemy_repository.py`).

## Consequências

- Ambiente local exige Docker (Postgres via Compose ou Testcontainers); não é mais possível rodar a API só com um arquivo de banco.
- Em produção AWS, o PostgreSQL roda como **RDS gerenciado**, fora do cluster EKS — ver [ADR-0003](../adrs/0003-postgresql-gerenciado-rds.md) para o detalhamento dessa decisão de infraestrutura.
- Ganho de robustez (MVCC, constraints reais) em troca de uma dependência de infraestrutura adicional que não existia com SQLite.
