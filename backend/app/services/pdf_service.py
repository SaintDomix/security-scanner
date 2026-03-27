import json
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from datetime import datetime

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

SEV_COLORS = {
    "critical": colors.HexColor("#DC2626"),
    "high":     colors.HexColor("#EA580C"),
    "medium":   colors.HexColor("#D97706"),
    "low":      colors.HexColor("#2563EB"),
    "info":     colors.HexColor("#6B7280"),
}

def _sev_color(sev: str):
    return SEV_COLORS.get(sev.lower(), colors.grey)


def generate_scan_report(scan_id: int, scan_data: dict) -> str:
    filename = f"scan_{scan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = REPORTS_DIR / filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=inch,
        rightMargin=inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", fontSize=22, textColor=colors.HexColor("#0F172A"),
                                 spaceAfter=6, fontName="Helvetica-Bold")
    h2_style = ParagraphStyle("H2", fontSize=14, textColor=colors.HexColor("#1E40AF"),
                               spaceAfter=4, spaceBefore=12, fontName="Helvetica-Bold")
    body_style = ParagraphStyle("Body", fontSize=9, textColor=colors.HexColor("#374151"),
                                spaceAfter=3, leading=13)
    small_style = ParagraphStyle("Small", fontSize=8, textColor=colors.HexColor("#6B7280"),
                                 spaceAfter=2, leading=11)
    code_style = ParagraphStyle("Code", fontSize=8, fontName="Courier",
                                textColor=colors.HexColor("#1E293B"),
                                backColor=colors.HexColor("#F1F5F9"),
                                spaceAfter=3, leading=11,
                                leftIndent=6, rightIndent=6)

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("SecureScanner", title_style))
    story.append(Paragraph(f"Security Scan Report — Scan #{scan_id}", styles["Normal"]))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
        f"Target: {scan_data.get('target', 'N/A')} | "
        f"Mode: {scan_data.get('scan_mode', 'N/A').upper()}",
        small_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1E40AF"), spaceAfter=10))

    # ── Summary table ────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h2_style))
    summary_data = [
        ["Tool", "Findings", "Critical", "High", "Medium", "Low"],
    ]
    tools = [
        ("Gitleaks (Secrets)", scan_data.get("gitleaks_findings", 0), scan_data.get("gitleaks", [])),
        ("Semgrep (SAST)", scan_data.get("semgrep_findings", 0), scan_data.get("semgrep", [])),
        ("Bearer (SAST/Privacy)", scan_data.get("bearer_findings", 0), scan_data.get("bearer", [])),
        ("DAST (Live Scan)", scan_data.get("dast_findings", 0), scan_data.get("dast", [])),
    ]
    total_c = total_h = total_m = total_l = 0
    for tool_name, count, findings in tools:
        c = sum(1 for f in findings if f.get("severity") == "critical")
        h = sum(1 for f in findings if f.get("severity") == "high")
        m = sum(1 for f in findings if f.get("severity") == "medium")
        l = sum(1 for f in findings if f.get("severity") == "low")
        total_c += c; total_h += h; total_m += m; total_l += l
        summary_data.append([tool_name, str(count), str(c), str(h), str(m), str(l)])
    summary_data.append(["TOTAL", str(total_c + total_h + total_m + total_l), str(total_c), str(total_h), str(total_m), str(total_l)])

    summary_table = Table(summary_data, colWidths=[2.2*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # ── Findings per tool ────────────────────────────────────────────────────
    def render_findings(section_title: str, findings: list, keys: list):
        if not findings:
            story.append(Paragraph(section_title, h2_style))
            story.append(Paragraph("✓ No issues found.", body_style))
            return

        story.append(Paragraph(f"{section_title} ({len(findings)} findings)", h2_style))
        for i, f in enumerate(findings[:100], 1):  # cap at 100
            sev = f.get("severity", "low")
            sev_color = _sev_color(sev)

            row_data = [[
                Paragraph(f"<b>#{i} [{sev.upper()}]</b> {f.get('title') or f.get('rule_id', '')}", body_style),
                Paragraph(sev.upper(), ParagraphStyle("Sev", fontSize=8, textColor=sev_color,
                           fontName="Helvetica-Bold", alignment=2)),
            ]]
            row_table = Table(row_data, colWidths=[5.5*inch, 0.8*inch])
            row_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
            ]))
            story.append(row_table)

            detail_parts = []
            for key, label in keys:
                val = f.get(key)
                if val:
                    detail_parts.append(f"<b>{label}:</b> {str(val)[:200]}")
            if detail_parts:
                story.append(Paragraph("  |  ".join(detail_parts), small_style))
            story.append(Spacer(1, 4))

    render_findings("🔑 Gitleaks — Secret Detection",
        scan_data.get("gitleaks", []),
        [("file", "File"), ("line", "Line"), ("description", "Desc"), ("rule_id", "Rule")])

    render_findings("🔍 Semgrep — Static Analysis",
        scan_data.get("semgrep", []),
        [("file", "File"), ("line", "Line"), ("message", "Message"), ("rule_id", "Rule")])

    render_findings("🛡️  Bearer — SAST & Privacy",
        scan_data.get("bearer", []),
        [("file", "File"), ("line", "Line"), ("description", "Desc"), ("cwe_ids", "CWE")])

    render_findings("🌐 DAST — Dynamic Analysis",
        scan_data.get("dast", []),
        [("title", "Title"), ("description", "Desc"), ("solution", "Fix"), ("evidence", "Evidence")])

    doc.build(story)
    return str(output_path)
