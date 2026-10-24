"""Neutral retrieval leads. Never replacement claims or factual evidence.

Literal queries are tried first. Recovery keeps names, topic words and years,
without requiring a disputed amount, day or polarity to appear in a result.
No model, network, fixed answer or per-example URL is used here.
"""
import re
import unicodedata
from app.services.source_relations import lexical_text, WORD_GROUPS

_STOP = set("a o as os um uma uns umas de da do das dos em no na nos nas e ou que se ao aos com como para por foi são era é ser tem teve segundo informou disse sobre até após entre ainda já mais menos seu sua seus suas ele ela eles elas este esta isso isto divulgação relatório relação the of in on at and was is were has had to by her his it its an as from".split())
_CALENDAR = set("janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro january february march april may june july august september october november december jan feb mar apr jun jul aug sep sept oct nov dec".split())
_DISPUTED = set("não nao nunca jamais nem not never abaixo acima above below aumentou reduziu elevou diminuiu subiu caiu cresceu diminuição aumento redução higher lower increased decreased raised lowered".split())


def discovery_topic_tokens(text):
    """Known bilingual topic aliases for ranking discovery leads only.

    The evidence reader already knows these lexical bindings. Comparing raw
    Portuguese words against an English title discarded them at the queue
    boundary and could prefer a generic dashboard from the same publisher.
    Do not add dates, translate unknown entities, or decide factual relations.
    Dates/polarity are deliberately not topic-ranking anchors; the original
    assertion still reaches the unchanged body/date/negation guards.
    """
    if not isinstance(text, str):
        return set()
    canonical = lexical_text(text)
    for group in WORD_GROUPS:
        canonical = re.sub(r"\b(?:" + "|".join(map(re.escape, group[1:])) + r")\b",
                           group[0], canonical, flags=re.I)
    fold = lambda value: "".join(char for char in unicodedata.normalize("NFD", value.casefold())
                                 if not unicodedata.combining(char))
    excluded = {fold(word) for word in _STOP | _DISPUTED | _CALENDAR}
    # URL paths commonly use hyphens for spaces. Do not combine a whole slug
    # into one identity, but retain numbered names (Zeta-31, not Zeta + 31)
    # and the two internal event aliases. Numeric ranges are not topic words.
    words = re.findall(r"event-(?:impact|classification)\b|[^\W_]+(?:-[^\W_]*\d[^\W_]*)?",
                       canonical, re.UNICODE | re.I)
    return {fold(word) for word in words
            if len(word) >= 3 and any(char.isalpha() for char in word) and fold(word) not in excluded}


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


def discovery_target_years(text):
    """Separate one measured year from its explicitly named comparison year.

    Discovery only: the complete claim, including its baseline, still reaches
    every evidence guard. No earlier/later year is inferred from a number or
    from chronology. Ambiguous constructions preserve all literal years.
    """
    subject = _discovery_subject(text)
    year = r"(?:18|19|20)\d{2}"
    years = set(re.findall(r"\b" + year + r"\b", subject))
    pairs = list(re.finditer(
        r"\b(?:em|in)\s+(" + year + r")\s+"
        r"(?:em relação a|na comparação com|comparado com|comparada com|compared with|compared to)"
        r"\s+(" + year + r")\b", subject, re.I,
    ))
    if len(pairs) == 1 and years == {pairs[0][1], pairs[0][2]}:
        return {pairs[0][1]}
    return years


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
    target_years = discovery_target_years(text)
    years = [word for word in eligible if word.isdigit() and word in target_years]
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


def primary_source_filter(text, default=""):
    """Route explicit institutions; leave unknown subjects open by default.

    A fixed collection of institutional sites is not a primary corpus for an
    unrelated subject. An empty filter lets the existing bounded search find
    candidates without assigning them authority: accepted bodies still pass
    the same source identity, family and evidence guards. Callers that need a
    deliberate fallback can supply it explicitly.
    """
    canonical = lexical_text(text)
    targets = []
    for pattern, domain in ((r"\bWHO\b", "who.int"), (r"\bNASA\b", "nasa.gov"),
                            (r"\bIBGE\b", "ibge.gov.br"), (r"\b(?:Copom|Banco Central)\b", "bcb.gov.br"),
                            (r"\bCopernicus\b", "copernicus.eu")):
        if re.search(pattern, canonical, re.I):
            targets.append("site:" + domain)
    return "(" + " OR ".join(targets) + ")" if targets else default


def editorial_source_query(text):
    """Diversify one existing recovery slot, not the factual assertion.

    The first literal query already searches in Portuguese. For an explicitly
    named international institution and a known translated topic, the second
    editorial slot can search English reporting instead of repeating only PT
    mirrors. Domestic/unknown institutions keep the original native recovery.
    No date, result or entity is added; the caller owns filters and request cap.
    """
    native = neutral_source_query(text, preserve_period=True)
    if not isinstance(text, str) or native is None:
        return native, "pt-br"
    canonical = lexical_text(text)
    if (not re.search(r"\b(?:NASA|WHO|Copernicus)\b", canonical, re.I)
            or re.search(r"\b(?:IBGE|Copom|Banco Central)\b", canonical, re.I)):
        return native, "pt-br"
    # Without a recognized vocabulary bridge an English locale is a guess,
    # not a useful language diversification. Keep names and unknown prose.
    if not any(re.search(r"\b(?:" + "|".join(map(re.escape, group[1:])) + r")\b", canonical, re.I)
               for group in WORD_GROUPS):
        return native, "pt-br"
    translated = primary_source_query(text)
    return (translated, "en") if translated else (native, "pt-br")
