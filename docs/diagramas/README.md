# Diagramas como código

Diagramas da Fase 4 gerados com a biblioteca [diagrams](https://diagrams.mingrammer.com/). Os PNGs ficam em `docs/imgs/`.

| Script | Gera |
|---|---|
| `arquitetura_geral.py` | `imgs/arquitetura_geral_fase4.png`: os 6 microsserviços, bancos, mensageria e serviços externos |
| `dependencia_terraform.py` | `imgs/dependencia_terraform_fase4.png`: ordem de apply entre os 9 repositórios Terraform |

A biblioteca não faz parte das dependências da API. Para gerar de novo, é preciso ter o Graphviz (`apt install graphviz`) e um ambiente à parte:

```bash
python3 -m venv /tmp/diagrams-venv
/tmp/diagrams-venv/bin/pip install diagrams==0.25.1
/tmp/diagrams-venv/bin/python docs/diagramas/arquitetura_geral.py
/tmp/diagrams-venv/bin/python docs/diagramas/dependencia_terraform.py
```
