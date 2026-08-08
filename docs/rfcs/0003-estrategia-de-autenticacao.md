# RFC-0003: Estratégia de autenticação

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-04-21 |

## Contexto

O sistema tem dois perfis de acesso bem distintos: um **usuário administrador** da oficina, que opera todos os CRUDs e o fluxo completo de OS, e o **cliente da oficina**, que só precisa acompanhar o andamento da sua própria OS e aprovar/recusar um orçamento — sem nunca ter uma conta ou senha no sistema. Além disso, a API roda com múltiplas réplicas atrás de um `Deployment` escalado por HPA (2 a 5 pods), o que torna qualquer estratégia baseada em sessão guardada em memória do processo inviável sem um store compartilhado adicional.

## Alternativas consideradas

- **Sessão em cookie + store compartilhado (Redis)**: atenderia o admin, mas exigiria um componente de infraestrutura extra só para autenticação, sem necessidade real no escopo do MVP; também não resolve o caso do cliente, que não tem login.
- **OAuth2 com Identity Provider externo**: over-engineering para um único ator administrativo local (`admin`/`Admin@123` como default); adequado para múltiplos clientes/parceiros externos, não para o escopo atual.
- **API key estática**: mais simples que JWT, mas sem expiração nativa e sem padrão de claims; problemática para os fluxos públicos, que precisam de um token de uso único, não uma chave reutilizável.
- **JWT stateless para o admin + token público de uso único para o cliente**: escolhida.

## Decisão

Adotar uma estratégia de autenticação **por perfil de acesso**, sem sessão de servidor:

1. **Admin — JWT** (`POST /auth/token`): login usuário/senha emite um token assinado, enviado como `Authorization: Bearer` nos endpoints administrativos (`app/auth`, validado em `app/shared/security.py`). Stateless por natureza — qualquer réplica da API valida o token sem precisar consultar um store central, o que é o encaixe natural para uma API horizontalmente escalada pelo HPA atrás do Load Balancer.
2. **Cliente — consulta pública por documento**: `GET /service-orders/{id}/tracking` autentica apenas conferindo que o `document_number` informado bate com o CPF/CNPJ do cliente dono da OS. Não exige token, porque é uma consulta de leitura de baixo risco e o cliente nunca teve credenciais.
3. **Cliente — decisão de orçamento por token de uso único**: `POST /service-orders/{id}/quote-response` usa um token aleatório gerado no envio do orçamento (`send-quote`) e enviado por e-mail, vinculado àquela OS e **invalidado após a primeira aprovação ou recusa**. Não é um JWT — é descartável por definição, o que um JWT com expiração longa não garantiria sem uma lista de revogação.

## Consequências

- Nenhum dos três mecanismos exige estado de sessão compartilhado entre réplicas, o que mantém a API "stateless" e compatível com o HPA sem infraestrutura adicional (Redis, sticky sessions).
- O JWT do admin depende de uma única credencial (`admin`/`Admin@123` local, `ADMIN_PASSWORD` em produção); não há hoje múltiplos usuários administrativos nem RBAC — se isso vier a ser necessário, exigirá uma nova RFC.
- O token de aprovação pública depende do e-mail chegar ao cliente (`SMTP_ENABLED=true`); se o e-mail falhar, o cliente não tem como aprovar o orçamento por outro canal.
- CPF/CNPJ, placa e e-mail têm validação de entrada (`app/shared/validators.py`), mitigando parte do risco de a consulta pública por documento ser usada para enumeração de dados.
