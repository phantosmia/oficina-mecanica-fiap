# Arquitetura

## Justificativa do banco de dados

A primeira versão do MVP foi implementada com **SQLite** por simplicidade de setup local. Para esta evolução, o banco foi migrado para **PostgreSQL**, motivado por:

- **Modelo cliente-servidor real**: o PostgreSQL é executado em um processo dedicado (no Compose, no CI e em produção), o que se aproxima do cenário operacional final e elimina particularidades do SQLite (banco em arquivo, locking em escrita concorrente, ausência de tipos ricos).
- **Concorrência e integridade**: oficinas mecânicas têm múltiplos usuários e fluxos concorrentes (criação de OS, baixa de estoque, atualização de status). O PostgreSQL oferece MVCC, transações reais e checagem de constraints mais robusta, incluindo `ON DELETE CASCADE` e `ON DELETE RESTRICT` honrados nativamente.
- **Aderência ao ambiente de execução**: como toda a stack já roda em containers, manter o banco como um serviço separado deixa o ambiente local idêntico ao de CI e ao de produção.
- **Evolução prevista**: a justificativa anterior já apontava o PostgreSQL como destino natural; esta entrega concretiza essa migração sem alterar a Clean Architecture. Domínio, casos de uso e controllers permanecem intactos.
- **CI determinístico**: o pipeline usa Testcontainers para provisionar um PostgreSQL `postgres:16-alpine` efêmero durante a suíte de testes.

## Clean Architecture

O projeto adota **Clean Architecture** organizada por **contextos de domínio**. Cada contexto é independente e possui suas próprias quatro camadas internas, com dependências fluindo sempre de fora para dentro.

### Regra de dependência

```text
controller  ->  application  ->  domain
    |               |
adapters    ->  domain (implements interface)
```

- **Domínio** não conhece nada externo, como FastAPI, SQLAlchemy ou Pydantic.
- **Application** depende apenas de interfaces abstratas (`IXxxRepository`).
- **Adapters** implementam as interfaces do domínio.
- **Controller** injeta as implementações concretas via `Depends` do FastAPI.

## Diagrama de componentes

O diagrama abaixo, na notação **C4 (nível de componentes)**, representa os principais componentes da aplicação e suas dependências externas. Os atores (`Usuário Administrador` e `Cliente da Oficina`) aparecem como `Person`, a aplicação é um limite (`boundary`) com dois sub-limites internos (`Entrada HTTP` e `Contextos de Domínio`), e os serviços externos (`PostgreSQL`, `SMTP Provider` e `New Relic`) ficam fora da aplicação.

![Diagrama de componentes C4 da aplicação Oficina Mecânica](imgs/diagramac4_componentes_oficina_mecanica_fiap.drawio.png)

### Leitura do diagrama

- **Atores**: o `Usuário Administrador` e o `Cliente da Oficina` fazem requisições HTTPS para a aplicação; o primeiro gerencia clientes, veículos, catálogo, peças e ordens, o segundo acompanha e aprova ordens pelos endpoints públicos.
- **Entrada HTTP**: a `FastAPI Application` roteia chamadas autenticadas para o `Auth / Login JWT`, que cuida da autenticação e emissão de token e encaminha a requisição para o contexto de domínio correspondente. Os `Endpoints públicos` expõem ações sem autenticação e usam diretamente o contexto `Service Orders` (rastreio de ordem e aprovação/recusa pública de orçamento).
- **Contextos de domínio**: `System`, `Clients`, `Veículos`, `Service Catalog`, `Parts` e `Service Orders` representam os componentes funcionais da aplicação. `Service Orders` é o componente central do fluxo de negócio — orquestra diagnóstico, orçamento, aprovação, recusa, baixa de estoque e entrega — e é o único contexto acessado pelas duas vias de entrada: autenticada (`Auth / Login JWT`, operações administrativas) e pública (`Endpoints públicos`, tracking e aprovação do cliente).
- **Shared**: não é um domínio de negócio; oferece recursos transversais (security/JWT, validators, error mapping, DB session, email port e telemetry) consumidos pelos demais componentes.
- **Serviços externos**: o `Banco de Dados da Oficina` (PostgreSQL) é lido/gravado pelo `Shared` (SQLAlchemy), o `SMTP Provider` recebe os envios de e-mail do `Shared`, e o `New Relic` recebe dados de duas origens distintas — a `FastAPI Application` reporta latência/erros/traces por rota via auto-instrumentação (agente APM), e o `Shared` registra eventos customizados de domínio (`ServiceOrderCreated`, `ServiceOrderStatusChanged`) usados pelos dashboards.

