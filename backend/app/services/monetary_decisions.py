"""Closed Copom decision bindings for an explicitly decoded official record.

No HTTP, source vote, historical-rate table or financial recommendation is
implemented here. A claim date can identify only the decision communicated
in the official record with that exact publication-reference date. It is not
an inferred meeting timestamp or a rule for borrowing dates from news pages.
The caller must supply an unmodified visible BODY passage and provenance
produced by ``official_source_body``; this structural validator is not a
signature or proof that arbitrary caller-supplied text came from that API.

The complete claim and formal-decision passage must parse. Only explicitly
closed rationale/compatibility wording is allowed around the decision; an
unknown condition, forecast, extra act, quotation or qualifier abstains.
The caller still owns future-date, context, source and aggregation guards.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Literal

from app.services.official_source_body import (
    COPOM_API_BASE,
    COPOM_INDEX_URL,
    COPOM_REFERENCE_DATE_SEMANTICS,
    COPOM_SCHEMA_URL,
)


Action = Literal["raise", "lower", "hold"]
Relation = Literal["supports", "refutes"]


@dataclass(frozen=True)
class CopomClaim:
    reference_date: str
    action: Action
    previous: Decimal | None
    target: Decimal


@dataclass(frozen=True)
class _Decision:
    action: Action
    previous: Decimal | None
    target: Decimal
    body_date: str | None = None


_MONTHS = {word: index for index, word in enumerate((
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
    "setembro", "outubro", "novembro", "dezembro"), 1)}
_DATE_LITERAL = (r"(?:\d{1,2}\s+de\s+(?:" + "|".join(_MONTHS) + r")\s+de\s+\d{4}"
                 r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})")
# Portuguese commas are decimal separators. A dot with three digits can be
# a Portuguese thousands group, so never silently reinterpret it as 0.001.
_NUMBER = r"(?:0|[1-9]\d{0,2})(?:,\d{1,4}|\.\d{1,2})?"
_SUBJECT = r"o\s+Copom"
_CLAIM_RATE = r"a\s+(?:taxa\s+)?Selic"
_CLAIM = re.compile(
    r"Em\s+(?P<date>" + _DATE_LITERAL + r"),?\s+" + _SUBJECT
    + r"\s+(?P<action>elevou|reduziu|manteve)\s+" + _CLAIM_RATE
    + r"(?P<rates>\s.+?)(?:\.)?", re.I)
_TRANSITION = re.compile(r"de\s+(?P<previous>" + _NUMBER + r")%\s+para\s+(?P<target>"
                         + _NUMBER + r")%(?:\s+ao\s+ano)?", re.I)
_TARGET = re.compile(r"(?P<connector>para|em)\s+(?P<target>" + _NUMBER
                     + r")%(?:\s+ao\s+ano)?", re.I)
_ACTIONS = {"elevou": "raise", "elevar": "raise", "reduziu": "lower", "reduzir": "lower",
            "manteve": "hold", "manter": "hold"}

# This is a closed formal rationale, not arbitrary text before/after the
# first convenient substring. In particular, "se ..." may never be dropped.
_RATIONALE = (r"Considerando\s+a\s+evolução\s+do\s+processo\s+de\s+desinflação,\s+"
              r"os\s+cenários\s+avaliados,\s+o\s+balanço\s+de\s+riscos\s+e\s+"
              r"o\s+amplo\s+conjunto\s+de\s+informações\s+disponíveis,\s+")
_COMPATIBILITY = (r",\s+e\s+entende\s+que\s+essa\s+decisão\s+é\s+compatível\s+com\s+a\s+estratégia\s+"
                  r"de\s+convergência\s+da\s+inflação\s+para\s+(?:o\s+redor\s+da|a)\s+meta\s+"
                  r"ao\s+longo\s+do\s+horizonte\s+relevante")
_FORMAL = re.compile(
    r"(?:Em\s+(?P<date>" + _DATE_LITERAL + r"),\s+)?(?:" + _RATIONALE + r")?"
    + r"o\s+(?:Copom|Comitê\s+de\s+Política\s+Monetária\s+\(Copom\))\s+decidiu"
    + r"(?:,\s+por\s+unanimidade,|\s+por\s+unanimidade)?\s+"
    + r"(?P<action>elevar|reduzir|manter)\s+a\s+(?:taxa\s+básica\s+de\s+juros|(?:taxa\s+)?Selic)"
    + r"(?P<rates>\s.+?)\s+(?:a\.a\.|ao\s+ano)(?:" + _COMPATIBILITY + r")?\.?", re.I)
_FORMAL_DELTA = re.compile(
    r"em\s+(?P<delta>" + _NUMBER + r")\s+(?P<unit>ponto\s+percentual|pontos\s+percentuais),?"
    + r"\s+para\s+(?P<target>" + _NUMBER + r")%", re.I)
_FORMAL_TRANSITION = re.compile(
    r"de\s+(?P<previous>" + _NUMBER + r")%\s+para\s+(?P<target>" + _NUMBER + r")%", re.I)
_FORMAL_TARGET = re.compile(r"(?P<connector>para|em)\s+(?P<target>" + _NUMBER + r")%", re.I)
_PROOF_FIELDS = frozenset({"kind", "record_id", "record_url", "record_reference_date",
                           "reference_date_semantics", "schema_url", "discovery_url"})


def _text(value, maximum):
    return " ".join(value.split()) if isinstance(value, str) and 0 < len(value) <= maximum else None


def _absolute_date(value):
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value).isoformat()
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
            day, month, year = map(int, value.split("/"))
        else:
            parts = value.casefold().split()
            if len(parts) != 5 or parts[1] != "de" or parts[3] != "de" or parts[2] not in _MONTHS:
                return None
            day, month, year = int(parts[0]), _MONTHS[parts[2]], int(parts[4])
        return date(year, month, day).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def _rate(value):
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _consistent(action, previous, target):
    return (previous is None or (action == "raise" and previous < target)
            or (action == "lower" and previous > target) or (action == "hold" and previous == target))


def parse_copom_claim(claim) -> CopomClaim | None:
    """Parse one complete dated historical Copom rate assertion, not advice."""
    text = _text(claim, 1000)
    if text is None or (match := _CLAIM.fullmatch(text)) is None:
        return None
    stamp = _absolute_date(match["date"])
    if stamp is None:
        return None
    action = _ACTIONS[match["action"].casefold()]
    rates = match["rates"].strip()
    if (transition := _TRANSITION.fullmatch(rates)) is not None:
        previous, target = _rate(transition["previous"]), _rate(transition["target"])
        if action == "hold":
            return None  # A maintenance is expressed as "manteve em", not a transition.
    elif (single := _TARGET.fullmatch(rates)) is not None:
        if (single["connector"].casefold() == "em") != (action == "hold"):
            return None
        previous, target = None, _rate(single["target"])
    else:
        return None
    if target is None or not _consistent(action, previous, target):
        return None
    return CopomClaim(stamp, action, previous, target)


def validate_copom_record(record) -> bool:
    """Revalidate canonical official record identity and typed date semantics.

    Dates on arbitrary HTML pages are deliberately outside this interface.
    Neither an official hostname alone nor a compatible title suffices.
    """
    if not isinstance(record, dict) or set(record) != _PROOF_FIELDS:
        return False
    number = record.get("record_id")
    stamp = record.get("record_reference_date")
    if (not isinstance(number, str) or not re.fullmatch(r"[1-9]\d{0,3}", number)
            or not 1 <= int(number) <= 5000 or not isinstance(stamp, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp)
            or _absolute_date(stamp) != stamp):
        return False
    return (record["kind"] == "bcb_copom_comunicado"
            and record["record_url"] == COPOM_API_BASE + "/comunicados_detalhes?nro_reuniao=" + number
            and record["reference_date_semantics"] == COPOM_REFERENCE_DATE_SEMANTICS
            and record["schema_url"] == COPOM_SCHEMA_URL
            and record["discovery_url"] == COPOM_INDEX_URL)


def _formal_decision(quote):
    text = _text(quote, 1800)
    if text is None or (match := _FORMAL.fullmatch(text)) is None:
        return None
    action = _ACTIONS[match["action"].casefold()]
    rates = match["rates"].strip()
    if (delta := _FORMAL_DELTA.fullmatch(rates)) is not None:
        amount, target = _rate(delta["delta"]), _rate(delta["target"])
        if action == "hold" or amount is None or amount <= 0:
            return None
        # Percentual points, not percentage change. This arithmetic is only
        # the inverse of the ONE explicit delta within the SAME decision.
        previous = target - amount if action == "raise" else target + amount
        if previous < 0 or previous >= 1000:
            return None
    elif (transition := _FORMAL_TRANSITION.fullmatch(rates)) is not None:
        previous, target = _rate(transition["previous"]), _rate(transition["target"])
        if action == "hold":
            return None
    elif (single := _FORMAL_TARGET.fullmatch(rates)) is not None:
        if (single["connector"].casefold() == "em") != (action == "hold"):
            return None
        previous, target = None, _rate(single["target"])
    else:
        return None
    body_date = _absolute_date(match["date"]) if match["date"] else None
    if ((match["date"] and body_date is None) or target is None
            or not _consistent(action, previous, target)):
        return None
    return _Decision(action, previous, target, body_date)


def copom_record_relation(claim, quote, proof) -> Relation | None:
    """Compare claim with the exact formal decision communicated by record.

    Different action/target or a different explicitly bound old rate refutes;
    absence of the old rate alone does not. A supporting transition requires
    its old value explicitly or computed from one explicit percentage-point
    delta and target, never from a table, index title or another paragraph.
    """
    left = parse_copom_claim(claim)
    if left is None or not validate_copom_record(proof):
        return None
    if left.reference_date != proof["record_reference_date"]:
        return None
    right = _formal_decision(quote)
    if right is None or (right.body_date is not None and right.body_date != left.reference_date):
        return None
    if left.action != right.action or left.target != right.target:
        return "refutes"
    if left.previous is not None:
        if right.previous is None:
            return None
        if left.previous != right.previous:
            return "refutes"
    return "supports"
