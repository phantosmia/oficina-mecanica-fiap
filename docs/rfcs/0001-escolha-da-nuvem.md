# RFC-0001: Escolha da nuvem (AWS)

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-07-03 |

## Contexto

O Tech Challenge exige provisionar a infraestrutura via IaC, publicar a API em um cluster Kubernetes gerenciado e demonstrar escalabilidade automática e pipeline de CI/CD até um ambiente real. Além do requisito técnico, o curso disponibiliza laboratórios **AWS Academy** com créditos e papéis (roles) pré-criados, mas com restrições típicas de ambiente educacional: sem permissão para criar roles IAM arbitrárias, sem OIDC customizado, sessões de credenciais temporárias.

## Alternativas consideradas

- **AWS EKS**: provedor com laboratório já disponibilizado pela FIAP (AWS Academy), ecossistema completo (EKS, ECR, RDS, Secrets Manager, S3+DynamoDB para state do Terraform) cobrindo toda a stack necessária sem sair do provedor.
- **GCP GKE / Azure AKS**: também atenderiam o requisito de Kubernetes gerenciado, mas exigiriam conta paga própria (sem laboratório educacional equivalente fornecido pelo curso) e módulos Terraform novos, sem ganho relevante sobre a opção já disponível.
- **Kubernetes self-hosted (kubeadm/on-prem)**: descartado por custo operacional de manter o control plane e por não ser o que o desafio pretende avaliar (uso de serviços gerenciados de nuvem).

## Decisão

Adotar **AWS** como provedor de nuvem, com **EKS** para o cluster Kubernetes, **RDS** para o PostgreSQL de produção, **ECR** para as imagens Docker, **Secrets Manager** para segredos e **S3 + DynamoDB** como backend remoto do Terraform (`infra/backend`).

Para conciliar o requisito de uma arquitetura "de produção real" com as restrições do laboratório educacional, o projeto implementa **dois modos de deploy** no mesmo Terraform/pipeline (ver `docs/kubernetes-aws.md` e `.github/workflows/deploy-aws.yml`):

- `aws`: modo de conta própria, com autenticação via GitHub OIDC, IRSA, External Secrets Operator e AWS Load Balancer Controller.
- `aws-academy`: modo compatível com o AWS Academy Lab, reaproveitando roles pré-criadas do laboratório e usando credenciais de sessão temporárias, com OIDC/IRSA/ALB Controller/External Secrets Operator desabilitados.

## Consequências

- A infraestrutura fica acoplada a serviços proprietários da AWS (Secrets Manager, IRSA, ALB Controller); migrar de nuvem exigiria reescrever módulos Terraform e parte dos manifests Kubernetes.
- Manter dois modos de deploy (`aws` e `aws-academy`) aumenta a complexidade do workflow e do Terraform (várias condicionais), mas foi o que permitiu gravar a demonstração e rodar a infraestrutura real dentro das restrições do laboratório da FIAP.
- Caso o projeto evolua para uma conta AWS própria em definitivo, o modo `aws-academy` e suas condicionais podem ser removidos, simplificando o pipeline.
