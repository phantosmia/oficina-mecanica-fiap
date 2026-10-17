#!/usr/bin/env bash
# Copia as credenciais do AWS Academy Lab (que expiram a cada sessão) do
# arquivo local .aws_credentials para os secrets do GitHub de todos os
# repositórios que provisionam ou fazem deploy na AWS.
#
# Uso: bash scripts/atualiza-credenciais-aws.sh [arquivo-de-credenciais]
#
# O arquivo segue o formato do ~/.aws/credentials (perfil [default]), que é o
# que o painel "AWS Details" do Lab mostra para copiar.
set -euo pipefail

CREDENTIALS_FILE="${1:-$(dirname "$0")/../.aws_credentials}"
OWNER="phantosmia"

# Secrets de repositório: os workflows destes repositórios leem as credenciais
# fora de qualquer GitHub Environment.
REPO_SECRETS=(
  oficina-mecanica-infra-banco-dados
  oficina-mecanica-infra-kubernetes
  oficina-mecanica-lambda-auth
  oficina-mecanica-catalogo
  oficina-mecanica-estoque
  oficina-mecanica-orcamento
  oficina-mecanica-pagamento
  oficina-mecanica-execucao
)

# Secrets de GitHub Environment (repositório:ambiente).
ENV_SECRETS=(
  oficina-mecanica-fiap:homologacao
)

read_key() {
  python3 - "$CREDENTIALS_FILE" "$1" <<'PY'
import configparser
import sys

config = configparser.ConfigParser()
config.read(sys.argv[1])
print(config["default"][sys.argv[2]], end="")
PY
}

[ -f "$CREDENTIALS_FILE" ] || { echo "Arquivo não encontrado: $CREDENTIALS_FILE" >&2; exit 1; }

for key in aws_access_key_id aws_secret_access_key aws_session_token; do
  name="${key^^}"
  value="$(read_key "$key")"

  for repo in "${REPO_SECRETS[@]}"; do
    printf '%s' "$value" | gh secret set "$name" -R "$OWNER/$repo"
  done

  for entry in "${ENV_SECRETS[@]}"; do
    printf '%s' "$value" | gh secret set "$name" -R "$OWNER/${entry%%:*}" -e "${entry##*:}"
  done
done

echo "Credenciais atualizadas em ${#REPO_SECRETS[@]} repositórios e ${#ENV_SECRETS[@]} ambiente(s)."
