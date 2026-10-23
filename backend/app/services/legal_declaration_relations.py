"""Literal numbered-article declarations, never legal effects or source trust.

Only complete closed statements are parsed. The caller still owns BODY
provenance, original-record validation, context guards and source aggregation.
An internally consistent article anchor is necessary, not proof of provenance.
"""
from dataclasses import dataclass
from datetime import date
import re
import unicodedata


_MAX_CHARACTERS = 1200
_MONTHS = {name: index for index, name in enumerate(
    "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split(), 1)}
_LAW_NUMBER = r"\d{1,6}(?:\.\d{3})*"
_LAW_DATE = r"\d{1,2}\s+de\s+(?:" + "|".join(_MONTHS) + r")\s+de\s+\d{4}"
_LAW = r"lei\s+(?:n[º°.]?\s*)?(?P<law_number>" + _LAW_NUMBER + r"),?\s+de\s+(?P<law_date>" + _LAW_DATE + r")"
_REFERENCE = re.compile(_LAW, re.I)
_CLAIM = re.compile(
    r"(?:o\s+)?artigo\s+(?P<article>\d{1,3})[º°o]?\s+da\s+"
    + _LAW + r",\s+(?P<negative>não\s+)?declarou\s+(?:legalmente\s+)?(?P<payload>.+)", re.I)
_ARTICLE = re.compile(
    r"(?:art(?:igo)?\.?\s*(?P<article>\d{1,3})[º°o]?|(?P<bare_article>\d{1,3})[º°])\s+"
    r"(?:(?:é|foi|fica)\s+declarad[oa]|declara-se)\s+(?P<payload>.+)", re.I)
_SAME_LAW_DATE = re.compile(
    r"(?P<state>extint[ao]|extinct[ao])(?:\s*,\s*|\s+)desde\s+a\s+data\s+"
    r"(?:desta|d['’]esta)\s+lei,\s*(?P<object>.+)", re.I)
_UNSAFE_SCOPE = re.compile(
    r"\b(?:não|nao|nunca|jamais|nem|not|never|se|caso|salvo|exceto|except|unless|"
    r"talvez|possivelmente|hipot[ée]tic[oa]|fict[íi]ci[oa]|simulad[oa]|"
    r"apenas|somente|exclusivamente|desde|até|enquanto|quando|"
    r"mas|porém|contudo|entretanto|que|e|ou)\b|\ba\s+partir\s+de\b", re.I)
_PAYLOAD_PUNCTUATION = re.compile(r"[,.!?;:\"'“”«»()\[\]{}]")


@dataclass(frozen=True)
class LegalDeclarationClaim:
    law_number: str
    law_date: str
    article_number: str
    negative: bool
    payload: str
    effective_scope: str | None = None


@dataclass(frozen=True)
class LegalArticleDeclaration:
    article_number: str
    payload: str
    effective_scope: str | None = None


def _statement(text):
    if not isinstance(text, str) or not 20 <= len(text) <= _MAX_CHARACTERS:
        return None
    text = " ".join(unicodedata.normalize("NFC", text).split())
    return text[:-1].rstrip() if text.endswith(".") else text


def _law_identity(match):
    calendar = re.fullmatch(r"(\d{1,2})\s+de\s+([^ ]+)\s+de\s+(\d{4})", match["law_date"], re.I)
    number = match["law_number"].replace(".", "")
    if calendar is None or int(number) == 0:
        return None
    try:
        day = date(int(calendar[3]), _MONTHS[calendar[2].casefold()], int(calendar[1])).isoformat()
    except (ValueError, KeyError):
        return None
    return {"law_number": number, "law_date": day}


def _payload(text):
    scope = None
    dated = _SAME_LAW_DATE.fullmatch(text)
    if dated:
        # This records the literal modifier of the declaration. It does not
        # infer legal validity, practical effects or an unmentioned date.
        scope = "same_law_date"
        text = dated["state"] + " " + dated["object"]
    if _UNSAFE_SCOPE.search(text) or _PAYLOAD_PUNCTUATION.search(text):
        return None
    text = text.casefold()
    text = re.sub(r"\bextinct([ao])\b", r"extint\1", text)
    text = re.sub(r"\bbrazil\b", "brasil", text)
    # One declared state and its complete object. Unknown multi-clause or
    # multiword predicates stay on the ordinary comparison path.
    if re.fullmatch(r"[^\W\d_]+\s+(?:a|o|as|os)\s+[^\W_].+", text, re.UNICODE) is None:
        return None
    return text, scope


def parse_legal_declaration_claim(text):
    """Parse one literal attribution to a complete law/article identity."""
    text = _statement(text)
    match = _CLAIM.fullmatch(text) if text else None
    if match is None or int(match["article"]) == 0:
        return None
    identity, payload = _law_identity(match), _payload(match["payload"])
    if identity is None or payload is None:
        return None
    return LegalDeclarationClaim(**identity, article_number=str(int(match["article"])),
                                 negative=bool(match["negative"]), payload=payload[0], effective_scope=payload[1])


def parse_legal_article_declaration(quote):
    """Parse one positive numbered BODY declaration, without source inference."""
    quote = _statement(quote)
    match = _ARTICLE.fullmatch(quote) if quote else None
    article = (match["article"] or match["bare_article"]) if match else None
    if article is None or int(article) == 0:
        return None
    payload = _payload(match["payload"])
    if payload is None:
        return None
    return LegalArticleDeclaration(str(int(article)), payload[0], payload[1])


def legal_declaration_has_unsafe_scope(quote):
    """Veto explicit ambiguous scope, not every unsupported writing style.

    False only permits ordinary guarded model review. It supplies no literal
    support/refutation. Known closed frames are parsed separately by caller.
    """
    text = _statement(quote)
    if text is None:
        return True
    text = re.sub(r"^(?:art(?:igo)?\.?\s*\d{1,3}[º°o]?|\d{1,3}[º°])\s+", "", text, count=1, flags=re.I)
    return bool(_UNSAFE_SCOPE.search(text) or _PAYLOAD_PUNCTUATION.search(text))


def legal_declaration_relation(claim, quote, anchor):
    """Return a literal relation; context/provenance guards must still run."""
    claimed = parse_legal_declaration_claim(claim)
    observed = parse_legal_article_declaration(quote)
    if (claimed is None or observed is None or not isinstance(anchor, dict)
            or set(anchor) != {"kind", "law_number", "law_date", "article_number", "reference"}
            or not isinstance(anchor.get("reference"), str)):
        return None
    reference = _REFERENCE.fullmatch(anchor["reference"].strip())
    identity = _law_identity(reference) if reference else None
    if identity is None or anchor != {"kind": "explicit_numbered_legal_article", **identity,
                                     "article_number": observed.article_number, "reference": anchor["reference"]}:
        return None
    if (identity != {"law_number": claimed.law_number, "law_date": claimed.law_date}
            or claimed.article_number != observed.article_number or claimed.payload != observed.payload
            or claimed.effective_scope is not None and claimed.effective_scope != observed.effective_scope):
        return None
    return "refutes" if claimed.negative else "supports"
