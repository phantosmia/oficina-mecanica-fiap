"""Ordem de apply entre os 9 repositórios Terraform.

Gera docs/imgs/dependencia_terraform_fase4.png. Ver docs/diagramas/README.md.

O diagrama mostra só a sequência das etapas. Cada repositório também lê
outputs de etapas anteriores que não são a imediatamente anterior (banco e
kubernetes são lidos por quase todos); essas leituras ficam na tabela de
docs/arquitetura.md, para não encher o desenho de setas longas.
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.iac import Terraform

SAIDA = Path(__file__).resolve().parent.parent / "imgs" / "dependencia_terraform_fase4"

PARALELO = "4. em paralelo"
GRUPO = "cluster_" + PARALELO

graph_attr = {
    "fontsize": "20",
    "pad": "0.4",
    "nodesep": "0.3",
    "ranksep": "0.9",
    "compound": "true",
    "splines": "spline",
}

with Diagram(
    "Ordem de apply dos repositórios Terraform",
    filename=str(SAIDA),
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    edge_attr={"fontsize": "12"},
):
    banco = Terraform("1. infra-banco-dados\nVPC do banco + RDS")
    kubernetes = Terraform("2. infra-kubernetes\nVPC + EKS + ECR")
    catalogo = Terraform("3. catalogo\nDynamoDB + SNS")

    with Cluster(PARALELO, graph_attr={"rank": "same"}):
        estoque = Terraform("estoque")
        orcamento = Terraform("orcamento")
        pagamento = Terraform("pagamento")
        execucao = Terraform("execucao")

    os_service = Terraform("5. oficina-mecanica-fiap\nsecret + os-saga-eventos")
    lambda_auth = Terraform("6. lambda-auth\nLambda + API Gateway")

    banco >> Edge(label="VPC (peering)") >> kubernetes
    kubernetes >> Edge(label="cluster") >> catalogo
    catalogo >> Edge(label="tópico\ncatalogo-eventos", color="royalblue", style="dashed") >> estoque
    kubernetes >> Edge(lhead=GRUPO, label="cluster") >> orcamento
    orcamento >> Edge(ltail=GRUPO, label="filas e tópicos\ndos participantes") >> os_service
    os_service >> Edge(label="secret do JWT") >> lambda_auth
