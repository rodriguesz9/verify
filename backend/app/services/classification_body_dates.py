"""Explicit classification/date bindings in consecutive literal BODY text.

This is a small grammar, not an event database or a truth decision. A complete
simple claim can match one dated classification in a coordinated sentence.
Every other clause, date, antecedent and contextual word stays in the proof.
Unknown grammar, qualifiers, subjects or polarity abstain. No URL, headline,
publication metadata or organization-specific event knowledge is consulted.
"""
from datetime import date
import re

from app.services.source_relations import lexical_text


_MONTHS = {name: number for number, names in enumerate((
    "janeiro january jan", "fevereiro february feb", "março march mar",
    "abril april apr", "maio may", "junho june jun", "julho july jul",
    "agosto august aug", "setembro september sep sept", "outubro october oct",
    "novembro november nov", "dezembro december dec",
), 1) for name in names.split()}
_MONTH = "(?i:" + "|".join(_MONTHS) + ")"
_DATE = (r"(?:\d{1,2}\s+(?:de\s+)?" + _MONTH + r"\.?\s+(?:de\s+)?\d{4}"
         r"|" + _MONTH + r"\.?\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}"
         r"|\d{1,2}/\d{1,2}/\d{4})")
_WORD = r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[-’'][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)*"
_WORDS = _WORD + r"(?:\s+" + _WORD + r"){0,11}?"
_SUBJECT = _WORDS + r"(?:\s+\([A-Za-z][A-Za-z0-9-]{1,15}\))?"
_PROPER = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9-]*"
_ACTOR = _PROPER + r"(?:\s+(?:(?:de|da|do|das|dos|of|the)\s+)?" + _PROPER + r"){0,7}(?:\s+\([A-Z]{2,8}\))?"
_LABEL = _WORDS + r"(?:\s+\([A-Z]{2,12}\))?"
_DIRECT_ACTION = r"(?:caracterizou|classificou|characterized|characterised|classified)"
_INFINITIVE = r"(?:caracterizar|classificar|characterize|characterise|classify)"
_UNSAFE = re.compile(
    r"\b(?:não|nao|nunca|jamais|nem|not|never|neither|denied|negou|nega|"
    r"fals[oa]s?|false|boato|rumou?r|supost[oa]s?|alleged|alega|alegou|"
    r"talvez|poderia|pode|might|could|possibly|will|planned|planejad[oa]|"
    r"fic[çc][ãa]o|fict[íi]ci[oa]s?|fiction(?:al)?|hipot[ée]tic[oa]s?|"
    r"hypothetical|simulad[oa]s?|simula[çc][ãa]o|simulat(?:ed|ion)|"
    r"inventad[oa]s?|invented|sat[íi]ric[oa]s?|sátira|satire|"
    r"publicad[oa]|atualizad[oa]|published|updated|according|segundo|"
    r"if|unless|se|caso|ignore|instructions|instruções|untrue|incorrect)\b"
    r"|\bno\s+(?:such\s+)?(?:classification|declaration|event)\b"
    r"|\bsem\s+(?:qualquer\s+)?(?:caracterização|classificação|declaração)\b"
    r"|[!?;\"“”«»]", re.I,
)
_CLAIM = re.compile(
    r"^\s*(?:(?:Em|On)\s+(?P<leading_date>" + _DATE + r"),\s+)?"
    r"(?:(?:[AaOo]|The)\s+)?(?P<actor>" + _ACTOR + r")\s+"
    r"(?P<action>" + _DIRECT_ACTION + r")\s+(?:(?:a|o|the)\s+)?"
    r"(?P<subject>" + _SUBJECT + r")\s+(?:como|as)\s+(?:(?:uma?|an?|the)\s+)?"
    r"(?P<label>" + _LABEL + r")"
    r"(?:\s+(?:em|on)\s+(?P<trailing_date>" + _DATE + r"))?\.?\s*$",
)
_COORDINATED = re.compile(
    r"^\s*(?:(?P<causal>This led|Isso levou)\s+)?"
    r"(?:(?:a|o|the)\s+)?(?P<actor>" + _ACTOR + r")\s+"
    r"(?P<first_clause>(?P<first_action>to declare|a declarar|declared|declarou)\s+"
    r"(?:(?:a|an|um|uma)\s+)?(?P<first_label>" + _LABEL + r")\s+"
    r"(?:on|em)\s+(?P<first_date>" + _DATE + r"))\s+"
    r"(?:and|e)\s+(?P<second_clause>(?:(?P<second_aux>to|a)\s+)?"
    r"(?P<action>" + _INFINITIVE + "|" + _DIRECT_ACTION + r")\s+"
    r"(?P<subject>" + _SUBJECT + r")\s+(?:as|como)\s+"
    r"(?:(?:a|an|um|uma)\s+)?(?P<label>" + _LABEL + r")\s+"
    r"(?:on|em)\s+(?P<second_date>" + _DATE + r"))\.?\s*$",
)
_DEFINITION = re.compile(
    r"^(?:The|A|O|A)\s+(?P<subject>" + _SUBJECT + r")\s+"
    r"(?P<label>pandemic|pandemia)\s+(?:is|é)\s+(?:a|an|um|uma)\s+"
    r"(?:(?:global|worldwide|regional|nacional)\s+)?(?:outbreak|surto)\s+"
    r"(?:of|de)\s+(?P<pathogen>" + _WORDS + r")"
    r"(?:\s+[–—-]\s+(?:an infectious disease caused by|uma doença infecciosa causada por)\s+"
    + _SUBJECT + r")?\.$",
)
_BRIDGE = re.compile(
    r"^Cases of\s+(?:novel\s+)?(?P<pathogen>" + _WORDS + r")"
    r"(?:\s+\([A-Za-z][A-Za-z0-9-]{1,15}\))?\s+were first detected in\s+"
    + _ACTOR + r"\s+in\s+" + _MONTH + r"\s+\d{4}"
    r"(?:, with the virus spreading rapidly to other countries across the world)?\.$",
)
_ANAPHOR = re.compile(r"^(?:the outbreak|o surto)$", re.I)


