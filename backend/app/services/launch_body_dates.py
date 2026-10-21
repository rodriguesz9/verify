"""Literal passive-launch body dates, never a date inferred from a URL/title.

This deliberately small PT grammar only connects one completed passive launch
to an immediately attached relative weekday/day. Publication must come from
the caller's explicit publication metadata. It does not identify who owns an
instrument, certify a source, compare claimed dates or decide a verdict.
"""
from datetime import date
import re


_WEEKDAYS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
_OUT_OF_SCOPE = re.compile(
    r"\b(?:não|nao|nunca|jamais|nem|talvez|poderia|previst[oa]|planejad[oa]|supostamente|"
    r"aleg[ao]u?|afirm[ao]u?|anunciou|informou|divulgou|disse|fals[oa]|boato|rumor|"
    r"decolou|pousou|aterrissou|partiu|chegou|entrou|colidiu|morreu|nasceu|cancelou|adiou)\b", re.I,
)
_PROPER_WORD = r"(?:[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+|[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]{2,})"
_PROPER_NAME = _PROPER_WORD + r"(?:\s+(?:(?:de|da|do|dos|das)\s+)?" + _PROPER_WORD + r"){0,5}"
_FLIGHT_NAME = _PROPER_NAME + r"(?:\s+[1-9]\d?)?"
_INSTRUMENT = r"(?i:telescópio(?:\s+espacial)?|missão|nave|sonda|foguete|satélite|espaçonave)"
_AGENCY = _PROPER_NAME + r"(?:\s+\([A-Z]{2,8}\))?"
_RELATIVE = (
    r"(?:(?i:n[ae]\s+manhã|na\s+tarde|na\s+noite)\s+(?i:dest[ae])|(?i:nest[ae]))\s+"
    r"(?P<weekday>" + "|".join(_WEEKDAYS) + r")\s*"
    r"\((?P<day>\d{1,2})(?:/(?P<month>\d{1,2}))?\)"
)
_LOCATION = (
    r"(?:(?i:a partir de uma base da)\s+" + _AGENCY + r"\s+(?i:na|no|em)\s+" + _PROPER_NAME
    + r"|(?i:na|no|em|da|do|de)\s+" + _PROPER_NAME + r")"
)
_FRAME = re.compile(
    r"^\s*(?:(?P<intro_agency>" + _AGENCY + r")\s+(?i:lança com sucesso)\s+"
    + _INSTRUMENT + r"\s+(?P<intro_name>" + _FLIGHT_NAME + r")\s+)?"
    r"(?:(?i:Em uma missão histórica),\s+)?"
    r"(?:(?i:o|a)\s+)?(?P<instrument>" + _INSTRUMENT + r")\s+(?P<name>" + _FLIGHT_NAME + r")\s+"
    r"(?i:foi lançad[oa])\s+(?:(?i:pel[oa])\s+" + _AGENCY + r"\s+)?"
    r"(?P<expression>" + _RELATIVE + r")"
    r"(?:\s+" + _LOCATION + r")?\s*\.?\s*$"
)
_MONTH = r"(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
_ABSOLUTE = r"(?:\d{1,2}\s+de\s+" + _MONTH + r"\s+de\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"
_DATE_ONLY_CLAIM = re.compile(
    r"(?i:[oa])\s+(?P<instrument>" + _INSTRUMENT + r")\s+(?P<name>" + _FLIGHT_NAME
    + r")\s+(?i:foi lançad[oa] em)\s+(?i:" + _ABSOLUTE + r")\.?"
)


def launch_date_claim_matches_body(claim, quote):
    """Restrict relative-date support to the same named, date-only claim.

    No agency, launch site, time-of-day, success or other claimed qualifier
    may disappear during normalization of the source's relative expression.
    A calendar/chronology and support/refutation comparison still runs later.
    """
    if not isinstance(claim, str) or not isinstance(quote, str):
        return False
    left, right = _DATE_ONLY_CLAIM.fullmatch(claim.strip()), _FRAME.fullmatch(quote)
    if left is None or right is None or _OUT_OF_SCOPE.search(claim):
        return False
    if " ".join(left["name"].casefold().split()) != " ".join(right["name"].casefold().split()):
        return False
    instrument, actual = left["instrument"].casefold(), right["instrument"].casefold()
    return instrument == actual or (instrument == "telescópio" and actual == "telescópio espacial")


def launch_body_temporal_anchor(quote, publication_date):
    """Return a revalidatable date link for one complete literal body frame.

    Unrecognized qualifiers/actions abstain; they are never deleted to make a
    match. One optional present-tense introductory launch label is accepted
    only when it repeats the same named object as the completed body clause.
    Weekday, day and any stated month must agree with publication metadata.
    The caller still enforces retrieval chronology and every factual guard.
    """
    if (not isinstance(quote, str) or not 20 <= len(quote) <= 1200
            or not isinstance(publication_date, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", publication_date)):
        return None
    try:
        published = date.fromisoformat(publication_date)
    except ValueError:
        return None
    if _OUT_OF_SCOPE.search(quote):
        return None
    match = _FRAME.fullmatch(quote)
    if match is None:
        return None
    if (match["intro_name"] and " ".join(match["intro_name"].casefold().split())
            != " ".join(match["name"].casefold().split())):
        return None
    if (int(match["day"]) != published.day
            or match["month"] and int(match["month"]) != published.month
            or match["weekday"].casefold() != _WEEKDAYS[published.weekday()]):
        return None
    return {"kind": "explicit_launch_body_date", "expression": match["expression"],
            "publication_date": publication_date}
