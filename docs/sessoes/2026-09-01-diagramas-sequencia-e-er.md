# 2026-09-01 — Diagramas de sequência e ER (fecha "Documentação da arquitetura")

## Contexto / pedido original

Continuação direta da sessão de 2026-08-31 ([resumo](2026-08-31-atualiza-diagramas-c4-fase3.md)): com os dois diagramas C4 (componentes e infraestrutura) já redesenhados e mergeados, faltavam os dois últimos itens da seção "Documentação da arquitetura" de `docs/proximos-passos.md` — Diagrama de Sequência e Diagrama ER.

## O que foi entregue

**PR [#29](https://github.com/phantosmia/oficina-mecanica-fiap/pull/29)** — os dois diagramas direto em `docs/arquitetura.md`, como Mermaid (mesmo padrão já usado nos diagramas de dependência entre repositórios e de fluxo de deploy do mesmo arquivo) — diferente dos dois diagramas C4 da sessão anterior, esses não precisaram de imagem `.drawio.png`, então não houve rodada de revisão visual iterativa desta vez.

### Diagrama ER

`erDiagram` do schema completo (`app/shared/models.py`): `clients`, `vehicles`, `services_catalog`, `parts`, `service_orders`, `service_order_services`, `service_order_parts`. Conferido contra o código, não só a partir da memória do schema:

- `ON DELETE CASCADE` em `clients → vehicles → service_orders` e `service_orders → itens` (apagar o pai apaga os filhos).
- `ON DELETE RESTRICT` em `services_catalog`/`parts → itens da ordem` — de propósito o oposto, porque `unit_price`/`subtotal` são um snapshot do preço no momento da criação da ordem (auditoria), não uma referência viva.
- Não existe tabela de admin/usuário — confirmado lendo `app/auth/controller.py`: o login é validado contra `ADMIN_USERNAME`/`ADMIN_PASSWORD` (env vars), não contra uma linha no banco.

### Diagrama de sequência

Três `sequenceDiagram` separados, cada um verificado linha a linha contra o código-fonte antes de escrever (não a partir dos ADRs de memória):

1. **Emissão do token via CPF** (`POST /auth/cpf`) — lido `handler.py` (`authenticate_handler`) do `oficina-mecanica-lambda-auth`: valida formato do CPF, consulta `find_client_by_document` no RDS, trata cliente inexistente/inativo com a mesma resposta 404 de propósito (não vaza qual dos dois casos é), gera o JWT.
2. **Validação do token numa rota `/api/*`** — lido `authorizer_handler` do mesmo arquivo: só decodifica/valida a assinatura (sem tocar no RDS), devolve `isAuthorized`; a entrega da requisição pro cluster continua sendo o API Gateway via VPC Link, nunca o Lambda — mesmo ponto que gerou várias iterações no diagrama de infraestrutura da sessão anterior.
3. **Abertura de ordem de serviço** (`POST /service-orders`) — lido `CreateServiceOrderUseCase.execute` (`app/service_orders/application/use_cases.py`) linha a linha: `upsert_client`, `upsert_vehicle`, loop de validação de cada serviço do catálogo (404 se não achar), loop de validação de cada peça com checagem de estoque (409 se insuficiente), cálculo de `labor_total`/`parts_total`/`quote_total`, persistência com status inicial `recebida` (confirmado em `value_objects.py`), e o evento customizado `record_service_order_created` pro New Relic.

## Decisões tomadas e por quê

- **Mermaid em vez de imagem no draw.io**: ao contrário dos diagramas C4 da sessão anterior (que já existiam como imagem e precisavam ser redesenhados mantendo o formato), esses dois eram novos — não havia motivo pra introduzir um novo par de arquivos `.drawio.png` quando o arquivo já usa Mermaid nativamente pra esse tipo de diagrama (fluxo/sequência), e fica versionado como texto revisável em PR.
- **Uma correção de precisão durante a escrita**: o texto inicial do ER dizia que `quote_token` era "invalidado (setado como usado)" após a resposta do orçamento — conferido no código (`execute_approval`/`RejectOrderUseCase`) que na verdade o valor volta a `null`, não existe nenhum flag "usado". Corrigido antes de commitar.

## Ajustes feitos depois do primeiro push (mesma PR #29)

- **Bug de render no GitHub**: um `;` dentro do texto de uma mensagem do `sequenceDiagram` ("Emissão do token via CPF") quebrava o parser do Mermaid no GitHub (`;` é tratado como terminador de statement mesmo dentro do texto da label) — reportado pela própria renderização da PR, corrigido trocando por travessão. Vale lembrar disso da próxima vez que escrever texto de mensagem em Mermaid: evitar `;` dentro do texto.
- **Reordenação do diagrama ER**: `SERVICES_CATALOG` cruzava visualmente com as conexões de `SERVICE_ORDERS`. Mermaid `erDiagram` não tem posicionamento manual (sem `direction`, sem x/y por entidade) — o único controle disponível é a ordem de declaração das relações/blocos de atributos, que foi ajustada (moveu `SERVICES_CATALOG` pro fim da lista de relações e do bloco de atributos). É um ajuste best-effort, não uma garantia de zero cruzamento.

## Pendências para a próxima sessão

A seção "Documentação da arquitetura" de `docs/proximos-passos.md` está **completa** agora (Diagrama de Componentes, Diagrama de Infraestrutura, Diagrama de Sequência, Diagrama ER — todos `[x]`). Restam as outras seções do checklist: **Entregáveis finais** (vídeo de demonstração da Fase 3, PDF único de entrega, links de Swagger/Postman nos READMEs), **Collaborators** (aceite pendente do `soat-architecture` em 3 dos 4 repositórios) e os **débitos técnicos conhecidos** (ECR duplo-gerenciado, Lambda sem o proxy unificado, credenciais default em homologação/produção, instrumentação New Relic da Lambda/Cloud Integration inativas).
