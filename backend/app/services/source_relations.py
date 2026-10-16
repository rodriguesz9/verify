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
    ("event-classification", "caracterizou", "caracterizada", "characterized", "characterised", "classificou", "classified", "declarou", "declared", "decretou"),
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


def opposing_measurements(claim, quote):
    """One explicit same-unit/amount comparison, not arbitrary opposing verbs.

    The caller still binds subject, dates, baseline numbers and model-selected
    literal evidence. Different amounts, Celsius/Fahrenheit or multiple
    measured comparisons cannot establish a deterministic contradiction here.
    """
    def measure(text):
        found = list(_MEASURED_POSITION.finditer(text))
        if len(found) != 1:
            return None
        number, unit, position = found[0].groups()
        return (_decimal(number), "percent" if unit == "%" else "celsius",
                "above" if position.casefold() in {"acima", "above"} else "below")
    left, right = measure(claim), measure(quote)
    return bool(left and right and left[:2] == right[:2] and left[0] is not None and left[2] != right[2])
