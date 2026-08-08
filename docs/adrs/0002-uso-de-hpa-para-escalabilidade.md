# ADR-0002: Uso de HPA para escalabilidade automática

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-07-04 |

## Contexto

O Tech Challenge exige demonstrar escalabilidade automática da aplicação sob carga real, tanto em Minikube quanto no EKS. A API FastAPI é stateless (ver [RFC-0003](../rfcs/0003-estrategia-de-autenticacao.md)), o que a torna elegível para escalar horizontalmente por réplicas de pod sem necessidade de afinidade de sessão.

## Decisão

Usar **HorizontalPodAutoscaler (`autoscaling/v2`)** (`k8s/base/hpa.yaml`) apontando para o `Deployment` da API, com:

- `minReplicas: 2`, `maxReplicas: 5`.
- Métricas de `Resource`: CPU (`averageUtilization: 70`) e memória (`averageUtilization: 75`).
- `behavior.scaleUp` agressivo: `stabilizationWindowSeconds: 0`, com política de até 100% de crescimento ou +2 pods a cada 15s (o que for maior).
- `behavior.scaleDown` conservador: `stabilizationWindowSeconds: 300`, reduzindo até 50% a cada 60s.

Isso exige o **metrics-server** como dependência de qualquer cluster onde a stack rode (addon do Minikube; add-on Terraform no EKS), pois é dele que o HPA lê CPU/memória.

## Alternativas consideradas

- **Vertical Pod Autoscaler (VPA)**: ajusta requests/limits de CPU/memória de um pod já existente, mas não cria novas réplicas — não atende ao requisito de escalabilidade horizontal nem à demonstração de múltiplos pods atendendo tráfego.
- **Cluster Autoscaler isolado (só nodes)**: escalaria os *nodes* do EKS conforme falta de capacidade, mas não decide sozinho quantos *pods* da API devem existir; sem o HPA, o número de réplicas do `Deployment` continuaria fixo.
- **Escala manual (`kubectl scale` sob demanda)**: descartada por não atender ao requisito de escalar automaticamente em resposta a carga.
- **HPA com `stabilizationWindowSeconds` e período de scale-up padrão (mais conservador)**: seria mais adequado a um cenário de produção real, mas a resposta ficaria lenta demais para os testes de carga (Locust) e a demonstração em vídeo — por isso o `behavior` foi ajustado especificamente para reagir em segundos (ver `docs/testes-carga-ci.md`).

## Consequências

- Todo cluster que rodar esta stack precisa do `metrics-server` disponível; sem ele, o HPA fica com `<unknown>` nas métricas e nunca escala.
- O mínimo de 2 réplicas fica sempre ativo, mesmo sem tráfego — custo/capacidade reservados permanentemente, não só sob demanda.
- O `scaleUp` agressivo (janela zero, +100%/15s) foi calibrado para demonstrações e testes de carga controlados (Locust); em um cenário de produção com picos de tráfego menos previsíveis, pode causar *thrashing* de réplicas e merece um `behavior` mais conservador — ajuste que fica registrado aqui como trabalho futuro, não como decisão pendente desta ADR.
- Escalar apenas a camada de API não escala o PostgreSQL (RDS) — ver [ADR-0003](0003-postgresql-gerenciado-rds.md); um pico de réplicas da API pode esbarrar em limite de conexões do banco antes de esbarrar em CPU/memória dos pods.
