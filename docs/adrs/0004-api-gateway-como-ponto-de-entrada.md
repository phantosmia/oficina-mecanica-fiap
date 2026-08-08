# ADR-0004: API Gateway como ponto único de entrada e autorização

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-08-08 |

## Contexto

Até a Fase 2, a comunicação externa com a API era exposta diretamente pelo Load Balancer/Ingress do EKS até o `Deployment` da aplicação, sem camada intermediária de gateway (ver [ADR-0001](0001-padrao-de-comunicacao-sincrono.md)). A Fase 3 exige centralizar o controle de acesso e o roteamento **antes** que a requisição alcance a aplicação, protegendo rotas sensíveis com autenticação via CPF e delegando a validação/emissão de JWT a um componente serverless dedicado ([RFC-0004](../rfcs/0004-escolha-do-api-gateway.md) escolheu o AWS API Gateway + AWS Lambda para esse papel).

## Decisão

Introduzir o **AWS API Gateway** como ponto único de entrada para as rotas protegidas por CPF, posicionado na frente do cluster EKS:

1. O cliente chama uma rota protegida através do API Gateway, nunca diretamente o Load Balancer do cluster.
2. A rota de autenticação (`/auth/cpf` ou equivalente) é roteada pelo Gateway para a **AWS Lambda**, que valida o CPF, consulta a existência/status do cliente no banco e devolve um JWT.
3. As demais rotas sensíveis passam por um **Lambda Authorizer** (ou mecanismo de validação equivalente do próprio Gateway) que confere o JWT antes de encaminhar (proxy) a requisição para o `Service`/`Ingress` do cluster EKS.
4. A aplicação FastAPI no EKS **continua validando o JWT internamente** (`app/shared/security.py`), como defesa em profundidade — não confia apenas na validação feita na borda pelo API Gateway.

## Alternativas consideradas

- **Manter o Load Balancer/Ingress como único ponto de entrada**, validando o JWT só dentro da aplicação (situação da Fase 2): não atende ao requisito explícito da Fase 3 de existir um API Gateway como componente dedicado de controle e roteamento.
- **Gateway como Ingress Controller dentro do próprio cluster** (Kong/Traefik): mantém tudo dentro do EKS, mas contraria a escolha do RFC-0004 pelo AWS API Gateway gerenciado e ainda exigiria hospedar e escalar esse componente como parte da infraestrutura Kubernetes.
- **Autenticação via CPF resolvida dentro da própria aplicação FastAPI**, sem Lambda: mais simples, mas não atende ao requisito de a validação de CPF e emissão de JWT ocorrerem em uma Function Serverless dedicada, fora do cluster.

## Consequências

- Toda rota protegida por CPF passa a ter um salto adicional gerenciado pela AWS (API Gateway → Lambda Authorizer) antes de chegar ao EKS — latência extra em troca de centralizar o controle de acesso fora da aplicação.
- A [estratégia de autenticação (RFC-0003)](../rfcs/0003-estrategia-de-autenticacao.md) passa a ter **três mecanismos coexistindo**, um por ator: JWT de admin via `POST /auth/token` (login usuário/senha), token público de uso único para aprovação de orçamento, e agora JWT de cliente emitido pela Lambda a partir do CPF, validado na borda pelo API Gateway. A aplicação precisa continuar aceitando e diferenciando esses formatos por tipo de rota.
- A disponibilidade da autenticação de clientes passa a depender de dois serviços gerenciados adicionais fora do EKS (API Gateway e Lambda); isso precisa entrar no escopo de latência, healthcheck e alertas exigido pelo monitoramento da Fase 3, não só as métricas do cluster.
- Se o API Gateway ou a Lambda ficarem indisponíveis, as rotas protegidas por CPF ficam inacessíveis mesmo com o cluster EKS saudável — um novo ponto de falha que não existia quando o Load Balancer apontava direto para a aplicação.
