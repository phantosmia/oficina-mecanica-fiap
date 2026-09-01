# Arquitetura

## Justificativa do banco de dados

A primeira versão do MVP foi implementada com **SQLite** por simplicidade de setup local. Para esta evolução, o banco foi migrado para **PostgreSQL**, motivado por:

- **Modelo cliente-servidor real**: o PostgreSQL é executado em um processo dedicado (no Compose, no CI e em produção), o que se aproxima do cenário operacional final e elimina particularidades do SQLite (banco em arquivo, locking em escrita concorrente, ausência de tipos ricos).
- **Concorrência e integridade**: oficinas mecânicas têm múltiplos usuários e fluxos concorrentes (criação de OS, baixa de estoque, atualização de status). O PostgreSQL oferece MVCC, transações reais e checagem de constraints mais robusta, incluindo `ON DELETE CASCADE` e `ON DELETE RESTRICT` honrados nativamente.
- **Aderência ao ambiente de execução**: como toda a stack já roda em containers, manter o banco como um serviço separado deixa o ambiente local idêntico ao de CI e ao de produção.
- **Evolução prevista**: a justificativa anterior já apontava o PostgreSQL como destino natural; esta entrega concretiza essa migração sem alterar a Clean Architecture. Domínio, casos de uso e controllers permanecem intactos.
- **CI determinístico**: o pipeline usa Testcontainers para provisionar um PostgreSQL `postgres:16-alpine` efêmero durante a suíte de testes.

## Diagrama Entidade-Relacionamento

O diagrama abaixo representa o schema do PostgreSQL (`app/shared/models.py`), gerenciado via Alembic.

```mermaid
erDiagram
    CLIENTS ||--o{ VEHICLES : possui
    CLIENTS ||--o{ SERVICE_ORDERS : solicita
    VEHICLES ||--o{ SERVICE_ORDERS : "é atendido em"
    SERVICE_ORDERS ||--o{ SERVICE_ORDER_SERVICES : inclui
    SERVICE_ORDERS ||--o{ SERVICE_ORDER_PARTS : inclui
    SERVICES_CATALOG ||--o{ SERVICE_ORDER_SERVICES : "referenciado por"
    PARTS ||--o{ SERVICE_ORDER_PARTS : "referenciado por"

    CLIENTS {
        int id PK
        string name
        string document_type
        string document_number UK
        string email
        string phone
        string status
    }
    VEHICLES {
        int id PK
        int client_id FK
        string brand
        string model
        int year
        string license_plate UK
    }
    SERVICES_CATALOG {
        int id PK
        string name
        string description
        float base_price
        int estimated_minutes
        bool active
    }
    PARTS {
        int id PK
        string name
        string sku UK
        string description
        float unit_price
        int stock_quantity
        int min_stock_level
    }
    SERVICE_ORDERS {
        int id PK
        int client_id FK
        int vehicle_id FK
        string status
        string problem_description
        string diagnosis_notes
        float labor_total
        float parts_total
        float quote_total
        string quote_token UK
        datetime quote_sent_at
        datetime approved_at
        datetime started_at
        datetime finished_at
        datetime delivered_at
    }
    SERVICE_ORDER_SERVICES {
        int id PK
        int service_order_id FK
        int service_id FK
        int quantity
        float unit_price
        float subtotal
    }
    SERVICE_ORDER_PARTS {
        int id PK
        int service_order_id FK
        int part_id FK
        int quantity
        float unit_price
        float subtotal
    }
```

### Leitura do diagrama ER

- **`clients` → `vehicles` → `service_orders`**: um cliente tem vários veículos e várias ordens de serviço; um veículo pode aparecer em várias ordens ao longo do tempo (revisões diferentes). As três relações são `ON DELETE CASCADE` — apagar um cliente apaga seus veículos e ordens (`app/shared/models.py`, `ForeignKey(..., ondelete="CASCADE")`).
- **`service_orders` → `service_order_services` / `service_order_parts`**: tabelas de associação (uma linha por item incluído na ordem), também `CASCADE` — apagar a ordem apaga seus itens.
- **`services_catalog` → `service_order_services`** e **`parts` → `service_order_parts`**: `ON DELETE RESTRICT`, de propósito o oposto do resto do schema — não é possível apagar um serviço do catálogo ou uma peça que já foi usada em alguma ordem, porque `unit_price`/`subtotal` são um **snapshot** do preço no momento da criação da ordem (auditoria do orçamento), não uma referência viva ao preço atual do catálogo/peça (ver `docs/regras-negocio.md`).
- `quote_token` é único e nulo até o orçamento ser enviado (`send-quote`) — é o token de uso único da aprovação pública por e-mail, invalidado (`quote_token` volta a `null`, não um flag "usado") assim que a ordem é aprovada ou recusada.
- Os campos `*_at` (`quote_sent_at`, `approved_at`, `started_at`, `finished_at`, `delivered_at`) marcam a entrada em cada status do fluxo (`recebida → em_diagnostico → aguardando_aprovacao → em_execucao → finalizada → entregue`) e alimentam tanto o cálculo de tempo médio de execução (`GetAverageExecutionTimeUseCase`) quanto os eventos customizados do New Relic (`app/shared/telemetry.py`).
- Não existe uma tabela de usuários/admin: o login administrativo (`POST /auth/token`) é validado contra `ADMIN_USERNAME`/`ADMIN_PASSWORD` (variáveis de ambiente, `app/shared/security.py`), não contra uma linha no banco.

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

## Diagrama de sequência