def _normal(value):
    return " ".join(lexical_text(value).casefold().split())


def _label(value):
    value = _normal(value)
    return "pandemic" if value == "pandemia" else value


def _overlapping_labels(left, right):
    # An added adjective cannot disguise two potentially competing dates of
    # the same classification. This check does not erase that adjective from
    # either preserved literal clause or confer a broader label equivalence.
    neutral = {"a", "an", "the", "of", "de", "da", "do", "um", "uma"}
    tokens = [{_label(word) for word in re.findall(_WORD, value) if _normal(word) not in neutral}
              for value in (left, right)]
    return bool(tokens[0] & tokens[1])


def _actor(value):
    # A written expansion and its parenthetical abbreviation must identify
    # the same actor. Only existing explicit lexical aliases can collapse
    # different spellings; arbitrary acronyms never gain an inferred owner.
    value = lexical_text(value)
    match = re.fullmatch(r"(.+?)\s+\(([A-Z]{2,8})\)", value)
    if match:
        if _normal(match[1]) != _normal(match[2]):
            return None
        value = match[1]
    return _normal(value)


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value).isoformat()
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
            day, month, year = map(int, value.split("/"))
        else:
            parts = re.sub(r"[.,]", "", value.casefold()).split()
            parts = [word for word in parts if word != "de"]
            if len(parts) != 3:
                return None
            if parts[0] in _MONTHS:
                month, day, year = _MONTHS[parts[0]], int(parts[1]), int(parts[2])
            else:
                day, month, year = int(parts[0]), _MONTHS[parts[1]], int(parts[2])
        return date(year, month, day).isoformat()
    except (ValueError, KeyError):
        return None


