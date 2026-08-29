# Próximos passos — Fase 3

Checklist vivo do que falta pra fechar os requisitos do PDF da Fase 3 (`13SOAT - Fase 3 - Tech Challenge.pdf`, na raiz do repo). Diferente de `docs/sessoes/` (log histórico, um arquivo por sessão, nunca reescrito), este arquivo é **atualizado in-place**: marque itens como feitos, apague o que não se aplica mais, adicione o que surgir. Ver também "Continuidade entre sessões" no `CLAUDE.md`.

## Documentação da arquitetura (exigência explícita do PDF)

- [ ] **Diagrama de Sequência** do fluxo de autenticação via CPF (cliente → Lambda → API Gateway → JWT) e de abertura de ordem de serviço. Não existe nenhum ainda — nem em `docs/arquitetura.md` nem em nenhum dos outros 3 repositórios.
- [ ] **Diagrama ER** do banco de dados, com explicação dos relacionamentos. `docs/adrs/0003-postgresql-gerenciado-rds.md` já traz a justificativa formal da escolha do banco (texto), mas falta o diagrama ER em si — não existe imagem nenhuma em `docs/imgs/` além do C4 de componentes e do diagrama de infraestrutura.
- [ ] **Diagrama de Componentes** (`docs/imgs/diagramac4_componentes_oficina_mecanica_fiap.drawio.png`) e **diagrama de infraestrutura** (`docs/imgs/diagrama_de_infraestrutura_oficina_mecanica_fiap.drawio.png`) estão **desatualizados**: ambos foram desenhados antes da separação em 4 repositórios da Fase 3 (o próprio `docs/arquitetura.md` já tem notas manuais avisando disso). Precisam ser redesenhados para refletir a arquitetura atual (4 repos, API Gateway, Lambda, EKS com New Relic, etc.) — as notas escritas já documentam o que mudou, útil como roteiro pra quem for redesenhar.

## Entregáveis finais (Portal do Aluno)

- [ ] **Vídeo de demonstração**: `docs/roteiro-video.md` existente é o roteiro da **Fase 2** (cobre só deploy, CI/CD, consumo de API e escalabilidade). A Fase 3 exige também: autenticação com CPF, dashboard de monitoramento **com análise ao vivo**, e logs/traces em execução. Precisa escrever um roteiro novo (ou adaptar o atual) cobrindo os 6 itens do PDF e gravar (até 15 min, YouTube/Vimeo público ou não listado).
- [ ] **PDF único de entrega**: links dos 4 repositórios, link do vídeo, links das documentações (RFCs/ADRs/diagramas) e confirmação do usuário `soat-architecture` adicionado a todos os repositórios. Não iniciado.
- [ ] **README de cada repositório — link para Swagger/Postman**: hoje os READMEs só apontam pro Swagger local (`http://localhost:8000/docs`). O PDF pede link pro Swagger/Postman das APIs — vale considerar linkar o Swagger do ambiente deployado (`http://<load-balancer>:8000/docs` de `homologacao`/`producao`, sabendo que o hostname muda a cada recriação do Service) ou publicar uma collection do Postman.

## Collaborators

- [ ] `soat-architecture` (permissão `write`): convite **enviado** em `oficina-mecanica-infra-kubernetes`, `oficina-mecanica-infra-banco-dados` e `oficina-mecanica-lambda-auth`; já estava aceito em `oficina-mecanica-fiap`. Aceite dos outros 3 ainda **pendente** — não dá pra forçar, só verificar depois (`gh api repos/phantosmia/<repo>/collaborators --jq '.[].login'`, sem aparecer em `.../invitations`).

## Débitos técnicos conhecidos (não bloqueiam a entrega, mas valem correção)

- [ ] **ECR duplo-gerenciado**: o repositório ECR (`oficina-mecanica-fiap`, único por conta AWS) está no Terraform state de `homologacao` **e** de `producao` simultaneamente (contornado via `terraform import` nos dois, porque o Terraform do `oficina-mecanica-infra-kubernetes` tenta criá-lo em cada ambiente). Risco: `terraform destroy` completo num dos dois ambientes apaga o ECR que o outro também usa. Correção proposta: ECR só é criado num ambiente "dono" (ex.: só em `producao`, via `count`/`var.environment`), os outros leem via `terraform_remote_state` — não implementado ainda.
- [ ] **Lambda sem o proxy unificado do API Gateway**: `eks_alb_listener_arn` está vazio em `homologacao`/`producao` porque o deploy usa o modo `aws-academy` (Service Kubernetes tipo `LoadBalancer`, não Ingress/ALB — o ADR-0006 assume o modo `aws` completo, com AWS Load Balancer Controller, que exige IAM bloqueado no Academy Lab). Consequência: a Lambda cobre só a autenticação via CPF (requisito literal do PDF, funcionando), mas a rota unificada "API Gateway como único ponto de entrada para tudo" (ADR-0004) não está ativa nesses ambientes.
- [ ] `ADMIN_PASSWORD`/`JWT_SECRET_KEY` usando os **defaults do código** (`Admin@123` / `change-me-in-production`) em `homologacao`/`producao`, por não terem secret dedicado configurado no GitHub Environment. Funciona, mas não é uma senha/chave própria do ambiente.

## Coisas que dependem do estado do AWS Academy Lab (reavaliar a cada sessão, não assumir)

- [ ] **Ambiente `dev`** foi destruído deliberadamente (banco + cluster) para caber `homologacao`+`producao` dentro da cota de 5 VPCs/região da conta. Recriar só se necessário, sabendo que a cota provavelmente vai barrar de novo sem derrubar outro ambiente antes.
- [ ] **Credenciais AWS Academy Lab expiram em poucas horas**, inclusive no meio de uma mesma sessão de trabalho longa (já aconteceu). Sempre confirmar com `aws sts get-caller-identity` antes de assumir que dão pra usar, e lembrar que a conta inteira pode ter rotacionado desde a última sessão (ver `docs/sessoes/2026-08-29-...md` para o precedente).
