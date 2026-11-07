# 2026-11-07 — Ambiente para o vídeo da Fase 4, gravação e documento de entrega

Continuação de [2026-11-07 — Roteiro do vídeo e diagramas](2026-11-07-roteiro-video-e-diagramas.md), na mesma data.

## Pedido

1. Subir tudo na AWS para gravar o vídeo. O Lab tinha sido reiniciado.
2. Ajudar durante a gravação: Postman, Mercado Pago, OBS, deploy do Estoque e New Relic.
3. Gerar o documento de entrega (.docx), que a usuária vai converter para PDF.

## Entregue

- **`homologacao` reprovisionado do zero.** A conta continuou a mesma (`340919830422`), mas os recursos tinham sido apagados.
  - Ordem: backend local, banco, cluster, Catálogo, os 4 participantes em paralelo, `infra/aws` e Lambda.
  - Os 6 serviços ficaram com `/health` 200.
  - Os seeds rodaram com o Estoque antes do Catálogo.
- **Environment do Postman com as URLs reais:** `postman/homologacao-2026-11-07.postman_environment.json`. Fica só local, coberto por um padrão no `.git/info/exclude`.
  - Catálogo, Estoque e Execução são `ClusterIP` e ficam em `localhost:8001/8002/8003`, por port-forward.
- **Mudança para o bloco de deploy do vídeo:** um parágrafo no README do Estoque sobre a ordem dos seeds ([oficina-mecanica-estoque#6](https://github.com/phantosmia/oficina-mecanica-estoque/pull/6)), mergeado e publicado na `homologacao` pela usuária durante a gravação.
- **Vídeo gravado** em 13 partes, 13:33 no total. Falta juntar as partes e subir.
- **Documento de entrega** em `~/entrega-fase4.docx`, fora do repositório. As seções seguem o PDF:
  - participantes;
  - links;
  - diagrama geral;
  - estratégia de saga;
  - divisão dos serviços;
  - tecnologias.
  
  O texto foi tirado do README, das ADRs 0008, 0009 e 0011 e das RFCs 0006 a 0008. O link do vídeo ainda é um marcador. Os participantes foram copiados da entrega da Fase 1, e a usuária vai confirmar.
- **Conferência dos requisitos do PDF:**
  - os 6 repositórios têm Dockerfile, k8s, CI/CD, README com badges de cobertura e quality gate, e Swagger/Postman;
  - cobertura entre 91,8% e 97,0%, quality gate OK em todos;
  - `main` protegida nos 6;
  - os 9 repositórios estão públicos.

## Problemas e decisões

- **SCP nova no backend.** O Lab passou a negar `s3:GetBucketObjectLockConfiguration`. O apply do `infra/backend` criou o bucket, mas o deixou *tainted*. A saída foi `terraform untaint` seguido de `plan -refresh=false`, e o passo ficou registrado em `docs/kubernetes-aws.md`.
- **Deploy do OS Service só por push na `homologacao`.** No `workflow_dispatch`, o `deploy-aws.yml` usa o environment `aws`, que não tem credenciais. O jeito foi um merge da `main` na `homologacao` seguido de push. Também registrado em `docs/kubernetes-aws.md`.
- **Orçamento sem SMTP em homologação.** `SMTP_ENABLED=false`, então nenhum e-mail sai. No vídeo, o link de aprovação vem de `GET /quotes/{order_id}` (`approval_url`), que é a requisição "Ver orçamento (admin)" da coleção.
- **Pagamento no sandbox** exige estar logado como comprador de teste. A janela anônima precisa entrar no Mercado Pago antes de abrir o link, como já estava no README do Pagamento.
- **Deploy verde sem pod novo.** Na gravação, o `workflow_dispatch` rodou na `homologacao` antes de a `main` ser levada para ela, e a imagem saiu com a tag antiga. Registrado em `docs/kubernetes-aws.md`.
- **NRQL por `order_id`.** O atributo é texto, então a query é `WHERE order_id = '1'`, com aspas. Na interface nova do New Relic, o editor fica em *All Capabilities → Query your data*.
- **Git por HTTPS.** Foi configurado `gh auth setup-git`, global, para o push não pedir usuário.
- **Branch local sem uso** no Estoque: `docs/seed-estoque-antes-do-catalogo` foi criada para regravar o PR, mas o #6 acabou mergeado. Pode ser apagada.
