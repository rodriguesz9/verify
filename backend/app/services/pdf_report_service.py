"""
PDF Forensic Report Generator Service
Generates court-ready admissible PDF audit reports for media verifications using ReportLab.
"""

import io
from html import escape
from datetime import datetime, timezone
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_forensic_pdf(report: Dict[str, Any], filename: str, file_hash_sha256: str) -> bytes:
    """
    Builds a professional PDF forensic audit certificate.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0A1520")
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#3A6070")
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#006699")
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1A2530")
    )

    story = []

    # 1. Header
    story.append(Paragraph("VERIFY — RELATÓRIO AUTOMATIZADO DE MÍDIA", title_style))
    story.append(Paragraph("Sistema de Verificação de Autenticidade e Detecção de Mídias Sintéticas", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#00D4FF"), spaceBefore=5, spaceAfter=15))

    # 2. Protocol Info Box
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M:%S UTC")
    info_data = [
        [Paragraph("<b>Arquivo Analisado:</b>", body_style), Paragraph(escape(str(filename)), body_style)],
        [Paragraph("<b>Hash Criptográfico (SHA-256):</b>", body_style), Paragraph(f"<code>{file_hash_sha256}</code>", body_style)],
        [Paragraph("<b>Data e Hora da Auditoria:</b>", body_style), Paragraph(now_str, body_style)],
        [Paragraph("<b>Protocolo de Emissão:</b>", body_style), Paragraph(f"VER-{file_hash_sha256[:10].upper()}", body_style)],
    ]
    info_table = Table(info_data, colWidths=[160, 360])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0F8FF")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCE0EB")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # 3. Veredito Final
    veredito = report.get("veredito_final", report.get("verdict", "Desconhecido")).upper()
    score = report.get("score", 50)
    
    bg_color = colors.HexColor("#E6F9F0") if "AUTENTIC" in veredito else colors.HexColor("#FDE8EC")
    border_color = colors.HexColor("#00AA55") if "AUTENTIC" in veredito else colors.HexColor("#D92546")
    
    verdict_p = Paragraph(f"<b>RESULTADO:</b> {escape(veredito)} | Precisão não calibrada", section_title)
    summary_p = Paragraph(escape(str(report.get('explicacao_leiga', report.get('summary', '')))), body_style)

    v_table = Table([[verdict_p], [summary_p]], colWidths=[520])
    v_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_color),
        ('BOX', (0,0), (-1,-1), 1.5, border_color),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(v_table)
    story.append(Spacer(1, 15))

    # 4. Camadas de Evidência Auditadas
    story.append(Paragraph("DETALHAMENTO DAS CAMADAS AUDITADAS", section_title))
    story.append(Spacer(1, 6))

    layers_data = [
        [Paragraph("<b>Camada</b>", body_style), Paragraph("<b>Tecnologia</b>", body_style), Paragraph("<b>Resultado / Evidência</b>", body_style)],
        [
            Paragraph("1. Metadados", body_style),
            Paragraph("EXIFTool / C2PA", body_style),
            Paragraph(escape(str(report.get("metadata", {}).get("summary", "Camada não disponível."))), body_style)
        ],
        [
            Paragraph("2. Detecção IA", body_style),
            Paragraph("Hive / Sightengine", body_style),
            Paragraph("Consulte a cobertura e as pontuações individuais abaixo. Não são porcentagens de certeza.", body_style)
        ],
        [
            Paragraph("3. Proveniência", body_style),
            Paragraph("Wayback Machine", body_style),
            Paragraph(escape(str(report.get("contexto", {}).get("wayback", {}).get("summary", "Camada não realizada."))), body_style)
        ],
        [
            Paragraph("4. Consolidação", body_style),
            Paragraph(escape(str(report.get("model_used", "Política de evidências"))), body_style),
            Paragraph(escape(str(report.get("explicacao_forense", "Resultado inconclusivo."))), body_style)
        ]
    ]
    l_table = Table(layers_data, colWidths=[90, 110, 320])
    l_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2EBF0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BDCFDA")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(l_table)
    for name, layer in report.get("provider_coverage", {}).items():
        story.append(Paragraph(escape(f"{name}: {layer.get('status')} — sinal IA: {layer.get('ai_score')}"), body_style))
    for limitation in report.get("limitations", []):
        story.append(Paragraph(escape(str(limitation)), body_style))
    story.append(Spacer(1, 25))

    # 5. Rodapé / Carimbo Digital
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#BDCFDA"), spaceBefore=5, spaceAfter=10))
    footer_text = Paragraph(
        "<i>Este documento é um relatório técnico automatizado emitido pela plataforma Verify. "
        "Não constitui perícia judicial, garantia de autenticidade ou comprovação de fatos. Revise as limitações e fontes.</i>",
        subtitle_style
    )
    story.append(footer_text)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