Três fluxos, cobrindo autenticação via CPF (emissão do token e validação em rota protegida) e abertura de ordem de serviço. Os nomes dos componentes seguem o [diagrama de infraestrutura](#diagrama-da-infraestrutura-provisionada) acima.

### Emissão do token (CPF)

```mermaid
sequenceDiagram
    actor Cliente
    participant GW as API Gateway
    participant LA as Lambda Authenticate
    participant DB as RDS PostgreSQL

    Cliente->>GW: POST /auth/cpf {cpf}
    GW->>LA: Invoca (fora de VPC; a execução roda numa ENI da VPC do banco)
    LA->>LA: Valida formato do CPF
    alt CPF inválido
        LA-->>GW: 400 {detail}
        GW-->>Cliente: 400 {detail}
    else CPF válido
        LA->>DB: SELECT clients WHERE document_number = ?
        DB-->>LA: cliente (ou nenhum)
        alt cliente inexistente ou inativo
            LA-->>GW: 404 "Cliente não encontrado ou inativo"
            GW-->>Cliente: 404
        else cliente ativo
            LA->>LA: Gera JWT (create_client_token)
            LA-->>GW: 200 {access_token, token_type}
            GW-->>Cliente: 200 {access_token, token_type}
        end
    end
```

Cliente inexistente e cliente inativo recebem a mesma resposta (404) de propósito — não revela a quem tenta autenticar se um CPF pertence a um cliente inativo ou simplesmente não existe (`docs/regras-negocio.md`).

### Validação do token numa rota protegida (`/api/*`)

```mermaid
sequenceDiagram
    actor Cliente
    participant GW as API Gateway
    participant AZ as Lambda authorize
    participant ALB as Load Balancer Interno
    participant API as FastAPI Application
    participant DB as RDS PostgreSQL

    Cliente->>GW: GET /api/service-orders/{id}/tracking<br/>Authorization: Bearer {token}
    GW->>AZ: Invoca (Lambda Authorizer)
    AZ->>AZ: Decodifica e valida a assinatura do JWT
    alt token ausente ou inválido
        AZ-->>GW: {isAuthorized: false}
        GW-->>Cliente: 403 Forbidden
    else token válido
        AZ-->>GW: {isAuthorized: true, context: {sub, type, client_id}}
        GW->>ALB: Encaminha via VPC Link
        ALB->>API: Encaminha
        API->>API: Valida o JWT novamente (defesa em profundidade, ADR-0004)
        API->>DB: SELECT service_orders WHERE id = ? (checa client_id/document_number)
        DB-->>API: dados da ordem
        API-->>ALB: 200 {tracking}
        ALB-->>GW: 200
        GW-->>Cliente: 200 {tracking}
    end
```

O `Lambda authorize` só decide `allow`/`deny` — quem entrega a requisição pro cluster é sempre o próprio API Gateway via VPC Link, nunca o Lambda (ver "Leitura do diagrama de infraestrutura" acima).

### Abertura de ordem de serviço (`POST /service-orders`, admin)

```mermaid
sequenceDiagram
    actor Admin as Usuário Administrador
    participant GW as API Gateway
    participant ALB as Load Balancer Interno
    participant API as FastAPI Application
    participant UC as CreateServiceOrderUseCase
    participant DB as RDS PostgreSQL
    participant NR as New Relic

    Admin->>GW: POST /service-orders<br/>Authorization: Bearer {JWT admin}<br/>{client, vehicle, problem_description, requested_services, requested_parts}
    GW->>ALB: Encaminha via VPC Link (rota pública — JWT de admin, não de cliente)
    ALB->>API: Encaminha
    API->>API: get_current_admin valida o JWT
    alt JWT inválido/ausente
        API-->>Admin: 401 Unauthorized
    else JWT válido
        API->>UC: execute(client_data, vehicle_data, ...)
        UC->>DB: upsert_client(document_number, ...)
        DB-->>UC: cliente (criado ou existente)
        UC->>DB: upsert_vehicle(client_id, plate, ...)
        DB-->>UC: veículo (criado ou existente)
        loop cada serviço solicitado
            UC->>DB: SELECT services_catalog WHERE id = ? AND active
            DB-->>UC: serviço (base_price) ou nenhum
        end
        loop cada peça solicitada
            UC->>DB: SELECT parts WHERE id = ?
            DB-->>UC: peça (unit_price, stock_quantity) ou nenhuma
        end
        alt serviço/peça não encontrada
            UC-->>API: NotFoundError
            API-->>Admin: 404
        else estoque insuficiente para alguma peça
            UC-->>API: InsufficientStockError
            API-->>Admin: 409
        else tudo válido
            UC->>UC: Calcula labor_total, parts_total, quote_total
            UC->>DB: INSERT service_orders (status=recebida) + itens
            DB-->>UC: ordem criada
            UC->>NR: record_service_order_created (evento customizado)
            UC-->>API: ServiceOrderEntity
            API-->>ALB: 201 Created {ServiceOrderRead}
            ALB-->>GW: 201
            GW-->>Admin: 201 {ServiceOrderRead}
        end
    end
```

`upsert_client`/`upsert_vehicle` criam ou reaproveitam o registro existente (busca por `document_number`/`license_plate`) — uma ordem de serviço não exige cadastro prévio manual do cliente/veículo. Os itens de serviço e peça são gravados com `unit_price`/`subtotal` **snapshotados** no momento da criação (ver "Leitura do diagrama ER" acima), não como referência viva ao preço atual do catálogo.

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
