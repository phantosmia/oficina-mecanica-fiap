# Segurança e Relatórios

## Relatório de vulnerabilidades

O projeto foi preparado para gerar relatórios de segurança com:

- `Bandit`: análise estática de segurança do código Python
- `pip-audit`: análise de vulnerabilidades nas dependências Python
- `Trivy`: análise complementar de filesystem e container

As ferramentas `Bandit` e `pip-audit` já estão configuradas nas dependências de desenvolvimento do projeto.

## Gerar relatório local

Execute:

```bash
bash scripts/security_scan.sh
```

Os relatórios serão gerados em:

- `reports/security/bandit-report.json`
- `reports/security/pip-audit-report.json`
- `reports/security/trivy-fs-report.json`, quando o Trivy estiver instalado
- `reports/security/security-report.md`
- `reports/security/security-report.pdf`

## Executar manualmente

```bash
poetry run bandit -r app
poetry run pip-audit
trivy fs .
```

## Relatório amigável

O script consolida achados em formatos mais fáceis de compartilhar com time, gestão e banca:

- Markdown: `reports/security/security-report.md`
- PDF: `reports/security/security-report.pdf`

## Observações

- `pip-audit` pode retornar código diferente de zero quando encontrar vulnerabilidades. Isso indica achados, não falha de configuração.
- `Trivy` não é instalado pelo Poetry; ele deve ser instalado no sistema para complementar a análise.
- Os relatórios JSON, Markdown e PDF gerados ficam ignorados no Git.

## Controles aplicados no projeto

- A API em Docker Compose roda com usuário sem privilégios (`app`, `uid=1001`).
- Segredos locais são mantidos fora do Git via `.env`, `.aws_credentials`, `terraform.tfvars` e `backend.hcl`.
- No AWS completo, dados sensíveis são armazenados em AWS Secrets Manager e consumidos pelo cluster via External Secrets.
- No AWS Academy, o workflow cria a Secret Kubernetes a partir do AWS Secrets Manager durante o deploy.
- Endpoints administrativos exigem JWT.
- CPF/CNPJ, placa e e-mail possuem validação de entrada.
