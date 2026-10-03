# 2026-10-03 — Desenho da Fase 4: 5 microsserviços com saga orquestrada

## Contexto / pedido original

Início da Fase 4 (`SOAT - Fase 4 - Tech challenge.pdf`): refatorar o sistema em microsserviços (mínimo 3, cada um com repositório, infraestrutura e banco próprios, pelo menos um SQL e um NoSQL), com mensageria, Saga Pattern com compensação, BDD, cobertura ≥ 80%, SonarQube/similar no CI e deploy automatizado no Kubernetes. Antes de escrever código, a sessão foi dedicada a decidir o desenho com a usuária e registrá-lo.

## O que foi entregue

- **PR [#35](https://github.com/phantosmia/oficina-mecanica-fiap/pull/35)**: RFC-0006 (decomposição), RFC-0007 (SQS + SNS), ADR-0008 (saga orquestrada no OS Service), ADR-0009 (persistência poliglota), `docs/saga.md` (contrato de comandos/eventos/compensações/prazos), ADR-0001 marcada como substituída e seção da Fase 4 em `docs/proximos-passos.md`.
- **4 repositórios novos**, públicos e vazios: [`oficina-mecanica-catalogo`](https://github.com/phantosmia/oficina-mecanica-catalogo), [`oficina-mecanica-estoque`](https://github.com/phantosmia/oficina-mecanica-estoque), [`oficina-mecanica-orcamento-pagamento`](https://github.com/phantosmia/oficina-mecanica-orcamento-pagamento), [`oficina-mecanica-execucao`](https://github.com/phantosmia/oficina-mecanica-execucao). Convite ao `soat-architecture` (`write`) enviado nos 4.
- `CLAUDE.md` local (não versionado) com a tabela de repositórios atualizada.

## Decisões tomadas e por quê

As decisões em si estão nos RFCs/ADRs. Aqui fica o caminho até elas, que não aparece nos documentos:

- **Proposta inicial era de 3 serviços** (os sugeridos no PDF). A usuária escolheu **4** (separando Catálogo & Estoque) e depois **5**: ao discutir se algum serviço além da Execução se beneficiaria de banco de documentos, ficou claro que o catálogo (muita leitura, atributos variáveis por tipo de peça) e o saldo de estoque (reserva transacional tudo-ou-nada) têm naturezas opostas. Separados, o Catálogo usa DynamoDB e o Estoque usa PostgreSQL. Efeito colateral bom: o Catálogo sai da saga e vira o caso de "REST síncrono quando necessário" do PDF.
- **Orquestrador num repositório próprio foi considerado e descartado** (pergunta da usuária): o estado da saga e o status da OS ficariam em bancos diferentes, exigindo uma segunda saga só para sincronizá-los. Dentro do OS Service, os dois mudam na mesma transação. Ficou registrado como evolução possível na ADR-0008.
- **Banco colunar para Orçamento & Pagamento foi considerado e descartado** (pergunta da usuária): colunar analítico lida mal com atualização de linha e transação; wide-column não tem transação entre linhas, e a idempotência do webhook do Mercado Pago depende disso. Registrado na ADR-0009.
- **Saga orquestrada e SQS + SNS** foram escolhidos pela usuária entre as opções apresentadas, sem divergência.
- **Mudança na máquina de status da OS** (consequência do exemplo de fluxo do PDF): o diagnóstico passa para depois do pagamento, dentro da Execução, e surgem `aguardando_pagamento` e `cancelada`. Ainda não implementado; `docs/regras-negocio.md` precisa ser atualizado junto com o código.

## Incidente

Um `git add docs` incluiu os roteiros de vídeo (`docs/roteiro-video*.md`, mantidos fora do Git de propósito) no commit já enviado. Eles foram removidos com `commit --amend` + `push --force-with-lease` na branch da PR, antes de a PR ser aberta, com autorização explícita da usuária. Ao commitar em `docs/`, adicionar arquivos por caminho em vez do diretório inteiro.

## Pendências para a próxima sessão

- Etapa 2 do checklist da Fase 4 em `docs/proximos-passos.md`: começar pelo **Catálogo** (extração mais simples, código já existe em `app/service_catalog` e `app/parts`).
- **Dependem da usuária**: conta de desenvolvedor e *access token* de teste do Mercado Pago (antes do serviço de Orçamento & Pagamento) e login no SonarCloud com a organização `phantosmia` + token (antes do CI).
- Confirmar no AWS Academy Lab que DynamoDB, SQS e SNS estão liberados, assim que houver credenciais válidas.

## Atualização (mesma sessão, depois do merge da PR #35)

- **Diagnóstico define o orçamento (opção B)**: foram apresentadas três opções para onde fica o diagnóstico: (A) depois do pagamento, que era o que estava na PR #35; (B) antes do orçamento, com o mecânico escolhendo serviços e peças; (C) antes do orçamento, mas mantendo os itens informados na abertura, como nas fases anteriores. A recomendação foi C, por ser a menor mudança sobre regras já entregues. A usuária escolheu **B**, a mais fiel ao funcionamento de uma oficina real. Consequências: a abertura da OS deixa de receber itens, a Execução participa duas vezes da saga (`EnfileirarDiagnostico` e `EnfileirarReparo`) e quem consulta o Catálogo por REST passa a ser a Execução, ao concluir o diagnóstico, e não o OS Service. ADR-0008, RFC-0006, ADR-0009 e `docs/saga.md` foram ajustados em uma PR nova.
- **PR #35 foi mergeada antes dos dois últimos commits** (README com a tabela única de repositórios). Eles foram reaplicados (*cherry-pick*) na mesma PR nova.
- **Catálogo implementado** ([oficina-mecanica-catalogo#1](https://github.com/phantosmia/oficina-mecanica-catalogo/pull/1), CI verde). Decisões de implementação que valem para os próximos serviços:
  - **`table.meta.client` já serializa tipos**: o cliente do *resource* do boto3 converte tipos Python sozinho. Serializar à mão com `TypeSerializer` aplica a conversão duas vezes, e o teste pegou isso (o moto acusou `unhashable type: 'dict'`; na AWS real seria um `ValidationException`).
  - **Ordenação no GSI sem acento** (`sort_key`): sem isso "Óleo" vinha depois de "Pastilha". Só apareceu ao rodar no LocalStack com os dados de exemplo.
  - **Testes com moto em vez de LocalStack/Testcontainers**: rápidos, sem Docker no CI. O LocalStack fica para o docker-compose e para a validação manual.
  - **Namespace Kubernetes próprio por serviço** (`oficina-catalogo`) e **relay da outbox como Deployment separado, com 1 réplica**.
- **Correção de processo (apontada pela usuária)**: a opção B tinha sido aplicada reescrevendo a ADR-0008, a RFC-0006, a ADR-0009 e a RFC-0007, que já estavam aprovadas (mergeadas na #35). Isso contraria a convenção dos próprios READMEs de `docs/adrs/` e `docs/rfcs/`. Refeito na mesma PR #36: os quatro voltaram à versão aprovada; a decisão ganhou a **ADR-0010** (com as alternativas A/B/C); a ADR-0008 ficou "parcialmente substituída pela ADR-0010"; a RFC-0006 e a RFC-0007 ganharam seções "Revisão"; a ADR-0009, uma nota. O `docs/saga.md` continua sendo editado no lugar, porque é o contrato vivo entre os serviços, não um registro de decisão.
