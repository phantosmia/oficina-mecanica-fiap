# ADR-0006: ALB interno + VPC Link como único ponto de entrada público

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-08-15 |

## Contexto

A [ADR-0004](0004-api-gateway-como-ponto-de-entrada.md) decidiu que o AWS API Gateway seria o "ponto único de entrada" das rotas protegidas por CPF, com a aplicação FastAPI no EKS continuando a validar o JWT internamente "como defesa em profundidade — não confia apenas na validação feita na borda pelo API Gateway". Essa frase pressupõe que a borda (o Gateway) é, de fato, atravessada — mas a implementação original do Ingress (`k8s/overlays/aws/ingress.yaml`) usa `alb.ingress.kubernetes.io/scheme: internet-facing`, ou seja, o ALB da aplicação principal tem um DNS público e é alcançável diretamente pela internet, **sem** passar pelo API Gateway.

Na prática, isso anula a proteção: qualquer rota "protegida" pelo Lambda Authorizer (repositório `oficina-mecanica-lambda-auth`) podia ser acessada diretamente no ALB, ignorando o Gateway e o Authorizer por completo. O "ponto único de entrada" da ADR-0004 nunca foi de fato único.

## Decisão

1. O ALB passa a ser **interno** (`alb.ingress.kubernetes.io/scheme: internal`, `k8s/overlays/aws/ingress.yaml`) — sem IP/DNS público, alcançável apenas de dentro da VPC do cluster EKS.
2. O AWS API Gateway (`oficina-mecanica-lambda-auth`) alcança esse ALB interno via **VPC Link** (`aws_apigatewayv2_vpc_link`, com ENIs nas subnets privadas do cluster, lidas via `terraform_remote_state` de `oficina-mecanica-infra-kubernetes` — uma nova dependência de state que esse repositório passa a ter).
3. Duas rotas convivem sobre a mesma integração privada:
   - `ANY /{proxy+}`, **sem** o Lambda Authorizer — para tudo que já funcionava antes (login e rotas administrativas, protegidas pelo próprio JWT de admin da aplicação; o link de aprovação de orçamento por e-mail, que usa um token de uso único, não JWT; tracking sem token; health checks). Essas rotas continuam com exatamente as mesmas regras de acesso de antes — só que agora atravessando o Gateway em vez do ALB direto.
   - `ANY /api/{proxy+}`, **com** o Lambda Authorizer (`jwt_client`) — o caminho que de fato aplica a proteção via CPF na borda, para quem chama explicitamente por ele (ex.: tracking de OS com `Authorization: Bearer`). `/api/*` vence `/*` no roteamento do HTTP API por ser mais específico, então as duas rotas não conflitam.
4. `PUBLIC_BASE_URL` (usado para montar o link de aprovação de orçamento por e-mail, `app/shared/email.py`) passa a apontar para a raiz deste API Gateway, não mais para o ALB — que deixou de ter endereço público.

## Alternativas consideradas

- **Manter o ALB internet-facing, restringindo seu security group a uma origem específica** (ex.: só o CIDR da VPC): mais simples de implementar (sem VPC Link, sem custo adicional), mas é uma garantia mais frágil — depende de manter aquela regra de security group correta ao longo do tempo, e o ALB continuaria tecnicamente exposto (com IP público) mesmo que hoje bloqueado. Descartada em favor de uma garantia de rede mais forte (sem rota pública nenhuma).
- **Forçar todo o tráfego pela rota `/api/*` com o `jwt_client` authorizer**: inviável — o `jwt_client` authorizer só entende tokens de cliente (`type: "client"`); um token de admin (`sub` = username, sem essa claim) seria rejeitado, tornando o login administrativo impossível (dependência circular: para logar como admin, seria preciso já ter um JWT de cliente). Por isso a rota geral (`/{proxy+}`) precisa existir sem esse authorizer.
- **Duas Ingresses/ALBs separados** (um interno para o Gateway, outro público só para os fluxos genuinamente públicos): resolveria o problema sem VPC Link, mas duplica a infraestrutura do Load Balancer só para replicar o roteamento que o próprio API Gateway já faz nativamente com duas rotas.

## Consequências

- `oficina-mecanica-lambda-auth` ganha uma **terceira** dependência de `terraform_remote_state` (agora lê banco de dados, aplicação principal **e** infraestrutura Kubernetes), e um novo recurso com custo recorrente (VPC Link, cobrado por hora + dados processados).
- `eks_alb_listener_arn` é outro valor que não é output de nenhum Terraform da Fase 3 (assim como o hostname do Ingress já era) — precisa ser obtido manualmente via AWS CLI depois que o Ingress existir, documentado no README de `oficina-mecanica-lambda-auth`.
- `PUBLIC_BASE_URL` também passa a depender de uma cópia manual do output `public_base_url` para o ConfigMap da aplicação principal (`k8s/overlays/aws/patch-configmap-rds.yaml`) — mais um valor sem automação entre repositórios, pelo mesmo motivo dos anteriores (o ALB só existe depois que o cluster já está no ar).
- A proteção via CPF passa a ser real na rota `/api/*`: não há mais como contorná-la batendo direto no ALB, porque o ALB não tem mais endereço público. As demais rotas (`/{proxy+}`) continuam com o mesmo nível de proteção que já tinham antes desta ADR (JWT de admin, token de uso único, ou nenhuma, conforme o caso) — esta ADR resolve o contorno da proteção por CPF, não redesenha a proteção das demais rotas.
