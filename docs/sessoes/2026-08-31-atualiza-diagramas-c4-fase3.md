# 2026-08-31 — Atualiza diagramas C4 (componentes e infraestrutura) para a Fase 3

## Contexto / pedido original

Continuação do item "Documentação da arquitetura" de `docs/proximos-passos.md`: os dois diagramas C4 (`docs/imgs/diagramac4_componentes_...png` e `docs/imgs/diagrama_de_infraestrutura_...png`) estavam desatualizados desde antes da separação em 4 repositórios da Fase 3, com notas manuais em `docs/arquitetura.md` avisando disso. A sessão trabalhou o redesign dos dois no draw.io (a usuária redesenhou, Claude revisou cada iteração contra o código/Terraform real e o texto de `arquitetura.md`).

## O que foi entregue

**PR [#27](https://github.com/phantosmia/oficina-mecanica-fiap/pull/27)** — atualiza as duas imagens `.drawio.png` e o texto de leitura correspondente em `docs/arquitetura.md`, mais `docs/proximos-passos.md` marcando os dois itens como concluídos.

### Diagrama de componentes

- New Relic como serviço externo, com as duas origens reais (ADR-0007): `FastAPI Application` via agente APM, `Shared` via eventos customizados (`app/shared/telemetry.py`, chamado por `service_orders`).
- Sub-limites `Entrada HTTP`/`Contextos de Domínio` explícitos; `Service Orders` marcado como o único contexto acessado pelas duas vias de entrada (autenticada e pública).

### Diagrama de infraestrutura

Passou por **6 iterações** de revisão (cada uma comparada contra o Terraform real dos 4 repositórios, não só visualmente):

1. Corrigido o fluxo de entrada: o Lambda **não** atua como proxy da requisição — o ADR-0006 tem duas rotas no API Gateway (pública e autenticada) convergindo no **mesmo** Load Balancer interno via VPC Link.
2. Descoberto e corrigido: o diagrama tinha uma VPC única agrupando tudo, mas o ADR-0005 define **duas VPCs reais** (cluster e banco) — confirmado o VPC Peering entre elas (`aws_vpc_peering_connection.eks_to_database`, em `oficina-mecanica-infra-kubernetes/main.tf`), usado por `API Deployment/Service` e `Alembic Migration Job` pra alcançar o RDS.
3. Diferenciadas as duas Lambdas do ADR-0005: `Lambda authorize` (Authorizer do API Gateway, sem VPC, só valida assinatura do JWT, chamada a cada requisição autenticada) vs. `Lambda Authenticate` (dentro da VPC do banco, consulta o RDS pra emitir o JWT a partir do CPF, chamada só no login).
4. **Achado importante, fora do escopo do diagrama em si**: só 2 dos 4 pontos de instrumentação do ADR-0007 estão de fato ativos hoje. Confirmado via `gh secret list`/`gh api` nos 4 repositórios — `NEW_RELIC_LICENSE_KEY` está configurado em `oficina-mecanica-fiap` (environments `homologacao`/`producao`, cobre o APM) e em `oficina-mecanica-infra-kubernetes` (secret de repo, cobre o `nri-bundle`), mas **não** em `oficina-mecanica-lambda-auth` (nem secret de repo, nem os GitHub Environments — que nem existem nesse repositório apesar do `ci.yml` referenciar `environment: ${{ github.ref_name }}`). A Cloud Integration AWS (RDS/API Gateway) também não tem workflow de CI que a aplique — é manual por design (`infra/newrelic-aws-integration/main.tf`), e é o item que o próprio ADR-0007 já registra como bloqueado no AWS Academy Lab. Registrado como débito técnico novo em `docs/proximos-passos.md`.
5. Decisão de escopo: **não repetir boundary por repositório Terraform** no diagrama de infraestrutura — essa informação já está mais precisa no diagrama de dependência Mermaid (mesmo arquivo). Agrupado por função em vez disso.
6. Ajustes finos de rótulo (setas sempre com verbo, "Load Balancer Interno" em vez de "public subnets", dois rótulos distintos pras duas Lambdas).

## Decisões tomadas e por quê

- **Diagramas por função, não por repositório**: evita duplicar a mesma informação (divisão em 4 repos) que o diagrama de dependência Terraform já cobre com mais precisão (nomes exatos de outputs, ordem de apply).
- **New Relic com uma seta mergeada** (`APM + nri-bundle → New Relic`) em vez de duas setas separadas: escolha consciente de simplicidade visual, aceitando perder a distinção entre os dois mecanismos no diagrama (fica só no texto de `arquitetura.md`).
- **VPC Peering desenhado no nível de VPC-a-VPC**, não saindo de cada componente (`API Deployment/Service`, `Alembic Migration Job`) individualmente até o RDS — mais fiel ao que o Terraform realmente cria (uma relação entre VPCs inteiras) e evita poluir o diagrama com setas repetidas.

## Pendências para a próxima sessão

- Restam dois itens da mesma seção de `docs/proximos-passos.md`: **Diagrama de Sequência** (autenticação via CPF + abertura de OS) e **Diagrama ER** do banco — nenhum dos dois existe ainda em lugar nenhum.
- Novo débito técnico registrado (não bloqueia a entrega, mas vale corrigir): configurar `NEW_RELIC_LICENSE_KEY`/`NEW_RELIC_ACCOUNT_ID` em `oficina-mecanica-lambda-auth` pra ativar de fato a instrumentação da Lambda — ver `docs/proximos-passos.md`.
