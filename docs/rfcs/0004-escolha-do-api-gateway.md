# RFC-0004: Escolha da solução de API Gateway

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-08-08 |

## Contexto

A Fase 3 do Tech Challenge exige introduzir um **API Gateway** para controle e roteamento das rotas da aplicação, protegendo rotas sensíveis com **autenticação via CPF**. Essa autenticação precisa ser resolvida por uma **Function Serverless** dedicada, responsável por validar o CPF, consultar a existência e o status do cliente na base de dados e emitir um JWT para consumo das APIs protegidas. O enunciado cita como exemplos de gateway o AWS API Gateway, Kong ou Traefik, com liberdade de escolha de nuvem.

O [RFC-0001](0001-escolha-da-nuvem.md) já havia fixado a AWS como provedor de nuvem do projeto (EKS, RDS, ECR, Secrets Manager, backend Terraform em S3+DynamoDB), com pipelines de CI/CD e papéis IAM/OIDC já desenhados em torno desse provedor.

## Alternativas consideradas

- **Kong** (self-hosted, rodando no próprio cluster): oferece controle total e um ecossistema rico de plugins, mas exigiria operar mais um componente com estado dentro do EKS (deploy, scaling, upgrades e alta disponibilidade do próprio gateway) — o oposto do direcionamento da Fase 3 de adotar **soluções serverless** sempre que possível.
- **Traefik**: já é comumente usado como Ingress Controller Kubernetes e poderia assumir o papel de gateway dentro do cluster, mas não tem integração nativa com Lambda; a validação de JWT contra a Function Serverless exigiria middleware customizado, além de continuar sendo um componente do cluster para escalar e manter.
- **AWS API Gateway**: escolhido. É um serviço gerenciado (sem componente próprio para operar ou escalar), com integração nativa a **AWS Lambda** — tanto para invocar a function de autenticação via CPF quanto para validar o JWT em rotas protegidas via **Lambda Authorizer** — e se encaixa na infraestrutura AWS já decidida no RFC-0001, sem introduzir um segundo fornecedor ou ferramenta a administrar.

## Decisão

Adotar o **AWS API Gateway** como camada de entrada e roteamento das rotas protegidas por CPF, integrado a uma **AWS Lambda** responsável por:

1. Validar o CPF informado pelo cliente.
2. Consultar a existência e o status do cliente na base de dados.
3. Gerar e devolver um JWT válido para consumo das APIs protegidas.

As demais rotas administrativas continuam expostas pela aplicação principal no EKS, conforme decidido em [ADR-0004](../adrs/0004-api-gateway-como-ponto-de-entrada.md), que detalha como o Gateway se posiciona na frente do cluster.

## Consequências

- Aprofunda o *lock-in* com a AWS já assumido no RFC-0001, sem reduzir uma portabilidade que o projeto já não tinha.
- Elimina a necessidade de operar um gateway dentro do cluster Kubernetes (Kong/Traefik): um componente gerenciado a menos para escalar, atualizar e monitorar.
- A autenticação por CPF passa a depender da disponibilidade de dois serviços gerenciados adicionais fora do EKS (API Gateway e Lambda); uma falha nesses serviços impede a emissão de JWT mesmo que o cluster esteja saudável — precisa entrar no escopo de monitoramento exigido pela Fase 3.
- A Function Serverless (Lambda) exige um repositório próprio com CI/CD dedicado, conforme a estrutura de repositórios exigida pela Fase 3 (Lambda, infraestrutura Kubernetes, infraestrutura de banco gerenciado e aplicação principal em repositórios separados).
