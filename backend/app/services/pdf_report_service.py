"""
PDF Forensic Report Generator Service
Renders the original server-verified result, without running a second analysis.
"""

import io
import math
from html import escape
from datetime import datetime, timezone
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def display_value(value, fallback="Não disponível") -> str:
    """Render absence explicitly, without replacing real zero/False values."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return fallback
    return str(value)


def detector_signal(value) -> str:
    """Only display documented probability-scale detector outputs, not certainty."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "não disponível"
    if not math.isfinite(value) or not 0 <= value <= 1:
        return "não disponível"
    return str(value)


def factual_labels(report):
    sources = report.get("veracity_decision_basis") in {"retrieved_sources", "mixed_evidence"} or report.get("evidence_mode") == "retrieved_sources"
    return {"supported": "Corroborado nas fontes consultadas" if sources else "Corroborado pelas checagens correspondentes",
            "refuted": "Refutado nas fontes consultadas" if sources else "Refutado pelas checagens correspondentes",
            "conflicting": "Fontes discordantes", "mixed": "Afirmações com resultados diferentes",
            "unverified": "Evidência insuficiente", "probably_false": "Provavelmente falsa / sem fundamento"}


def factual_source_lines(source):
    """Display server-owned document evidence separately from ClaimReview."""
    if source.get("relation") in {"supports", "refutes"} and source.get("excerpt"):
        return ["Documento consultado: " + display_value(source.get("title") or source.get("publisher_family")),
                display_value(source.get("url")),
                "Trecho do corpo: " + display_value(source.get("excerpt")),
                "Relação: " + ("sustenta a afirmação" if source["relation"] == "supports" else "contradiz a afirmação"),
                "Recuperado em: " + display_value(source.get("retrieved_at")),
                "Família da fonte: " + display_value(source.get("publisher_family")),
                "Comparação assistida por modelo e regras conservadoras; não é checagem editorial publicada nem garantia de verdade."]
    return ["Fonte correspondente: " + display_value(source.get("publisher") or source.get("publisher_family"))
            + " | Avaliação: " + display_value(source.get("rating"))
            + " | Data: " + display_value(source.get("review_date")), display_value(source.get("url"))]


def source_crosscheck_lines(report):
    """Preserve observations even when they were insufficient for a decision."""
    layer = report.get("source_corroboration")
    if (not isinstance(layer, dict) or layer.get("version") != "source_corroboration_v1"
            or layer.get("decision_role") != "grounded_source_comparison"):
        return []
    labels = {"corroborated": "Corroborada nas fontes consultadas", "refuted": "Refutada nas fontes consultadas",
              "conflicting": "Fontes discordantes", "mixed": "Afirmações com resultados diferentes",
              "insufficient": "Evidência insuficiente"}
    lines = ["CRUZAMENTO DE FONTES CONSULTADAS", "Estado: " + labels.get(layer.get("state"), "Evidência insuficiente"),
             "Comparação de trechos recuperados, não votação de IAs nem certificado de verdade."]
    if layer.get("reason"):
        lines.append(display_value(layer["reason"]))
    coverage = layer.get("coverage") if isinstance(layer.get("coverage"), dict) else {}
    lines.append("Cobertura completa das afirmações: " + ("Sim" if coverage.get("complete_claim_coverage") is True else "Não"))
    decisions = report.get("claim_assessments") if isinstance(report.get("claim_assessments"), list) else []
    incorporated = set()
    for decision in decisions:
        if isinstance(decision, dict) and isinstance(decision.get("evidence"), list):
            incorporated.update((source.get("url"), source.get("excerpt"))
                                for source in decision["evidence"] if isinstance(source, dict))
    claims = layer.get("claims") if isinstance(layer.get("claims"), list) else []
    for decision in claims[:5]:
        if not isinstance(decision, dict):
            continue
        lines.extend(["Afirmação comparada: " + display_value(decision.get("claim")),
                      "Resultado do cruzamento: " + labels.get(decision.get("state"), "Evidência insuficiente"),
                      display_value(decision.get("explanation"))])
        evidence = decision.get("evidence") if isinstance(decision.get("evidence"), list) else []
        if not evidence:
            lines.append("Nenhum trecho aceito nesta comparação; ausência não comprova falsidade.")
        for source in evidence[:6]:
            if not isinstance(source, dict):
                continue
            if isinstance(source.get("claim_part"), str) and source["claim_part"].strip():
                lines.append("Parte avaliada: " + display_value(source["claim_part"]))
            if (source.get("url"), source.get("excerpt")) in incorporated:
                lines.append("Trecho já apresentado na avaliação individual acima; não é outra fonte independente.")
            else:
                lines.extend(factual_source_lines(source))
            if source.get("context"):
                lines.append("Contexto adjacente: " + display_value(source["context"]))
        if len(evidence) > 6:
            lines.append(f"Outros {len(evidence) - 6} registros de evidência não reproduzidos neste PDF; consulte o relatório original.")
        excluded = decision.get("excluded_evidence") if isinstance(decision.get("excluded_evidence"), list) else []
        for source in excluded[:6]:
            if isinstance(source, dict):
                lines.append("Trecho NÃO usado: " + display_value(source.get("exclusion_reason")))
        if len(excluded) > 6:
            lines.append(f"Outros {len(excluded) - 6} motivos de exclusão não reproduzidos neste PDF; consulte o relatório original.")
    excluded = layer.get("excluded_sources") if isinstance(layer.get("excluded_sources"), list) else []
    for source in excluded[:3]:
        if isinstance(source, dict):
            lines.append("Documento NÃO usado: " + display_value(source.get("url")))
            lines.append(display_value(source.get("exclusion_reason")))
    limitations = layer.get("limitations") if isinstance(layer.get("limitations"), list) else []
    lines.extend("Limite do cruzamento: " + display_value(value) for value in limitations[:8])
    return lines