def _subject_names(value):
    """A literal parenthetical name defines an alias, never a qualifier."""
    if re.search(r"\b(?:e|ou|and|or)\b", value, re.I):
        return set()
    match = re.fullmatch(r"(.+?)\s+\(([A-Za-z][A-Za-z0-9-]{1,15})\)", value)
    return {_normal(match[1]), _normal(match[2])} if match else {_normal(value)}


def classification_body_binding(claim, quote, context):
    """Return a revalidatable support-only proof, or ``None``.

    Inputs must be the unmodified complete claim, literal BODY passage and
    its complete retained context. For an anaphoric ``the outbreak``, the
    passage itself must contain its explicit outbreak definition immediately
    before it, optionally separated by one neutral same-pathogen case report.
    A heading/context occurrence of the disease cannot supply that identity.

    The caller must retain provenance/family, retrieval chronology, common
    context guards and model review. This helper neither rewrites evidence nor
    grants refutation, source eligibility, independence or a final verdict.
    """
    if (not all(isinstance(value, str) for value in (claim, quote, context))
            or not 20 <= len(claim) <= 1000 or not 20 <= len(quote) <= 1200
            or not context or len(context) > 3600
            or _UNSAFE.search(claim) or _UNSAFE.search(quote) or _UNSAFE.search(context)):
        return None
    left = _CLAIM.fullmatch(claim)
    if left is None or bool(left["leading_date"]) == bool(left["trailing_date"]):
        return None
    claimed_date = _date(left["leading_date"] or left["trailing_date"])
    if claimed_date is None:
        return None
    statements = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ])", quote.strip())
    if not 1 <= len(statements) <= 3:
        return None
    right = _COORDINATED.fullmatch(statements[-1])
    if right is None:
        return None
    if right["causal"]:
        expected = ("to declare", "to") if right["causal"] == "This led" else ("a declarar", "a")
        if ((right["first_action"], right["second_aux"]) != expected
                or re.fullmatch(_INFINITIVE, right["action"]) is None):
            return None
    elif (right["first_action"] not in {"declared", "declarou"} or right["second_aux"]
          or re.fullmatch(_DIRECT_ACTION, right["action"]) is None):
        return None
    actor = _actor(left["actor"])
    dates = [_date(right["first_date"]), _date(right["second_date"])]
    if (not actor or actor != _actor(right["actor"]) or None in dates
            or claimed_date != dates[1] or _label(left["label"]) != _label(right["label"])
            or _overlapping_labels(right["first_label"], right["label"])):
        return None
    antecedent = None
    subject = re.sub(r"^(?:the|a|an|o|a)\s+", "", right["subject"], flags=re.I)
    if _ANAPHOR.fullmatch(right["subject"]):
        if len(statements) < 2:
            return None
        definition = _DEFINITION.fullmatch(statements[0])
        if definition is None or _label(definition["label"]) != _label(right["label"]):
            return None
        if len(statements) == 3:
            bridge = _BRIDGE.fullmatch(statements[1])
            if bridge is None or _normal(bridge["pathogen"]) != _normal(definition["pathogen"]):
                return None
        subject = definition["subject"]
        antecedent = {"definition": statements[0], "bridge": statements[1] if len(statements) == 3 else None}
    elif len(statements) != 1:
        return None
    if _normal(left["subject"]) not in _subject_names(subject):
        return None
    return {
        "kind": "explicit_coordinated_classification_body_date",
        "actor": actor, "subject": subject, "classification": _label(right["label"]),
        "date": dates[1], "matched_clause": 1, "antecedent": antecedent,
        "clauses": [
            {"literal": right["first_clause"], "classification": _label(right["first_label"]), "date": dates[0]},
            {"literal": right["second_clause"], "classification": _label(right["label"]), "date": dates[1]},
        ],
        "claim": claim, "quote": quote, "context": context,
    }
