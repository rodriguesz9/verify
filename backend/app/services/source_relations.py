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
    r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(°\s*C|graus?\s+Celsius|degrees?\s+Celsius|%)\s*"
    r"(acima|abaixo|above|below|(?:warmer|colder|higher|lower)\s+than)\b", re.I,
)
_INTERVAL_MEASUREMENT_PREFIX = re.compile(
    r"(?<![\w.,])(?:(?:between|entre|from|de)\s+)?\d+(?:[.,]\d+)?\s*"
    r"(?:(?:°\s*C|graus?\s+Celsius|degrees?\s+Celsius|%)\s*)?"
    r"(?:and|e|to|a|até|ate|para)$", re.I,
)
_QUALIFIED_MEASUREMENT_PREFIX = re.compile(
    r"\b(?:at\s+(?:least|most)|more\s+than|less\s+than|up\s+to|about|approximately|around"
    r"|pelo\s+menos|no\s+m[aá]ximo|no\s+m[ií]nimo|mais\s+de|menos\s+de|at[eé]"
    r"|cerca\s+de|aproximadamente)$", re.I,
)
_REFERENCE_RANGE = r"((?:18|19|20)\d{2})\s*[-–—]\s*((?:18|19|20)\d{2})\b"
_LOCAL_REFERENCE_RANGE = re.compile(r"\b" + _REFERENCE_RANGE)
_LOCAL_BASELINES = tuple(re.compile(pattern, re.I) for pattern in (
    # The comparison owns an immediately adjacent reference complement.
    # Arbitrary later clauses cannot lend their period to this measurement.
    r"^\s+(?:the\s+)?" + _REFERENCE_RANGE
        + r"\s+(?:(?:surface\s+air\s+)?temperature\s+)?(?:average|mean|baseline|reference(?:\s+period)?)\b",
    r"^\s+(?:the\s+)?(?:(?:surface\s+air\s+)?temperature\s+)?"
        r"(?:average|mean|baseline|reference\s+period)(?:\s+(?:of|for|from|over|during|de))?\s+"
        + _REFERENCE_RANGE,
    r"^\s+(?:(?:da|do|a|ao|à|de)\s+)?"
        r"(?:m[eé]dia|temperatura\s+m[eé]dia|n[ií]vel|per[ií]odo(?:\s+de\s+refer[eê]ncia)?)"
        r"(?:\s+(?:do\s+per[ií]odo|de|do|da|para|entre))?\s+" + _REFERENCE_RANGE,
))
_REFERENCE_COORDINATION = re.compile(
    r"^\s*(?:,\s*(?:(?:and|or|e\s+também|e|ou)\s+)?|(?:as\s+well\s+as|e\s+também|and|or|e|ou)\s+|/\s*)", re.I,
)


def _coordinated_baseline(tail):
    coordination = _REFERENCE_COORDINATION.match(tail)
    if coordination is None:
        return False
    following = tail[coordination.end():].lstrip()
    # A coordinated complement can omit the repeated word "average":
    # "average for X and for Y" / "média de X e de Y" still name two
    # references. Strip only a leading complement preposition/article;
    # an explicit independent subject ("another series uses Y") stays intact.
    bare = re.sub(r"^(?:for|of|from|over|during|de|para|entre)\s+",
                  "", following, count=1, flags=re.I)
    bare = re.sub(r"^(?:the|a|an)\s+", "", bare, count=1, flags=re.I)
    return bool(_LOCAL_REFERENCE_RANGE.match(bare) or any(
        pattern.match(" " + following) for pattern in _LOCAL_BASELINES))


def _local_baseline(tail):
    for pattern in _LOCAL_BASELINES:
        match = pattern.match(tail)
        if match is not None:
            first, last = match.groups()
            return {(first, last)} if first < last and not _coordinated_baseline(tail[match.end():]) else None
    # None marks a literal range with unknown ownership; an empty set means
    # no explicit range was stated. Do not let an unparsed claimed reference
    # disappear from the support/refutation comparison.
    return None if _LOCAL_REFERENCE_RANGE.search(tail) else set()


def _ambiguous_measurement_prefix(text, start):
    # These helpers support an unsigned scalar only. A sign, uncertainty,
    # dash or interval endpoint must not silently become its positive amount.
    # A dash immediately before the value can also be punctuation; abstain
    # rather than guess whether it is a minus sign or a sentence separator.
    prefix = text[:start].rstrip()
    return bool(prefix and (prefix[-1] in "+-−±–—"
                           or _INTERVAL_MEASUREMENT_PREFIX.search(prefix)
                           or _QUALIFIED_MEASUREMENT_PREFIX.search(prefix)))


def _has_ambiguous_measurement(text, identities=None):
    return any(_ambiguous_measurement_prefix(text, match.start())
               and (identities is None or (_decimal(match[1]), "percent" if match[2] == "%" else "celsius") in identities)
               for match in _MEASURED_POSITION.finditer(text))


def _measured_comparisons(text):
    result = []
    matches = list(_MEASURED_POSITION.finditer(text))
    for index, match in enumerate(matches):
        if _ambiguous_measurement_prefix(text, match.start()):
            continue
        number, unit, position = match.groups()
        # A stated baseline belongs to THIS measured comparison, not a
        # different amount elsewhere in a paragraph. Keep the whole local
        # clause; a matching numeric range elsewhere cannot repair it.
        # A following measured comparison owns its own baseline, even when
        # both occur before a sentence-ending full stop. Do not borrow the
        # second metric's reference range for the first one.
        end = min(match.end() + 180, matches[index + 1].start() if index + 1 < len(matches) else len(text))
        tail = re.split(r"[.!?;]", text[match.end():end], maxsplit=1)[0]
        ranges = _local_baseline(tail)
        above = position.casefold() in {"acima", "above"} or bool(re.fullmatch(r"(?:warmer|higher)\s+than", position, re.I))
        result.append((_decimal(number), "percent" if unit == "%" else "celsius",
            "above" if above else "below", ranges))
    return result


def supporting_measurements_bound(claim, quote):
    """Extra support guard for an explicit amount/unit/direction + baseline.

    No new inference when this narrow construction is absent. When present,
    each claimed baseline must belong to the uniquely matching measured
    value, not another metric elsewhere in the same body window.
    """
    claimed = _measured_comparisons(claim)
    if (any(value[3] is None for value in claimed) or _has_ambiguous_measurement(claim)
            or _has_ambiguous_measurement(quote, {value[:2] for value in claimed})):
        return False
    bounded = [value for value in claimed if value[3]]
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
    candidates for the matching amount/unit cannot establish a deterministic
    contradiction here. A named reference without its literal range is not
    expanded from background knowledge.
    """
    left = _measured_comparisons(claim)
    if (len(left) != 1 or left[0][0] is None or left[0][3] is None or _has_ambiguous_measurement(claim)
            or _has_ambiguous_measurement(quote, {left[0][:2]})):
        return False
    # Other metrics in the same body window no longer mask a unique matching
    # amount/unit/baseline. Duplicate matching metrics remain ambiguous.
    observed = _measured_comparisons(quote)
    matches = [right for right in observed if right[:2] == left[0][:2]]
    return (len(matches) == 1 and left[0][2] != matches[0][2]
            and all(right[2] == matches[0][2] for right in observed)
            and left[0][3] == matches[0][3])
