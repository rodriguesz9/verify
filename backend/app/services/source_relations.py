"""Small explicit linguistic bindings, never truth labels or model answers."""
import re
from decimal import Decimal, InvalidOperation

_ORGANIZATIONS = (
    (re.compile(r"\b(?:organiza[çc][ãa]o mundial (?:da|de) sa[úu]de|world health organi[sz]ation|OMS|WHO)\b", re.I), "WHO"),
    (re.compile(r"\b(?:instituto brasileiro de geografia e estat[íi]stica|IBGE)\b", re.I), "IBGE"),
)

WORD_GROUPS = (
    ("spacecraft", "spacecraft", "nave", "sonda", "espaçonave"),
    ("asteroid", "asteroid", "asteroide", "asteróide"),
    ("event-impact", "impact", "impacted", "collision", "collided", "crashed", "smashed", "colidiu", "colisão", "impacto", "atingiu"),
    ("intentional", "intentional", "intentionally", "intencional", "intencionalmente", "purposely", "deliberately"),
    ("pandemic", "pandemia", "pandemic"),
    ("event-classification", "caracterizou", "caracterizada", "caracterizado", "characterized", "characterised", "classificou", "classified", "declarou", "declared", "decretou"),
    ("gdp", "pib", "gdp"),
    ("growth", "cresceu", "crescimento", "grew", "growth"),
    ("average", "média", "average"),
    ("temperature", "temperatura", "temperature"),
)


def lexical_text(text):
    for pattern, canonical in _ORGANIZATIONS:
        text = pattern.sub(canonical, text)
    # Temperature symbols are units, not Roman-numeral names ("C").
    for symbol, name in (("C", "celsius"), ("F", "fahrenheit")):
        text = re.sub(r"°\s*" + symbol + r"\b|\b(?:graus?|degrees?)\s+" + name + r"\b", name, text, flags=re.I)
    return text


def _direction(text, up, down):
    directions = set()
    if re.search(up, text, re.I):
        directions.add("up")
    if re.search(down, text, re.I):
        directions.add("down")
    return next(iter(directions)) if len(directions) == 1 else None


def opposing_directions(claim, quote):
    # Contradiction still needs matching subject, event/date, amounts and units
    # in the caller. Multiple/opposing verbs in one sentence remain ambiguous.
    pairs = (
        (r"\b(?:acima|above|warmer|higher)\b", r"\b(?:abaixo|below|colder|lower)\b"),
        (r"\b(?:aumentou|elevou|subiu|raised|increased)\b", r"\b(?:reduziu|diminuiu|caiu|lowered|decreased|reduced)\b"),
    )
    return any((left := _direction(claim, up, down)) is not None
               and (right := _direction(quote, up, down)) is not None and left != right for up, down in pairs)


def _decimal(value):
    if "," in value and "." in value:
        decimal = "," if value.rfind(",") > value.rfind(".") else "."
        value = value.replace("." if decimal == "," else ",", "").replace(",", ".")
    else:
        value = value.replace(",", ".")
    try:
        return Decimal(value).normalize()
    except InvalidOperation:
        return None


_TRANSITION = re.compile(r"\b(?:de|from)\s+(\d+(?:[.,]\d+)?)\s*%\s+(?:para|to)\s+(\d+(?:[.,]\d+)?)\s*%", re.I)


def percentage_transition(text):
    # Exactly one explicit, unit-bound transition; never bags of numbers.
    matches = list(_TRANSITION.finditer(text))
    if len(matches) != 1:
        return None
    pair = tuple(_decimal(value) for value in matches[0].groups())
    return pair if all(value is not None for value in pair) else None


_MEASURED_POSITION = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(°\s*C|graus?\s+Celsius|degrees?\s+Celsius|%)\s*"
    r"(acima|abaixo|above|below)\b", re.I,
)


def _measured_comparisons(text):
    result = []
    for match in _MEASURED_POSITION.finditer(text):
        number, unit, position = match.groups()
        # A stated baseline belongs to THIS measured comparison, not a
        # different amount elsewhere in a paragraph. Keep the whole local
        # clause; a matching numeric range elsewhere cannot repair it.
        tail = re.split(r"[.!?;]", text[match.end():match.end() + 180], maxsplit=1)[0]
        ranges = set(re.findall(r"\b((?:18|19|20)\d{2})\s*[-–—]\s*((?:18|19|20)\d{2})\b", tail))
        result.append((_decimal(number), "percent" if unit == "%" else "celsius",
            "above" if position.casefold() in {"acima", "above"} else "below", ranges))
    return result


def supporting_measurements_bound(claim, quote):
    """Extra support guard for an explicit amount/unit/direction + baseline.

    No new inference when this narrow construction is absent. When present,
    each claimed baseline must belong to the uniquely matching measured
    value, not another metric elsewhere in the same body window.
    """
    bounded = [value for value in _measured_comparisons(claim) if value[3]]
    observed = _measured_comparisons(quote)
    for left in bounded:
        matches = [right for right in observed if right[:2] == left[:2]]
        if left[0] is None or len(left[3]) != 1 or len(matches) != 1 or matches[0] != left:
            return False
    return True


def opposing_measurements(claim, quote):
    """One explicit same-unit/amount comparison, not arbitrary opposing verbs.

    The caller still binds subject, dates, baseline numbers and model-selected
    literal evidence. Different amounts, Celsius/Fahrenheit or multiple
    measured comparisons cannot establish a deterministic contradiction here.
    """
    left = _measured_comparisons(claim)
    if len(left) != 1 or left[0][0] is None:
        return False
    # Other metrics in the same body window no longer mask a unique matching
    # amount/unit/baseline. Duplicate matching metrics remain ambiguous.
    observed = _measured_comparisons(quote)
    matches = [right for right in observed if right[:2] == left[0][:2]]
    return (len(matches) == 1 and left[0][2] != matches[0][2]
            and all(right[2] == matches[0][2] for right in observed)
            and left[0][3] == matches[0][3])
