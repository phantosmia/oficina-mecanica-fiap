# 2026-10-10 — Microsserviço de Orçamento

## Contexto / pedido original

Continuação da sessão de [2026-10-03](2026-10-03-desenho-fase4-microsservicos.md), depois do merge das PRs #38/#39 (contrato da saga e RFC-0008/ADR-0011) e dos serviços de Catálogo, Estoque e Execução. Pedido: implementar o serviço de **Orçamento**, o primeiro dos dois que saíram da separação de Orçamento & Pagamento.

## O que foi entregue

- **[oficina-mecanica-orcamento#1](https://github.com/phantosmia/oficina-mecanica-orcamento/pull/1)** (CI verde): o serviço completo. Ver o README de lá para o detalhe.
- **Nesta PR do repositório principal**: payloads das mensagens do Orçamento em `docs/saga.md` e o item marcado em `docs/proximos-passos.md`.

## Decisões tomadas e por quê

- **Página HTML para o link do e-mail** (não estava no plano): a primeira validação no docker-compose mostrou que o link levava a uma rota JSON, e aprovar exigia um `POST`. Um cliente que clicasse no link veria JSON cru e não teria como aprovar. Foi acrescentada uma página mínima (sem framework de templates, só f-strings com `html.escape`) com itens, totais e os botões Aprovar/Recusar; as rotas JSON continuam para uso por API. O e-mail aponta para a página (`/orcamento/{token}`).
- **Mailpit no docker-compose do serviço**: SMTP de teste com caixa de entrada web (`http://localhost:8025`). Permite mostrar no vídeo o e-mail chegando e o cliente clicando no link, sem SMTP real.
- **Um orçamento por OS** (`QUOTE#<order_id>`), em vez de por `quote_id`: simplifica o acesso do orquestrador e do admin (que pensam em OS) e dá unicidade de graça.
- **Marcador de saga compensada** (`COMPENSATED#<saga_id>`), o equivalente do *tombstone* de reserva do Estoque: aqui o risco de um `GerarOrcamento` atrasado é pior, porque mandaria ao cliente o link de uma OS já cancelada.
- **E-mail depois do commit, em tentativa única**, com reenvio manual pelo admin, em vez de pôr o e-mail numa outbox própria: falha de SMTP não pode travar a saga, e um e-mail perdido não deixa nada inconsistente (o admin vê o link em `GET /quotes/{order_id}`).
- **Service `LoadBalancer`** no overlay `aws-academy`: o cliente abre o link de fora do cluster. A forma de exposição definitiva (API Gateway, como o OS Service na Fase 3) fica para a etapa de infraestrutura.

## OS Service e orquestrador (mesma sessão)

- **Nesta PR**: o OS Service refatorado para o papel da Fase 4 e o orquestrador (`app/saga/`), além do `docker-compose.yml` com os 6 serviços. Ver `docs/proximos-passos.md` (etapas 3 e 4) para o que foi entregue.
- **Máquina de estados como domínio puro** (`ServiceOrderSaga`): recebe (estado, evento) e devolve uma `Decision` (comandos, mudança na OS, aviso ao cliente). Os 21 testes unitários cobrem linha a linha as tabelas de `docs/saga.md`; a camada de aplicação só grava a decisão numa transação.
- **Compensações uma de cada vez**, cada uma esperando a confirmação da anterior (não em paralelo): mais lento, mas a ordem do `docs/saga.md` (estornar antes de liberar a reserva etc.) é respeitada e fica legível no histórico. Compensação que esgota as tentativas fica parada em `COMPENSANDO` com reenvio manual, nunca é dada como concluída sem confirmação.
- **Mensagens fora de ordem aceitas onde fazem sentido**: `DiagnosticoIniciado`/`DiagnosticoConcluido` antes do `DiagnosticoEnfileirado`, `PagamentoConfirmado` antes do `CobrancaCriada`. Eventos atrasados durante a compensação são ignorados (o participante que está compensando já trata o caso, ex.: o Pagamento estorna um pagamento que entrou no meio).
- **Abertura da OS e início da saga na mesma transação**: o `CreateServiceOrderUseCase` recebe uma porta `ISagaStarter`, implementada pela saga com a mesma sessão SQLAlchemy. Por isso o repositório de OS deixou de fazer commit sozinho.
- **Testes do OS Service passam a usar `TEST_DATABASE_URL`** em vez de `DATABASE_URL` (mesma proteção dos outros serviços: a suíte recria o schema a cada caso). O `CLAUDE.md` local e `docs/testes-carga-ci.md` foram atualizados.
- **Validação com os 6 serviços reais** (docker-compose): fluxo até a cobrança no Mercado Pago real e duas compensações reais funcionaram na primeira execução, sem ajuste de contrato entre os serviços: os payloads documentados em `docs/saga.md` na etapa de cada participante bateram com o que o orquestrador envia.

## Pendências para a próxima sessão

- **Pagamento** (PostgreSQL + Mercado Pago, Checkout Pro via API de Orders), com as credenciais de teste já criadas.
- Depois: o **OS Service com o orquestrador**, que liga os 6 serviços.
