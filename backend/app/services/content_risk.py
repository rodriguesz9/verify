"""Risk categories that can support a qualified probably-false assessment."""
import re

from app.core.domain_checker import check_domain_reputation
from app.services.source_registry import source_identity


_RISK_CATEGORIES = (
    ("Alegação alarmista de ameaça coletiva", re.compile(
    r"\b(?:vai|v[aã]o|quer|querem|planeja|planejam|pretende|pretendem|"
    r"est[aá]\s+prestes\s+a)\s+"
    r"(?:matar|assassinar|exterminar|massacrar|eliminar)\b"
    r".{0,100}\b(?:todos|todas|todo\s+o\s+povo|a\s+popula[cç][aã]o|"
    r"os\s+judeus|as\s+crian[cç]as|os\s+brasileiros|milh[oõ]es)\b",
    re.IGNORECASE | re.DOTALL,
    ), "Alegação coletiva alarmante, com potencial de gerar medo ou pânico; intenção não determinada."),
    ("Corrente alarmista ou chamada para viralização", re.compile(
        r"(?:compartilhe|repasse|espalhe|mande\s+para\s+todos).{0,100}"
        r"(?:antes\s+que\s+(?:apaguem|deletem|censurem)|"
        r"a\s+m[ií]dia\s+n[aã]o\s+quer\s+que\s+voc[eê]\s+saiba|"
        r"est[aá]\s+sendo\s+escondid[oa])",
        re.IGNORECASE | re.DOTALL,
    ), "Chamada alarmista para viralizar alegação sem apresentar fonte verificável."),
    ("Alegação de ocultação sem fonte", re.compile(
        r"\b(?:governo|m[ií]dia|imprensa|autoridades|farmac[eê]uticas)\b"
        r".{0,50}\b(?:esconde|escondem|est[aá]\s+escondendo|censura|censuram|"
        r"proibiu\s+a\s+divulga[cç][aã]o)\b",
        re.IGNORECASE | re.DOTALL,
    ), "Atribui ocultação deliberada sem apresentar fonte ou documento verificável."),
)
_NEGATION = re.compile(r"\b(?:n[aã]o|nunca|jamais)\b", re.IGNORECASE)


def classify_unsubstantiated_content(text, report, source_url=None, domain_info=None,
                                     source_attribution=None, search_sources=None):
    """Assess a claim only when its source and content both show risk.

    A domain must be explicitly low reputation (<=40) or unclassified (<=55),
    with no recognized high-reputation match. A category match is also required.
    This does not use search-result absence as evidence or prove author intent.
    """
    if (not isinstance(text, str) or report.get("veracity_status") != "unverified"
            or report.get("verdict") == "Scam"):
        return None
    assessments = report.get("claim_assessments")
    if (not isinstance(assessments, list) or len(assessments) != 1
            or not isinstance(assessments[0], dict) or assessments[0].get("status") != "unverified"):
        return None

    matched_category = next(((name, pattern.search(text), description)
                             for name, pattern, description in _RISK_CATEGORIES
                             if pattern.search(text)), None)
    if not matched_category:
        return None
    category, match, category_description = matched_category
    if _NEGATION.search(text[max(0, match.start() - 50):match.start()]):
        return None

    assessments = []
    if isinstance(source_url, str) and source_url.strip():
        identity = source_identity(source_url)
        if identity and identity.get("source_type") in {"primary", "editorial"}:
            assessments.append((88, "Domínio reconhecido como fonte primária ou editorial"))
        else:
            info = domain_info if isinstance(domain_info, dict) else check_domain_reputation(source_url)
            score = info.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                assessments.append((score, info.get("note") or "Heurística de reputação do domínio"))
    else:
        matches = source_attribution.get("matches", []) if isinstance(source_attribution, dict) else []
        candidates = [item for item in matches if isinstance(item, dict)] if isinstance(matches, list) else []
        if not candidates and isinstance(search_sources, list):
            candidates = [item for item in search_sources if isinstance(item, dict)]
        for item in candidates:
            source_url_candidate = item.get("url") or item.get("link")
            if not isinstance(source_url_candidate, str):
                continue
            identity = source_identity(source_url_candidate)
            assessment = item.get("publisher_assessment")
            curated_level = assessment.get("level") if isinstance(assessment, dict) else None
            if curated_level in {"primary", "editorial"} or (identity and identity.get("source_type") in {"primary", "editorial"}):
                assessments.append((88, "Domínio reconhecido como fonte primária ou editorial"))
                continue
            info = check_domain_reputation(source_url_candidate)
            score = info.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                assessments.append((score, info.get("note") or "Heurística de reputação do domínio"))

    questionable = [item for item in assessments if item[0] <= 55]
    recognized_trusted = [item for item in assessments if item[0] >= 80]
    if not questionable or recognized_trusted:
        return None
    source_assessment = min(questionable, key=lambda item: item[0])
    reputation_level = "baixa" if source_assessment[0] <= 40 else "não classificada"

    explanation = (
        f"A reputação da fonte foi classificada como {reputation_level} ({source_assessment[1]}), "
        f"e o conteúdo corresponde à categoria ‘{category}’. Classificação: provavelmente falsa/sem fundamento. "
        "É uma avaliação de risco combinada, não uma refutação factual nem prova da intenção de quem publicou."
    )
    return {
        "status": "probably_false",
        "category": category,
        "category_description": category_description,
        "source_reputation_score": source_assessment[0],
        "source_reputation_basis": source_assessment[1],
        "basis": f"reputação {reputation_level} da fonte + categoria de risco no conteúdo",
        "explanation": explanation,
    }