def generate_text_pdf(report: Dict[str, Any]) -> bytes:
    """Render a signed text/link result, not a media-origin certificate.

    All variable-length content flows outside table rows. Original input,
    extracted page text and human-review provenance remain distinct.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=40, rightMargin=40,
                           topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("TextReportBody", parent=styles["Normal"], fontSize=10,
                          leading=14, spaceAfter=7, textColor=colors.HexColor("#1A2530"))
    heading = ParagraphStyle("TextReportSection", parent=body, fontName="Helvetica-Bold",
                             fontSize=13, leading=17, spaceBefore=13, keepWithNext=True,
                             textColor=colors.HexColor("#006699"))
    title = ParagraphStyle("TextReportTitle", parent=heading, fontSize=20, leading=24)
    story = []
    labels = factual_labels(report)

    def paragraph(value, style=body):
        story.append(Paragraph(escape(display_value(value)).replace("\n", "<br/>"), style))

    def mapping(value):
        return value if isinstance(value, dict) else {}

    def entries(value):
        return value if isinstance(value, list) else []

    is_url = report.get("content_type") == "url"
    paragraph("VERIFY - RELATÓRIO DE " + ("LINK" if is_url else "TEXTO"), title)
    paragraph("Cópia do resultado original. A exportação não repete consultas nem atualiza as fontes.")
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#006699")))
    paragraph("Análise original: " + display_value(report.get("analyzed_at")))
    paragraph("PDF emitido em: " + datetime.now(timezone.utc).isoformat())
    paragraph("Versão da política: " + display_value(report.get("policy_version")))
    paragraph("RESULTADO E LIMITES", heading)
    paragraph("Veracidade do conteúdo: " + labels.get(report.get("veracity_status"), "Evidência insuficiente"))
    paragraph("Estado da análise: " + {"partial": "Parcial (cobertura limitada)",
                                       "inconclusive": "Inconclusiva"}.get(report.get("analysis_status"), "Não informado"))
    paragraph(report.get("summary"))
    if report.get("plain_explanation") != report.get("summary"):
        paragraph(report.get("plain_explanation"))
    paragraph("Precisão não calibrada. O índice de decisão não é probabilidade de verdade. Este relatório não autentica mídia, autoria ou identidade.")
    paragraph("ENTRADA ORIGINAL", heading)
    paragraph(report.get("query_input"))
    if is_url:
        paragraph("URL final após redirecionamentos: " + display_value(report.get("source_url")))
        extraction = mapping(report.get("source_extraction"))
        paragraph("Método: " + {"static_html": "HTML estático", "plain_text": "Texto simples"}.get(extraction.get("method"), "Não informado"))
        paragraph("Texto efetivamente analisado (não equivale à página inteira):")
        paragraph(report.get("source_text"))
        if extraction.get("truncated"):
            paragraph("Texto limitado aos primeiros 5.000 caracteres extraídos; o restante não foi analisado.")
        paragraph("A extração não executa JavaScript nem resolve toda a visibilidade por CSS.")
    review = mapping(report.get("text_review"))
    if review:
        paragraph("CONFERÊNCIA HUMANA DO TEXTO", heading)
        paragraph("Nova checagem do texto confirmado pelo usuário. A edição não comprova correspondência ao arquivo nem autenticidade da mídia.")
        paragraph("Arquivo de origem: " + display_value(review.get("filename")))
        paragraph("SHA-256 do arquivo de origem (identifica bytes, não prova verdade): " + display_value(review.get("file_hash_sha256")))
        paragraph("Leitura automática original:")
        paragraph(review.get("original_text"))
        paragraph("Texto confirmado para esta checagem:")
        paragraph(review.get("reviewed_text"))
        paragraph("Alterado pelo usuário: " + ("Sim" if review.get("changed") else "Não"))
        paragraph("Conferido em: " + display_value(review.get("reviewed_at")))
    paragraph("AFIRMAÇÕES, FONTES E CORRESPONDÊNCIA", heading)
    decisions = entries(report.get("claim_assessments"))
    if not decisions:
        paragraph("Nenhuma avaliação individual utilizável. Não há conclusão sobre verdade ou falsidade.")
    for index, decision in enumerate(decisions, 1):
        decision = mapping(decision)
        paragraph(f"Afirmação {index}: " + display_value(decision.get("claim")), heading)
        paragraph("Resultado: " + factual_labels(decision).get(decision.get("status"), "Evidência insuficiente"))
        paragraph(decision.get("explanation"))
        evidence = entries(decision.get("evidence"))
        if not evidence:
            paragraph("Nenhuma fonte correspondente utilizável para esta afirmação.")
        for source in evidence:
            source = mapping(source)
            for line in factual_source_lines(source):
                paragraph(line)
        for source in entries(decision.get("excluded_evidence")):
            source = mapping(source)
            paragraph("Fonte recuperada NÃO usada: " + display_value(source.get("publisher") or source.get("url")))
            paragraph("Motivo: " + display_value(source.get("exclusion_reason")))
            if source.get("url"):
                paragraph(source["url"])
    for index, line in enumerate(source_crosscheck_lines(report)):
        paragraph(line, heading if index == 0 else body)
    paragraph("ALERTAS E LIMITAÇÕES", heading)
    for alert in entries(report.get("red_flags")):
        paragraph("Alerta: " + display_value(alert))
    for name, layer in mapping(report.get("provider_coverage")).items():
        layer = mapping(layer)
        state = display_value(layer.get("status"))
        state = {"not_configured": "Não configurado", "disabled": "Desativado",
                 "success": "Respondeu (não comprova precisão)", "timeout": "Tempo limite atingido",
                 "error": "Falha na execução", "rate_limited": "Limite de uso atingido",
                 "invalid_response": "Resposta inválida", "unavailable": "Indisponível"}.get(state, state)
        paragraph("Cobertura - " + name + ": " + state)
        if layer.get("reason"):
            paragraph(layer["reason"])
    for limitation in entries(report.get("limitations")):
        paragraph(limitation)
    paragraph("Próximo passo: " + display_value(report.get("elderly_tip")))
    story.append(HRFlowable(width="100%", thickness=.5, color=colors.HexColor("#BDCFDA")))
    paragraph("Relatório automatizado de apoio à checagem. Não constitui perícia judicial, comprovação de fatos ou garantia de autenticidade. Confira datas, fontes e limitações.")

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#3A6070"))
        canvas.drawString(40, 24, "Verify | Apoio à checagem; não constitui perícia")
        canvas.drawRightString(letter[0] - 40, 24, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def generate_forensic_pdf(report: Dict[str, Any], filename: str, file_hash_sha256: str) -> bytes:
    """
    Builds an explanatory report, not a certificate or judicial examination.
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
        textColor=colors.HexColor("#006699"),
        keepWithNext=True
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
    story.append(Paragraph("VERIFY - RELATÓRIO AUTOMATIZADO DE MÍDIA", title_style))
    story.append(Paragraph("Apoio à checagem - indícios de origem e conteúdo são avaliações separadas", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#00D4FF"), spaceBefore=5, spaceAfter=15))

    # 2. Protocol Info Box
    emitted_at = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M:%S UTC")
    analyzed_at = str(report.get("analyzed_at") or "Não registrada nesta análise legada.")
    info_data = [
        [Paragraph("<b>Arquivo Analisado:</b>", body_style), Paragraph(escape(str(filename)), body_style)],
        [Paragraph("<b>Hash Criptográfico (SHA-256):</b>", body_style), Paragraph(f"<code>{file_hash_sha256}</code>", body_style)],
        [Paragraph("<b>Análise original:</b>", body_style), Paragraph(escape(analyzed_at), body_style)],
        [Paragraph("<b>PDF emitido em:</b>", body_style), Paragraph(emitted_at, body_style)],
        [Paragraph("<b>Versão da política:</b>", body_style), Paragraph(escape(display_value(report.get("policy_version"), "Não informada")), body_style)],
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
    veredito = display_value(report.get("veredito_final") or report.get("verdict"), "Inconclusivo").upper()
    if report.get("content_type") == "video":
        visual_positive = report.get("visual_authenticity_status") in {"ai_indications", "manipulation_indications"} and report.get("visual_analysis_status") != "inconclusive"
        audio = report.get("audio_analysis") if isinstance(report.get("audio_analysis"), dict) else {}
        details = report.get("media_details") if isinstance(report.get("media_details"), dict) else {}
        audio_positive = (details.get("has_audio") is not False and audio.get("authenticity_status") == "ai_indications"
                          and audio.get("analysis_status") in {"partial", "complete", "completed", "success"})
        veredito = "SINAIS VISUAIS E ACÚSTICOS" if visual_positive and audio_positive else "INDÍCIOS DE FALA SINTÉTICA" if audio_positive else "INDÍCIOS EM QUADROS AMOSTRADOS" if visual_positive else "INCONCLUSIVO"
    inconclusive = veredito == "INCONCLUSIVO"
    bg_color = colors.HexColor("#F0F8FF") if inconclusive else colors.HexColor("#FFF4DF")
    border_color = colors.HexColor("#006699") if inconclusive else colors.HexColor("#AC6500")
    
    result_label = "RESULTADO DAS CAMADAS" if report.get("content_type") == "video" else "ORIGEM DA MÍDIA"
    verdict_p = Paragraph(f"<b>{result_label}:</b> {escape(veredito)} | Precisão não calibrada", section_title)
    summary_p = Paragraph(escape(display_value(report.get('explicacao_leiga') or report.get('summary'), 'Explicação não disponível nesta análise.')), body_style)

    # Only short labels belong inside an unsplittable table row. A long
    # explanation must flow across pages instead of raising LayoutError.
    v_table = Table([[verdict_p]], colWidths=[520])
    v_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_color),
        ('BOX', (0,0), (-1,-1), 1.5, border_color),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(v_table)
    story.append(Spacer(1, 8))
    story.append(summary_p)
    story.append(Spacer(1, 15))

    factual_content = report.get("content_analysis")
    if not isinstance(factual_content, dict) or not factual_content:
        factual_content = report
    labels = {**factual_labels(factual_content),
              "undetermined": "Origem indeterminada",
              "ai_indications": "Indícios de geração por IA", "manipulation_indications": "Indícios de manipulação",
              "not_applicable": "Não se aplica", "inconclusive": "Inconclusivo"}
    status_labels = {"inconclusive": "Inconclusiva", "partial": "Parcial (cobertura limitada)",
                     "complete": "Concluída", "completed": "Concluída", "success": "Concluída",
                     "error": "Falha na execução", "failed": "Não foi possível concluir",
                     "unavailable": "Indisponível", "not_configured": "Não configurada",
                     "not_tested": "Não testada", "disabled": "Desativada", "timeout": "Tempo limite atingido",
                     "invalid_response": "Resposta inválida", "rate_limited": "Limite de uso atingido",
                     "aggregate_only": "Resultado agregado", "pending": "Pendente",
                     "in_progress": "Em processamento", "blocked_uncertain": "Estado não confirmado",
                     "blocked_expired": "Acompanhamento encerrado", "capacity_exceeded": "Serviço ocupado",
                     "pending_user_review": "Aguarda conferência do texto", "skipped": "Não executada",
                     "no_text": "Nenhum texto extraído", "no_speech": "Nenhuma fala utilizável"}

    def status(value):
        value = display_value(value, "Não informada")
        return status_labels.get(value, value)

    def text(value):
        return escape(display_value(value)).replace("\n", "<br/>")

    def paragraph(value):
        story.append(Paragraph(text(value), body_style))

    def mapping(value):
        return value if isinstance(value, dict) else {}

    def entries(value):
        return value if isinstance(value, list) else []

    paragraph("Estado da análise: " + status(report.get("analysis_status", "Não informado")))
    authenticity = report.get("authenticity_status") or "undetermined"
    if report.get("content_type") == "video":
        visual = report.get("visual_authenticity_status")
        if visual in {"undetermined", "ai_indications", "manipulation_indications"}:
            if report.get("visual_analysis_status") == "inconclusive":
                visual = "undetermined"
            paragraph("Origem dos quadros visuais: " + labels[visual])
        else:
            paragraph("Origem visual não separada neste relatório legado. O resultado geral não permite inferir a origem das imagens.")
        paragraph("Estado da análise visual: " + status(report.get("visual_analysis_status")))
        if report.get("visual_detector_disagreement") is True:
            paragraph("Os detectores visuais discordaram. É necessária revisão dos quadros amostrados.")
        audio = mapping(report.get("audio_analysis"))
        has_audio = mapping(report.get("media_details")).get("has_audio")
        if has_audio is False:
            paragraph("Faixa de áudio: não existe neste vídeo. Nenhuma voz foi avaliada.")
        elif audio:
            audio_origin = audio.get("authenticity_status")
            audio_state = audio.get("analysis_status")
            usable = audio_state in {"partial", "complete", "completed", "success"}
            paragraph("Origem da faixa de áudio: " + ("Indícios de possível fala sintética" if usable and audio_origin == "ai_indications" else "Não determinada"))
            paragraph("Estado da análise do áudio: " + status(audio_state))
            if audio.get("detector_disagreement") is True:
                paragraph("Os detectores da faixa de áudio discordaram. A origem da voz exige revisão.")
            paragraph("Sinais da voz não se aplicam à origem das imagens. Não identificam a pessoa, não comprovam clonagem nem verificam sincronização labial ou o vídeo inteiro.")
        else:
            paragraph("Faixa de áudio: análise não disponível. Não é possível concluir a origem da voz.")
    else:
        paragraph("Origem/autenticidade: " + labels.get(str(authenticity), str(authenticity)))
    story.append(Spacer(1, 12))
    story.append(Paragraph("CONTEÚDO E AFIRMAÇÕES - NÃO CONFUNDIR COM ORIGEM", section_title))
    content = mapping(report.get("content_analysis")) or report
    veracity = content.get("veracity_status") or "unverified"
    if content.get("status"):
        paragraph("Estado da checagem do conteúdo: " + status(content["status"]))
    paragraph("Veracidade do conteúdo: " + labels.get(str(veracity), str(veracity)))
    paragraph(display_value(content.get("summary"), "Não houve checagem utilizável do conteúdo."))
    extracted = report.get("transcription") or mapping(mapping(report.get("forensics")).get("ocr")).get("text")
    if extracted:
        paragraph("Texto extraído (OCR/transcrição; confira com o arquivo original):")
        paragraph(extracted)
    for decision in entries(content.get("claim_assessments")):
        decision = mapping(decision)
        story.append(Spacer(1, 7))
        paragraph("Afirmação: " + display_value(decision.get("claim")))
        state = decision.get("status") or "unverified"
        paragraph("Resultado: " + factual_labels(decision).get(str(state), str(state)))
        paragraph(decision.get("explanation", ""))
        for source in entries(decision.get("evidence")):
            source = mapping(source)
            for line in factual_source_lines(source):
                paragraph(line)
        for source in entries(decision.get("excluded_evidence")):
            source = mapping(source)
            paragraph("Fonte recuperada NÃO usada: " + display_value(source.get("publisher") or source.get("url")))
            paragraph("Motivo: " + display_value(source.get("exclusion_reason"), "Não corresponde à decisão."))
            if source.get("url"):
                paragraph(source["url"])
    for line in source_crosscheck_lines(content):
        paragraph(line)
    for limitation in entries(content.get("limitations")):
        paragraph("Limitação do conteúdo: " + display_value(limitation))
    story.append(Spacer(1, 15))

    # 4. Camadas de Evidência Auditadas
    story.append(Paragraph("DETALHAMENTO DAS CAMADAS AUDITADAS", section_title))
    story.append(Spacer(1, 6))

    layers_data = [
        [Paragraph("<b>Camada</b>", body_style), Paragraph("<b>Tecnologia</b>", body_style), Paragraph("<b>Resultado / Evidência</b>", body_style)],
        [
            Paragraph("1. Metadados", body_style),
            Paragraph("EXIFTool / C2PA", body_style),
            Paragraph("Resumo dos metadados disponível abaixo, quando executado.", body_style)
        ],
        [
            Paragraph("2. Detecção IA", body_style),
            Paragraph("Hive / Sightengine", body_style),
            Paragraph("Consulte a cobertura e as pontuações individuais abaixo. Não são porcentagens de certeza.", body_style)
        ],
        [
            Paragraph("3. Proveniência", body_style),
            Paragraph("Wayback Machine", body_style),
            Paragraph("Resumo da pesquisa de proveniência disponível abaixo, quando executado.", body_style)
        ],
        [
            Paragraph("4. Consolidação", body_style),
            Paragraph("Política de evidências", body_style),
            Paragraph("Explicação e versão do modelo disponíveis abaixo.", body_style)
        ]
    ]
    l_table = Table(layers_data, colWidths=[90, 110, 320], repeatRows=1)
    l_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2EBF0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BDCFDA")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(l_table)
    story.append(Spacer(1, 8))
    paragraph("Metadados: " + display_value(mapping(report.get("metadata")).get("summary"), "Camada não disponível."))
    paragraph("Proveniência: " + display_value(mapping(mapping(report.get("contexto")).get("wayback")).get("summary"), "Camada não realizada."))
    paragraph("Consolidação (" + display_value(report.get("model_used"), "Política de evidências") + "): "
              + display_value(report.get("explicacao_forense"), "Resultado inconclusivo."))
    for indication in entries(report.get("red_flags")):
        paragraph("Indício encontrado: " + display_value(indication))
    if mapping(report.get("provider_coverage")):
        paragraph("Escala dos sinais: 0 a 1; não são porcentagens de certeza ou veracidade. Pontuação ausente não significa zero.")
    for name, layer in mapping(report.get("provider_coverage")).items():
        layer = mapping(layer)
        if layer.get("voting_eligible") is False:
            paragraph(f"{name}: {status(layer.get('status'))} - experimental, sem participação no veredito.")
        elif str(layer.get("decision_role")) in {"ocr_only", "inspection_only", "transcription_only"}:
            paragraph(f"{name}: {status(layer.get('status'))} - extração/inspeção auxiliar, não decide verdade ou origem.")
        else:
            paragraph(f"{name}: {status(layer.get('status'))} - sinal IA: {detector_signal(layer.get('ai_score'))}; sinal facial: {detector_signal(layer.get('deepfake_score'))}.")
        if layer.get("provider") or layer.get("model_used"):
            paragraph(f"Fornecedor/modelo: {layer.get('provider') or name} / {layer.get('model_used') or 'não informado'}.")
        if layer.get("reason"):
            paragraph(layer["reason"])
    if report.get("content_type") == "video" and mapping(report.get("media_details")).get("has_audio") is not False:
        for name, layer in mapping(mapping(report.get("audio_analysis")).get("provider_coverage")).items():
            layer = mapping(layer)
            if layer.get("decision_role") == "transcription_only":
                paragraph(f"Áudio/{name}: {status(layer.get('status'))} - transcrição; não determina origem da voz.")
            elif layer.get("voting_eligible") is False:
                paragraph(f"Áudio/{name}: {status(layer.get('status'))} - experimental, excluído do veredito.")
            else:
                paragraph(f"Áudio/{name}: {status(layer.get('status'))} - sinal de fala sintética: {detector_signal(layer.get('ai_score'))}.")
            if layer.get("reason"):
                paragraph(layer["reason"])
    for limitation in entries(report.get("limitations")):
        paragraph("Limitação da mídia: " + display_value(limitation))
    video = mapping(mapping(report.get("forensics")).get("video"))
    if video:
        paragraph(f"Vídeo: {display_value(video.get('sampled_frames'), 'não informado')} quadros amostrados; tempos (segundos): {display_value(video.get('timestamps_seconds'), 'não informados')}.")
        paragraph("A amostragem não verifica todos os quadros nem autentica identidades ou sincronização labial.")
    paragraph("Próximo passo: " + display_value(report.get("dica_seguranca") or report.get("elderly_tip"), "Confira as fontes originais."))
    story.append(Spacer(1, 8))

    # 5. Rodapé / Carimbo Digital
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#BDCFDA"), spaceBefore=5, spaceAfter=6))
    footer_text = Paragraph(
        "<i>Este documento é um relatório técnico automatizado emitido pela plataforma Verify. "
        "Não constitui perícia judicial, garantia de autenticidade ou comprovação de fatos. Revise as limitações e fontes.</i>",
        subtitle_style
    )
    story.append(footer_text)

    def page_footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#3A6070"))
        canvas.drawString(40, 24, "Verify | Apoio à checagem; não constitui perícia")
        canvas.drawRightString(letter[0] - 40, 24, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
