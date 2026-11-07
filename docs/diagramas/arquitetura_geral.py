"""Diagrama geral da arquitetura da Fase 4: microsserviços, bancos e comunicação.

Gera docs/imgs/arquitetura_geral_fase4.png. Ver docs/diagramas/README.md.

Simplificações deliberadas, para o diagrama caber numa leitura:
- SQS e SNS aparecem como um nó só: o OS Service manda comandos para a fila de
  cada participante, e os eventos voltam pelos tópicos SNS até a os-saga-eventos
  (detalhes em docs/saga.md).
- LoadBalancers do Orçamento e do Pagamento e o envio de e-mail ficam no rótulo
  do serviço, não como nós.
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb, RDS
from diagrams.aws.integration import SimpleQueueServiceSqs as SQS
from diagrams.aws.network import APIGateway, ElasticLoadBalancing as ELB
from diagrams.k8s.compute import Deployment
from diagrams.onprem.client import Users
from diagrams.onprem.network import Internet
from diagrams.saas.alerting import Newrelic

SAIDA = Path(__file__).resolve().parent.parent / "imgs" / "arquitetura_geral_fase4"

MENSAGEM = dict(color="darkorange", style="bold", dir="both")
REST = dict(color="forestgreen", style="bold")
DADOS = dict(color="gray50")
HTTP = dict(color="black")

graph_attr = {
    "fontsize": "22",
    "pad": "0.4",
    "nodesep": "0.35",
    "ranksep": "0.9",
    "newrank": "true",
    "splines": "spline",
}


def servico(nome, rotulo, tipo_banco, rotulo_banco):
    """Quadro com o Deployment do serviço e o seu banco, lado a lado."""
    with Cluster(nome):
        app = Deployment(rotulo)
        app >> Edge(**DADOS) >> tipo_banco(rotulo_banco)
    return app


with Diagram(
    "Oficina Mecânica: microsserviços no EKS (Fase 4)",
    filename=str(SAIDA),
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    usuarios = Users("Admin, mecânico\ne cliente")
    gateway = APIGateway("API Gateway")
    lambda_auth = Lambda("Lambda\n(login por CPF)")
    lb_os = ELB("LoadBalancer")

    with Cluster("OS Service"):
        os_svc = Deployment("API + orquestrador\nda saga")
        rds_os = RDS("PostgreSQL")
        os_svc >> Edge(**DADOS) >> rds_os

    mensageria = SQS("SQS + SNS\ncomandos e eventos\nda saga")

    execucao = servico("Execução", "Execução", Dynamodb, "DynamoDB")
    estoque = servico("Estoque", "Estoque", RDS, "PostgreSQL")
    orcamento = servico(
        "Orçamento", "Orçamento\n(e-mail com link\nde aprovação)", Dynamodb, "DynamoDB"
    )
    with Cluster("Pagamento"):
        pagamento = Deployment("Pagamento\n(e-mail com link\nde pagamento)")
        rds_pag = RDS("PostgreSQL")
        pagamento >> Edge(**DADOS) >> rds_pag
    catalogo = servico(
        "Catálogo (fora da saga)",
        "Catálogo\n(publica PecaCadastrada\npara o Estoque)",
        Dynamodb, "DynamoDB",
    )

    mercado_pago = Internet("Mercado Pago")
    newrelic = Newrelic("New Relic\nAPM e traces\ndos 6 serviços")

    # Entrada
    usuarios >> Edge(**HTTP) >> gateway >> Edge(**HTTP) >> lambda_auth
    lambda_auth >> Edge(**DADOS) >> rds_os
    usuarios >> Edge(**HTTP) >> lb_os >> Edge(**HTTP) >> os_svc

    # Saga orquestrada
    os_svc >> Edge(label="comandos / eventos", **MENSAGEM) >> mensageria
    mensageria >> Edge(**MENSAGEM) >> [execucao, estoque, orcamento, pagamento]

    # REST síncrono, fora da saga
    execucao >> Edge(label="REST", **REST) >> catalogo

    # Externos
    pagamento >> Edge(**HTTP) >> mercado_pago
    lb_os >> Edge(style="invis") >> newrelic