## Diagrama de componentes internos dos contextos

Cada contexto de domínio segue a mesma organização interna. O diagrama abaixo detalha como os componentes internos se relacionam dentro de um contexto, mantendo a regra de dependência da Clean Architecture.

```mermaid
flowchart LR
    Controller[Controller / FastAPI Router]
    Schemas[Schemas / Pydantic]
    UseCases[Application / Use Cases]
    Domain[Domain / Entities + Rules]
    RepoInterface[Domain Repository Interface]
    Repository[Adapter / SQLAlchemy Repository]
    Presenter[Adapter / Presenter]
    Database[(PostgreSQL)]

    Controller --> Schemas
    Controller --> UseCases
    UseCases --> Domain
    UseCases --> RepoInterface
    Repository --> RepoInterface
    Repository --> Database
    Presenter --> Schemas
    Controller --> Presenter
```

### Leitura do diagrama interno

- `Controller` recebe a requisição HTTP, valida dependências e chama casos de uso.
- `Schemas` definem os contratos Pydantic de entrada e saída.
- `Application / Use Cases` orquestra regras do domínio e depende de interfaces, não de implementações concretas.
- `Domain` concentra entidades, objetos de valor e regras puras de negócio.
- `Domain Repository Interface` define o contrato exigido pelo domínio.
- `Adapter / SQLAlchemy Repository` implementa esse contrato usando persistência em PostgreSQL.
- `Adapter / Presenter` converte entidades de domínio para schemas de resposta.

## Diagrama da infraestrutura provisionada

