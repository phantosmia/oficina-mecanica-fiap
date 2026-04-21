from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "security"
MARKDOWN_REPORT = REPORT_DIR / "security-report.md"
PDF_REPORT = REPORT_DIR / "security-report.pdf"


@dataclass(frozen=True)
class Finding:
    source: str
    title: str
    severity: str
    details: str
    fix_version: str | None = None


def load_json_report(file_name: str) -> dict | list | None:
    report_path = REPORT_DIR / file_name
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def collect_bandit_findings(payload: dict | None) -> list[Finding]:
    if not payload:
        return []

    findings: list[Finding] = []
    for item in payload.get("results", []):
        findings.append(
            Finding(
                source="Bandit",
                title=item.get("test_name", "Achado de segurança"),
                severity=item.get("issue_severity", "UNKNOWN"),
                details=f"{item.get('filename', 'arquivo desconhecido')}:{item.get('line_number', '?')} - {item.get('issue_text', '')}",
            )
        )
    return findings


def collect_pip_audit_findings(payload: dict | None) -> list[Finding]:
    if not payload:
        return []

    findings: list[Finding] = []
    for dependency in payload.get("dependencies", []):
        package_name = dependency.get("name", "package")
        package_version = dependency.get("version", "?")
        for vuln in dependency.get("vulns", []):
            fix_versions = ", ".join(vuln.get("fix_versions", [])) or None
            findings.append(
                Finding(
                    source="pip-audit",
                    title=f"{package_name} {package_version} - {vuln.get('id', 'CVE desconhecido')}",
                    severity="HIGH",
                    details=vuln.get("description", "Sem descrição."),
                    fix_version=fix_versions,
                )
            )
    return findings


def collect_trivy_findings(payload: dict | None) -> list[Finding]:
    if not payload:
        return []

    findings: list[Finding] = []
    for result in payload.get("Results", []):
        target = result.get("Target", "target")
        for vuln in result.get("Vulnerabilities", []) or []:
            findings.append(
                Finding(
                    source="Trivy",
                    title=f"{target} - {vuln.get('VulnerabilityID', 'ID desconhecido')}",
                    severity=vuln.get("Severity", "UNKNOWN"),
                    details=vuln.get("Title") or vuln.get("Description", "Sem descrição."),
                    fix_version=vuln.get("FixedVersion"),
                )
            )
    return findings


def summarize(findings: list[Finding]) -> dict[str, int]:
    summary = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "UNKNOWN": 0}
    for finding in findings:
        severity = finding.severity.upper()
        summary[severity if severity in summary else "UNKNOWN"] += 1
    return summary


def build_markdown(findings: list[Finding], bandit_found: bool, pip_audit_found: bool, trivy_found: bool) -> str:
    summary = summarize(findings)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Relatório de Vulnerabilidades",
        "",
        f"Gerado em: {generated_at}",
        "",
        "## Ferramentas utilizadas",
        "",
        f"- Bandit: {'sim' if bandit_found else 'não'}",
        f"- pip-audit: {'sim' if pip_audit_found else 'não'}",
        f"- Trivy: {'sim' if trivy_found else 'não'}",
        "",
        "## Resumo executivo",
        "",
        f"- Total de achados: {len(findings)}",
        f"- Críticos: {summary['CRITICAL']}",
        f"- Altos: {summary['HIGH']}",
        f"- Médios: {summary['MEDIUM']}",
        f"- Baixos: {summary['LOW']}",
        f"- Não classificados: {summary['UNKNOWN']}",
        "",
        "## Achados",
        "",
    ]

    if not findings:
        lines.append("Nenhuma vulnerabilidade foi identificada pelos relatórios processados.")
        return "\n".join(lines) + "\n"

    for index, finding in enumerate(findings, start=1):
        lines.extend(
            [
                f"### {index}. {finding.title}",
                "",
                f"- Fonte: {finding.source}",
                f"- Severidade: {finding.severity}",
                f"- Correção sugerida: {finding.fix_version or 'não informada'}",
                "",
                finding.details,
                "",
            ]
        )

    return "\n".join(lines)


def build_pdf(markdown_content: str, findings: list[Finding]) -> None:
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = ParagraphStyle(
        "BodySmall",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=6,
    )

    story = [Paragraph("Relatório de Vulnerabilidades", title_style), Spacer(1, 0.5 * cm)]

    summary = summarize(findings)
    summary_table = Table(
        [
            ["Total", "Críticos", "Altos", "Médios", "Baixos", "Não classificados"],
            [len(findings), summary["CRITICAL"], summary["HIGH"], summary["MEDIUM"], summary["LOW"], summary["UNKNOWN"]],
        ],
        colWidths=[2.2 * cm, 2.5 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 4 * cm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 0.6 * cm), Paragraph("Achados", heading_style)])

    if not findings:
        story.append(Paragraph("Nenhuma vulnerabilidade foi identificada pelos relatórios processados.", body_style))
    else:
        for index, finding in enumerate(findings, start=1):
            details = (
                f"<b>{index}. {finding.title}</b><br/>"
                f"Fonte: {finding.source}<br/>"
                f"Severidade: {finding.severity}<br/>"
                f"Correção sugerida: {finding.fix_version or 'não informada'}<br/>"
                f"Detalhes: {finding.details}"
            )
            story.append(Paragraph(details, body_style))

    document = SimpleDocTemplate(str(PDF_REPORT), pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm)
    document.build(story)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    bandit_payload = load_json_report("bandit-report.json")
    pip_audit_payload = load_json_report("pip-audit-report.json")
    trivy_payload = load_json_report("trivy-fs-report.json")

    findings = [
        *collect_bandit_findings(bandit_payload if isinstance(bandit_payload, dict) else None),
        *collect_pip_audit_findings(pip_audit_payload if isinstance(pip_audit_payload, dict) else None),
        *collect_trivy_findings(trivy_payload if isinstance(trivy_payload, dict) else None),
    ]

    markdown_content = build_markdown(
        findings,
        bandit_found=bandit_payload is not None,
        pip_audit_found=pip_audit_payload is not None,
        trivy_found=trivy_payload is not None,
    )
    MARKDOWN_REPORT.write_text(markdown_content, encoding="utf-8")
    build_pdf(markdown_content, findings)

    print(f"Relatório Markdown gerado em: {MARKDOWN_REPORT}")
    print(f"Relatório PDF gerado em: {PDF_REPORT}")


if __name__ == "__main__":
    main()