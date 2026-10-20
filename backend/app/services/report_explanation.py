"""Render the completed factual decision; never classify or call a model.

Adapts Juan Oliveira's explicit text/link report flow to the grounded policy.
Only accepted evidence is presented. Search snippets and provider error bodies
are deliberately not inputs to this explanation.
"""
from copy import deepcopy
from urllib.parse import urlsplit

VERSION = "grounded_text_explanation_v1"
LABELS = {
    "supported": "verificado como verdadeiro nas fontes consultadas",
    "refuted": "verificado como falso nas fontes consultadas",
    "conflicting": "evidências em desacordo; exige conferência humana",
    "unverified": "sem evidência correspondente suficiente para concluir",
}


def _safe_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(char.isspace() for char in value):
        return None
    try:
        url = urlsplit(value)
        if (url.scheme == "https" and url.hostname and not url.username and not url.password
                and url.port in (None, 443)):
            return value
    except ValueError:
        pass
    return None


def _references(assessment):
    sources = []
    allowed = {"supports", "supported"} if assessment["status"] == "supported" else (
        {"refutes", "refuted"} if assessment["status"] == "refuted" else
        {"supports", "supported", "refutes", "refuted"})
    evidence = assessment.get("evidence")
    for item in evidence if isinstance(evidence, list) else []:
        if (not isinstance(item, dict) or item.get("exclusion_reason")
                or item.get("source_role") == "submitted_source" or item.get("relation") not in allowed):
            continue
        url = _safe_url(item.get("url"))
        if not url or any(source["url"] == url for source in sources):
            continue
        documentary = assessment.get("evidence_mode") == "retrieved_sources"
        source = {"url": url, "kind": "document" if documentary else "published_review"}
        # A reviewed claim is not a passage from an article. Only documentary
        # evidence already accepted by the source policy has literal quotes.
        quote = item.get("excerpt")
        if (documentary
                and isinstance(quote, str) and quote.strip() and len(quote) <= 600):
            source["excerpt"] = quote  # Never shorten away a negation/date.
        sources.append(source)
        if len(sources) == 2:
            break
    return sources


def _coverage_notes(report):
    coverage = report.get("provider_coverage")
    statuses = {item.get("status") for item in coverage.values() if isinstance(item, dict)
                and isinstance(item.get("status"), str)} if isinstance(coverage, dict) else set()
    notes = []
    for values, note in (
        ({"rate_limited", "budget_exhausted"}, "O limite de algumas consultas foi atingido; isso não indica que a informação seja falsa."),
        ({"timeout"}, "Algumas consultas não terminaram no tempo disponível; isso não indica verdade nem falsidade."),
        ({"not_configured"}, "Algumas consultas não estavam habilitadas; a pesquisa ficou limitada."),
        ({"error", "invalid_response"}, "Algumas consultas não retornaram dados utilizáveis; essas falhas não foram tratadas como evidência."),
    ):
        if statuses & values:
            notes.append(note)
    return notes


def enrich_grounded_report(report):
    """Return a copy, changing only prose and an explanation-only envelope."""
    if not isinstance(report, dict):
        return deepcopy(report)
    result = deepcopy(report)
    if isinstance(result.get("report_explanation"), dict) and result["report_explanation"].get("version") == VERSION:
        return result
    if result.get("veracity_status") not in {*LABELS, "mixed"}:
        return result
    original = result.get("plain_explanation")
    if not isinstance(original, str) or not original.strip():
        return result  # Do not manufacture a missing policy contract.
    paragraphs, claims = [original], []
    assessments = result.get("claim_assessments")
    for item in assessments[:5] if isinstance(assessments, list) else []:
        if not isinstance(item, dict) or item.get("status") not in LABELS:
            continue
        claim = item.get("claim")
        if not isinstance(claim, str) or not claim.strip() or len(claim) > 5000:
            continue
        entry = {"claim": claim, "status": item["status"], "references": _references(item)}
        claims.append(entry)
        paragraphs.append(f'Trecho enviado: “{claim}”\nResultado para este trecho: {LABELS[item["status"]]}.')
        for reference in entry["references"]:
            if "excerpt" in reference:
                paragraphs.append(f'Trecho citado pela análise: “{reference["excerpt"]}”\nFonte: {reference["url"]}')
            else:
                label = "Fonte consultada" if reference["kind"] == "document" else "Checagem utilizada"
                paragraphs.append(f'{label}: {reference["url"]}')
    if result.get("verdict") != "Scam" and result.get("analysis_status") == "inconclusive":
        paragraphs.extend(_coverage_notes(result))
        paragraphs.append("Notícias relacionadas, títulos de busca e concordância entre respostas de IA não substituem evidências correspondentes. Não compartilhe como confirmado apenas por aparecer em uma busca.")
    if result.get("verdict") == "Scam":
        paragraphs.append("Os sinais de possível golpe não comprovam a identidade do remetente. Confirme pedidos de dinheiro por um canal oficial ou conhecido.")
    result["plain_explanation"] = "\n\n".join(paragraphs)
    result["report_explanation"] = {"version": VERSION, "decision_role": "explanation_only",
                                    "claims": claims, "new_provider_calls": 0}
    return result
