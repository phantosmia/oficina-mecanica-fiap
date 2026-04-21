#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/reports/security"

mkdir -p "$REPORT_DIR"

cd "$ROOT_DIR"

echo "[1/3] Gerando relatório Bandit..."
if ! poetry run bandit --exit-zero -r app -f json -o "$REPORT_DIR/bandit-report.json"; then
  echo "Bandit encontrou problemas ou retornou código não-zero. Relatório salvo em $REPORT_DIR/bandit-report.json"
fi

echo "[2/3] Gerando relatório pip-audit..."
if ! poetry run pip-audit -f json -o "$REPORT_DIR/pip-audit-report.json"; then
  echo "pip-audit encontrou vulnerabilidades. Relatório salvo em $REPORT_DIR/pip-audit-report.json"
fi

echo "[3/3] Verificando Trivy..."
if command -v trivy >/dev/null 2>&1; then
  if ! trivy fs --format json -o "$REPORT_DIR/trivy-fs-report.json" "$ROOT_DIR"; then
    echo "Trivy encontrou problemas ou retornou código não-zero. Relatório salvo em $REPORT_DIR/trivy-fs-report.json"
  fi
else
  echo "Trivy não encontrado. Instale o Trivy para gerar o relatório complementar de filesystem/container."
fi

echo "[4/4] Gerando versão amigável do relatório..."
poetry run python scripts/render_security_report.py

echo "Relatórios disponíveis em: $REPORT_DIR"
