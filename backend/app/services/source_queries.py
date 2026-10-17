"""Neutral retrieval leads. Never replacement claims or factual evidence.

Literal queries are tried first. Recovery keeps names, topic words and years,
without requiring a disputed amount, day or polarity to appear in a result.
No model, network, fixed answer or per-example URL is used here.
"""
import re
from app.services.source_relations import lexical_text, WORD_GROUPS

_STOP = set("a o as os um uma uns umas de da do das dos em no na nos nas e ou que se ao aos com como para por foi são era é ser tem teve segundo informou disse sobre até após entre ainda já mais menos seu sua seus suas ele ela eles elas este esta isso isto divulgação relatório relação the of in on at and was is were has had to by her his it its an as from".split())
_CALENDAR = set("janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro january february march april may june july august september october november december jan feb mar apr jun jul aug sep sept oct nov dec".split())
_DISPUTED = set("não nao nunca jamais nem not never abaixo acima above below aumentou reduziu elevou diminuiu subiu caiu cresceu diminuição aumento redução higher lower increased decreased raised lowered".split())


def _discovery_subject(text):
    # Report dates and reference periods are different fields. The literal
    # first search retains both; recovery focuses on the reported subject so
    # a publication in 2025 about GDP in 2024 does not rank only GDP in 2025.
    date = r"\d{1,2}\s+de\s+(?:" + "|".join(_CALENDAR) + r")\s+de\s+\d{4}"
    release = re.match(r"^Na divulgação de\s+" + date + r",\s*(.+)$", text, re.I)
    if release:
        return release[1]
    report = re.match(r"^Segundo o relatório d[oa]\s+(.{2,50}?)\s+de\s+" + date + r",\s*(.+)$", text, re.I)
    return report[1] + " " + report[2] if report else text


def neutral_source_query(text, *, preserve_period=False):
    if not isinstance(text, str) or not 20 <= len(text.strip()) <= 500:
        return None
    text = _discovery_subject(text)
    words = re.findall(r"[^\W\d_]+(?:-\d+)?|\b(?:18|19|20)\d{2}\b", text, re.UNICODE)
    # Stop words are dropped only from a discovery query. The original claim
    # remains untouched, including negation, every number and every date.
    omitted = _STOP | _DISPUTED | (set() if preserve_period else _CALENDAR)
    eligible = [word for word in words if len(word) >= 3 and word.casefold() not in omitted]
    names = [word for word in eligible if word[0].isupper()]
    topics = [word for word in eligible if not word[0].isupper() and not word.isdigit()]
    years = [word for word in eligible if word.isdigit()]
    ordered = list(dict.fromkeys([*names, *topics, *years]))
    # Do not silently drop a final entity/qualifier to meet a provider limit.
    # If a neutral query cannot fit as a whole, keep the existing literal plan.
    if not 2 <= len(ordered) <= 24:
        return None
    query = " ".join(ordered)
    return query if len(query) <= 240 else None


def primary_source_query(text):
    """Small explicit vocabulary bridge for English primary publications.

    No generated facts: only known identity aliases and translated topic words.
    Dates/amounts/polarity remain in the untouched original claim, never inferred
    from this discovery lead. Unknown words/names remain literal.
    """
    if not isinstance(text, str) or not 20 <= len(text.strip()) <= 500:
        return None
    # Brazilian statistical/monetary releases are normally written in PT.
    # Translating PIB/crescimento to GDP/growth ranked English mirrors and
    # unrelated later releases. The original period discriminates recurring
    # releases; it is a discovery anchor, never evidence that the date is true.
    if re.search(r"\b(?:IBGE|Copom|Banco Central)\b", text, re.I):
        return neutral_source_query(text, preserve_period=True)
    translated = lexical_text(text)
    names = {"event-impact": "impact", "event-classification": "classification"}
    for group in WORD_GROUPS:
        canonical = names.get(group[0], group[0])
        translated = re.sub(r"\b(?:" + "|".join(re.escape(word) for word in group[1:]) + r")\b",
                            canonical, translated, flags=re.I)
    return neutral_source_query(translated)


def primary_source_filter(text, default):
    # Route a named institution to its public corpus. This is not a truth
    # assertion: its actual body still has to be retrieved and cross-checked.
    canonical = lexical_text(text)
    targets = []
    for pattern, domain in ((r"\bWHO\b", "who.int"), (r"\bNASA\b", "nasa.gov"),
                            (r"\bIBGE\b", "ibge.gov.br"), (r"\b(?:Copom|Banco Central)\b", "bcb.gov.br"),
                            (r"\bCopernicus\b", "copernicus.eu")):
        if re.search(pattern, canonical, re.I):
            targets.append("site:" + domain)
    return "(" + " OR ".join(targets) + ")" if targets else default