O diagrama abaixo representa os principais recursos provisionados na AWS e o fluxo de tráfego em runtime, agrupados por **função** (rede/cluster, aplicação, banco, observabilidade) em vez de por repositório Terraform — a divisão em 4 repositórios e a ordem de apply entre eles já têm um diagrama dedicado, [logo abaixo](#diagrama-de-dependência-entre-os-repositórios-terraform).

![Diagrama da infraestrutura provisionada na AWS](imgs/diagrama_de_infraestrutura_oficina_mecanica_fiap.drawio.png)

### Leitura do diagrama de infraestrutura

- **Duas VPCs**, não uma só: a **VPC do cluster** (`oficina-mecanica-infra-kubernetes` — EKS Cluster e o `Load Balancer Interno`) e a **VPC do banco** (`oficina-mecanica-infra-banco-dados` — RDS e a Lambda `Authenticate`), conectadas por **VPC Peering** (`aws_vpc_peering_connection.eks_to_database`, criado no repositório do cluster) — é por esse peering que `API Deployment/Service` e `Alembic Migration Job` alcançam o RDS, que não é publicamente acessível.
- **Entrada (ADR-0004/ADR-0006)**: o `Usuário Final` faz requisições HTTPS para o `Amazon API Gateway` — um serviço gerenciado, fora de qualquer VPC. Duas rotas convivem sobre o mesmo `Load Balancer Interno` (sem IP público desde o ADR-0006):
  - **Rota pública** (`/{proxy+}`, sem Lambda Authorizer): vai direto via **VPC Link** até o `Load Balancer Interno` — cobre login admin, tracking sem token e aprovação de orçamento por token de uso único.
  - **Rota autenticada** (`/api/*`): primeiro invoca a `Lambda authorize` (o Lambda Authorizer), que só valida a assinatura do JWT — sem consultar o banco nem depender de nenhuma VPC (ADR-0005, evita o custo de ENI numa função chamada a cada requisição). Se aprovado, a requisição segue pelo mesmo VPC Link até o mesmo `Load Balancer Interno` — o Lambda nunca atua como proxy da requisição.
- **Emissão de token** (rota separada, ex. `/auth/cpf`): o `Amazon API Gateway` invoca a `Lambda Authenticate`, que roda **dentro da VPC do banco** (ADR-0005) porque precisa consultar o RDS diretamente para validar o CPF antes de emitir o JWT.
- O `Load Balancer Interno` encaminha para o `API Deployment / Service` dentro do `EKS Cluster` (subnets privadas). Também no cluster: `Alembic Migration Job`, os add-ons de plataforma (`HPA + metrics-server`) e o `nri-bundle` (New Relic Kubernetes integration, ADR-0007).
- O `AWS Secrets Manager` guarda as credenciais da API, sincronizadas para o cluster via IRSA/External Secrets Operator.
- **New Relic**: hoje só **2 dos 4 pontos do ADR-0007 estão ativos** — o `API Deployment / Service` reporta latência/erros via agente APM, e o `nri-bundle` envia métricas de infraestrutura do cluster; ambos aparecem como uma única seta "Envia dados de telemetria" no diagrama. A instrumentação da Lambda (layer) e a Cloud Integration para RDS/API Gateway existem no código dos respectivos repositórios mas não estão configuradas em nenhum ambiente hoje — ver débito técnico correspondente em `docs/proximos-passos.md`.
- **Provisionamento e Pipeline**: o `Desenvolvedor` e o `GitHub Actions` publicam a imagem no `Amazon ECR` (Docker push) e executam `terraform apply` contra o backend remoto (`Terraform State S3` + `DynamoDB` para lock) — compartilhado pelos 4 repositórios, cada um com sua própria `key` de state.
- Os recursos de **Identidade e Acesso** (EKS OIDC + IRSA, GitHub OIDC + ECR Role) ficam no repositório do cluster.
- Observação: no modo **AWS Academy**, a pipeline usa secrets (chaves de sessão) para acessar a conta AWS, e os recursos de OIDC/IRSA ficam desabilitados.

## Diagrama de dependência entre os repositórios Terraform

A leitura via `terraform_remote_state` (ver seção anterior) cria uma **ordem de apply obrigatória** entre os quatro repositórios: cada seta abaixo é uma leitura de state, não uma chamada de API — se o state do lado de origem da seta ainda não existir no ambiente (`dev`, `homologacao` ou `producao`) sendo lido, o `plan`/`apply` do lado de destino falha.

```mermaid
flowchart LR
    DB["oficina-mecanica-infra-banco-dados<br/><small>database/&lt;env&gt;/terraform.tfstate</small>"]
    K8S["oficina-mecanica-infra-kubernetes<br/><small>kubernetes/&lt;env&gt;/terraform.tfstate</small>"]
    APP["oficina-mecanica-fiap: infra/aws<br/><small>aws/&lt;env&gt;/terraform.tfstate</small>"]
    LAMBDA["oficina-mecanica-lambda-auth<br/><small>lambda/&lt;env&gt;/terraform.tfstate</small>"]

    DB -- "rds_secret_arn" --> K8S
    DB -- "rds_endpoint, rds_password" --> APP
    K8S -- "cluster_name, ecr_repository_url,<br/>oidc_provider_arn" --> APP
    DB -- "vpc_id, private_subnet_ids,<br/>rds_secret_arn" --> LAMBDA
    APP -- "app_secret_arn<br/>(JWT_SECRET_KEY)" --> LAMBDA
    K8S -- "vpc_id, private_subnet_ids<br/>(VPC Link, ADR-0006)" --> LAMBDA
```

Ordem de apply, portanto: **banco de dados → cluster Kubernetes → aplicação principal → Lambda de autenticação**. Isso vale tanto para uma aplicação manual local quanto para os workflows de CI/CD de cada repositório — nenhum deles provisiona os outros automaticamente, então rodar o `terraform apply` do repositório errado primeiro (ou apontar `kubernetes_state_key`/`database_state_key`/`app_state_key`/`infra_environment` para um ambiente que nunca foi aplicado) leva a essa falha. A Lambda depende da aplicação principal porque lê o `JWT_SECRET_KEY` do secret que `infra/aws` cria (ver [ADR-0005](adrs/0005-lambda-auth-na-vpc-do-banco.md)) **e** do cluster Kubernetes diretamente, para o VPC Link alcançar o ALB interno da aplicação principal (ver [ADR-0006](adrs/0006-alb-interno-vpc-link.md)) — por isso ela é sempre a última da cadeia.

> **O que acontece se você rodar fora de ordem:** o `terraform plan` (ou `apply`) do repositório que lê o state ausente falha imediatamente, com:
> ```
> Error: Unable to find remote state
> No stored state was found for the given workspace in the given backend.
> ```
> Não há execução parcial nem valores vazios silenciosos — o Terraform recusa a rodar o `plan` sem conseguir resolver a leitura. A correção é sempre a mesma: aplique primeiro o repositório de origem da seta, no mesmo ambiente (`dev`/`homologacao`/`producao`) que o repositório dependente está tentando ler.

## Diagrama do fluxo de deploy

O diagrama abaixo detalha o fluxo executado pelo workflow `deploy-aws.yml` (GitHub Actions), desde a autenticação na AWS até a validação final do rollout no EKS. Os losangos representam pontos condicionais controlados pelo modo de deploy (`deployment_mode`, `terraform_apply`, `build_image`) — no disparo manual (`workflow_dispatch`) esses valores vêm dos inputs; no disparo automático (push em `homologacao`/`producao`) são resolvidos automaticamente (`aws-academy`, `terraform_apply`/`build_image` sempre `true`).

```mermaid
flowchart TB
    Start(["push homologacao/producao<br/>ou workflow_dispatch"]) --> Auth{deployment_mode}
    Auth -->|aws| OIDC["Autentica via GitHub OIDC<br/> assume role AWS"]
    Auth -->|aws-academy| Keys["Autentica via chaves<br/> de sessão AWS Academy"]

    OIDC --> Setup{{"Setup Terraform<br/>+ kubectl"}}
    Keys --> Setup

    Setup --> Backend{{"Preparar backend<br/> remoto (backend.hcl)"}}
    Backend --> Tfvars{{"Gerar tfvars<br/> sensíveis"}}
    Tfvars --> Init["terraform init"]
    Init --> Plan["terraform plan<br/> (lê kubernetes + database<br/> via terraform_remote_state)"]

    Plan --> RemoteStateCheck{"State remoto dos outros<br/> repos existe no ambiente?"}
    RemoteStateCheck -->|não| Fail(["Falha imediata:<br/> remote state ausente"])
    RemoteStateCheck -->|sim| ApplyCheck{"terraform_apply?"}
    ApplyCheck -->|true| Apply["terraform apply<br/> -auto-approve"]
    ApplyCheck -->|false| Outputs["Ler outputs<br/> do Terraform"]
    Apply --> Outputs

    Outputs --> BuildCheck{"build_image?"}
    BuildCheck -->|true| Build["Login ECR +<br/> docker build/push"]
    BuildCheck -->|false| Kube["Configurar kubeconfig<br/> do EKS"]
    Build --> Kube

    Kube --> Overlay{{"Preparar overlay<br/> Kustomize por modo"}}
    Overlay --> Validate["kubectl kustomize<br/> (valida manifests)"]
    Validate --> ApplyK8s["kubectl apply -k<br/> (recria Migration Job)"]

    ApplyK8s --> WaitMig[["Aguardar Migration Job<br/> (condition=complete)"]]
    WaitMig --> WaitRollout[["Aguardar rollout do<br/> Deployment da API"]]
    WaitRollout --> Summary["Resumo do deploy"]
    Summary --> End([Deploy concluído])
```

### Leitura do fluxo de deploy

- **Formas do diagrama**: retângulos são passos de execução; hexágonos são passos de preparação; losangos são decisões condicionais; e os retângulos de borda dupla representam os passos de **aguardar execução** (Migration Job e rollout). O texto completo de cada condição está detalhado nos tópicos abaixo, para manter os nós do diagrama curtos e legíveis em qualquer visualizador de Markdown.
- **Autenticação**: no modo `aws` a pipeline assume uma role via GitHub OIDC; no modo `aws-academy` usa chaves de sessão temporárias.
- **Terraform**: sempre roda `init` e `plan` (só o Terraform de `infra/aws`: secret da API + IRSA); o `apply` só ocorre quando o input `terraform_apply=true`. Já durante o `plan`, o Terraform lê automaticamente `cluster_name`, `ecr_repository_url`, `oidc_provider_arn`, `rds_endpoint` e `rds_password` via `terraform_remote_state` dos outros dois repositórios; os outputs resultantes (`app_secret_name`, `api_secrets_role_arn`, `cluster_name`, `ecr_repository_url`, `rds_endpoint`) alimentam os passos seguintes — não há mais variables do GitHub para esses valores.
- **Dependência entre repositórios**: se o `oficina-mecanica-infra-kubernetes` e o `oficina-mecanica-infra-banco-dados` ainda não tiverem sido aplicados no ambiente apontado pelo input `infra_environment` (default `dev`), o `terraform plan` deste passo falha imediatamente (`Unable to find remote state`) — ver o [diagrama de dependência entre os repositórios](#diagrama-de-dependência-entre-os-repositórios-terraform) acima. Rodar este workflow antes deles é o erro mais comum de "executei fora de ordem".
- **Imagem**: quando `build_image=true`, a pipeline faz login no ECR, builda e publica a imagem antes do deploy.
- **Kubernetes**: configura o `kubeconfig`, prepara o overlay Kustomize do modo escolhido, valida os manifests, recria o `Migration Job` e aplica tudo no EKS.
- **Sincronização**: aguarda o `Migration Job` completar e o rollout do `Deployment` da API estabilizar antes de emitir o resumo final.



```text
app/
├── shared/                  # Infraestrutura transversal
│   ├── models.py            # Modelos SQLAlchemy (ORM)
│   ├── database.py          # Engine, sessão e get_db()
│   ├── security.py          # JWT e autenticação
│   ├── validators.py        # Validações de CPF/CNPJ e placa
│   ├── exceptions.py        # Erros de domínio
│   ├── http_errors.py       # Mapeamento DomainError -> HTTPException
│   ├── email.py             # Porta IEmailNotifier + templates
│   └── smtp_notifier.py     # Adaptador SMTP concreto
│
├── auth/                    # Autenticação JWT
├── clients/                 # Gestão de clientes
├── vehicles/                # Gestão de veículos
├── service_catalog/         # Catálogo de serviços
├── parts/                   # Peças e insumos
├── service_orders/          # Ordens de serviço
└── system/                  # Healthcheck e status
```

Cada contexto segue a mesma estrutura interna:

```text
<contexto>/
├── domain/
│   ├── entity.py         # Entidades puras, sem ORM ou HTTP
│   ├── repository.py     # Interface ABC exigida pelo domínio
│   └── value_objects.py  # Status e regras de transição, quando aplicável
├── application/
│   └── use_cases.py      # Casos de uso
├── adapters/
│   ├── sqlalchemy_repository.py
│   └── presenter.py
├── controller.py
└── schemas.py
```

## Princípios aplicados

| Princípio | Como foi aplicado |
|---|---|
| Inversão de dependência | `application` depende de `IXxxRepository`; `adapters` implementa a interface; `controller` injeta a implementação concreta |
| Isolamento do domínio | Entidades são `dataclass` puras, sem import de FastAPI, SQLAlchemy ou Pydantic |
| Casos de uso independentes | `use_cases.py` lança apenas `DomainError`; a conversão para HTTP fica no `controller` |
| Substituibilidade | Repositórios concretos podem ser trocados por mocks nos testes sem alterar domínio ou casos de uso |

## Contextos

- `app/shared`: infraestrutura transversal, segurança, configuração e validações
- `app/auth`: autenticação JWT
- `app/clients`: gestão de clientes
- `app/vehicles`: gestão de veículos
- `app/service_catalog`: catálogo de serviços
- `app/parts`: peças e insumos
- `app/service_orders`: ordens de serviço e regras de negócio
- `app/system`: healthcheck e status da aplicação
