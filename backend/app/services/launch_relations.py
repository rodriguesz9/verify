"""Narrow, pure comparison of explicitly completed, identified mission launches.

``launch_date_relation(claim, quote)`` returns ``supports``, ``refutes`` or None.
A mission-date frame needs one completed launch, an explicit mission/flight
label, a proper program name plus flight number, and one full calendar date
directly bound to that launch. Numeric/Roman flight numbers are equivalent;
the existing Apolo/Apollo spelling alias is explicit, not an entity lookup.
Closed past-tense liftoff/blastoff/decolagem predicates are launch synonyms.
An agency possessive is retained; an explicitly claimed owner cannot vanish
or be replaced by an inferred organization alias during comparison.
Named vehicle/mission or vehicle/payload frames can support an identical date
only; different dates of those potentially repeated launches never refute.
Vehicle model numbers alone are not mission identities. Unknown constructions
deliberately abstain.
``is_launch_date_claim`` is a broader scope guard: additional qualifiers,
negation, plans and unsupported date precision remain in scope, so they
cannot fall back to a generic partial comparison when strict parsing fails.

The caller owns provenance: ``quote`` must be a literal BODY passage, never a
headline, caption, timeline label, publication date or synthesized context.
``quote_role`` can enforce a role already established by the caller; it does
not classify source text. No context, retrieval time, publisher, or model guard
is replaced by this helper. In particular, this does not create source votes.
"""
from dataclasses import dataclass
from datetime import date
import re
import unicodedata
from typing import Literal


Relation = Literal["supports", "refutes"]
_MONTHS = {word: index for index, words in enumerate((
    "janeiro january jan", "fevereiro february feb", "março march mar",
    "abril april apr", "maio may", "junho june jun", "julho july jul",
    "agosto august aug", "setembro september sep sept", "outubro october oct",
    "novembro november nov", "dezembro december dec"), 1) for word in words.split()}
_MONTH = "(?:" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"
_DATE = re.compile(
    r"(?<![\w/-])(?:\d{1,2}\s+(?:de\s+)?" + _MONTH + r"\s+(?:de\s+)?\d{4}"
    r"|" + _MONTH + r"\s+\d{1,2},?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})(?![\w/-])", re.I)
_UNSAFE = re.compile(
    r"\b(?:não|nao|not|never|nunca|jamais|nem|without|didn['’]t|wasn['’]t|"
    r"will|would|may|might|could|planned|scheduled|expected|plans|"
    r"será|seria|previst[oa]|planejad[oa]|agendad[oa]|poderia|talvez|"
    r"rumou?r|boato|alegad[oa]|allegedly|alleged|supostamente|claimed|"
    r"announced|announcement|anunciou|anunciad[oa]|published|updated|publicad[oa]|"
    r"return(?:ed)?|retornou|splashdown|landed|pousou|"
    r"attempt(?:ed)?|tentativa|failed|failure|falhou|fracassou|abort(?:ed)?|"
    r"cancel(?:led|ed)?|test(?:ed)?|teste|relaunch(?:ed)?|relançad[oa]|again|"
    r"e|and|also|but|mas|porém|também|caption|legenda|credit|crédito)\b", re.I)
_LAUNCH = re.compile(
    r"^(?P<subject>.+?)\s+(?P<verb>(?:(?:was\s+)?(?:successfully\s+)?launched"
    r"|(?:successfully\s+)?(?:lifted|blasted)\s+off"
    r"|(?:foi\s+lançad[oa]|decolou)(?:\s+com\s+sucesso)?))(?P<details>\s.*|)$", re.I)
_LABEL = r"(?:mission|flight|missão|voo)"
_SCOPE_LABEL = re.compile(r"\b" + _LABEL + r"\b", re.I)
_SCOPE_VEHICLE = re.compile(r"\b(?:foguete|rocket)\b", re.I)
_SCOPE_PAYLOAD = re.compile(r"\b(?:espaçonave|nave|spacecraft|payload)\b", re.I)
_SCOPE_LAUNCH = re.compile(
    r"\b(?:launch(?:ed|es|ing)?|(?:lift(?:ed|ing)?|blast(?:ed|ing)?)\s+off|"
    r"lançamentos?|lançad[oa]s?|lançou|lançaram|lançar|lança|decolou|decolar)\b", re.I)
_SCOPE_YEAR = re.compile(r"\b(?:18|19|20|21)\d{2}\b")
_NAME_WORD = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ’'-]{1,40}"
_AGENCY = _NAME_WORD + r"(?:\s+" + _NAME_WORD + r"){0,4}"
_AGENCY_FRONT = re.compile(r"^(?P<agency>" + _AGENCY + r")[’']s\s+(?P<subject>.+)$")
_AGENCY_BACK = re.compile(r"^(?P<subject>.+?)\s+(?i:da|do|de|of)\s+(?P<agency>" + _AGENCY + r")$")
_IDENTITY = re.compile(r"(?P<program>" + _NAME_WORD + r"(?:\s+" + _NAME_WORD
                       + r"){0,3})[ -](?P<number>[1-9]\d{0,2}|[IVXLCDM]{1,8})")
_OBJECT_ID = (_NAME_WORD + r"(?:\s+" + _NAME_WORD + r"){0,3}[ -](?:[1-9]\d{0,2}|[IVXLCDM]{1,8})")
_NOMINAL = re.compile(
    r"^(?:(?:o\s+)?lançamento\s+(?:da|do|de)\s+(?P<pt_subject>.+?)\s+(?:ocorreu|aconteceu)"
    r"|(?:the\s+)?launch\s+of\s+(?:the\s+)?(?P<en_subject>.+?)\s+(?:occurred|took place))"
    r"(?P<details>\s.*|)$", re.I)
_VEHICLE_MISSION = re.compile(
    r"^(?i:(?:the\s+)?)" + r"(?P<vehicle>" + _OBJECT_ID + r")"
    r"(?i:\s+rocket\s+launches\s+on\s+(?:the\s+)?)"
    r"(?P<subject>" + _OBJECT_ID + r"(?i:\s+(?:mission|flight)))"
    r"(?P<details>\s.*|)$")
_VEHICLE_PAYLOAD = re.compile(
    r"^(?i:(?:o\s+)?foguete\s+)" + r"(?P<vehicle>" + _OBJECT_ID + r")"
    r"(?i:\s+lançou\s+(?:a\s+)?(?:espaçonave|nave)\s+)"
    r"(?P<payload>" + _OBJECT_ID + r")(?P<details>\s.*|)$")
_LOCATION_WORD = r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ’'-]*|\d{1,3}[A-Z])"
_LOCATION = re.compile(_LOCATION_WORD + r"(?:\s+(?:(?i:at|in|of|the|de|da|do|em|no|na)\s+)?"
                       + _LOCATION_WORD + r"){0,14}")
_TIME = re.compile(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})"
                   r"(?:\s*(?P<meridiem>a\.?m\.?|p\.?m\.?))?"
                   r"(?:\s+(?P<zone>UTC|GMT|EST|EDT|CST|CDT|MST|MDT|PST|PDT|BRT))?", re.I)


@dataclass(frozen=True)
class _Launch:
    identity: tuple[str, int]
    day: date
    crew: str | None
    successful: bool
    location: str | None
    time: tuple[int, int, str | None] | None
    identity_kind: Literal["mission", "vehicle_mission", "vehicle_payload"]
    vehicle: tuple[str, int] | None = None
    agency: str | None = None


def _number(value):
    if value.isdigit():
        return int(value)
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = sum(-values[char] if index + 1 < len(value) and values[char] < values[value[index + 1]]
                 else values[char] for index, char in enumerate(value))
    rest, canonical = result, ""
    for amount, roman in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
                          (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
                          (5, "V"), (4, "IV"), (1, "I")):
        count, rest = divmod(rest, amount)
        canonical += roman * count
    return result if canonical == value else None


def _day(value):
    value = value.casefold().replace(".", "").replace(",", "")
    words = [word for word in value.split() if word != "de"]
    try:
        if len(words) == 3 and words[1] in _MONTHS:
            return date(int(words[2]), _MONTHS[words[1]], int(words[0]))
        if len(words) == 3 and words[0] in _MONTHS:
            return date(int(words[2]), _MONTHS[words[0]], int(words[1]))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        day, month, year = re.split(r"[/-]", value)
        # Slash dates are day/month/year, matching the caller's date contract.
        return date(int(year), int(month), int(day))
    except (ValueError, TypeError):
        return None


def _subject(value):
    value = re.sub(r"^(?:a|o|the)\s+", "", value.strip(), flags=re.I)
    agency = None
    # An explicit owner is a claim qualifier, not decoration. Removing it
    # without carrying it to the comparison would let a different agency's
    # mission support/refute a qualified claim. Unknown aliasing abstains.
    front_agency, back_agency = _AGENCY_FRONT.fullmatch(value), _AGENCY_BACK.fullmatch(value)
    if front_agency and back_agency:
        return None
    if owned := front_agency or back_agency:
        agency = " ".join(owned["agency"].casefold().split())
        value = owned["subject"]
    value = re.sub(r"\bnão\s+tripulad[oa]\b", "uncrewed", value, flags=re.I)
    value = re.sub(r"\btripulad[oa]\b", "crewed", value, flags=re.I)
    crew_words = re.findall(r"\b(?:uncrewed|crewed)\b", value, re.I)
    if len(crew_words) > 1:
        return None
    crew = crew_words[0].casefold() if crew_words else None
    # The qualifier belongs only to the mission, before its name or label.
    value = re.sub(r"^(?:uncrewed|crewed)\s+", "", value, flags=re.I)
    front = re.match(r"^" + _LABEL + r"\s+", value, re.I)
    back = re.search(r"\s+" + _LABEL + r"$", value, re.I)
    if bool(front) == bool(back):
        return None
    value = value[front.end():] if front else value[:back.start()]
    value = re.sub(r"^(?:uncrewed|crewed)\s+", "", value, flags=re.I)
    identity = _object_identity(value)
    if identity is None:
        return None
    return identity, crew, agency


def _object_identity(value):
    identity = _IDENTITY.fullmatch(value)
    if identity is None or (number := _number(identity["number"])) is None:
        return None
    program = identity["program"].casefold()
    return ("apollo" if program == "apolo" else program), number


def _assertion(value):
    """Bind explicit subjects/objects before admitting any date comparison."""
    launch = _LAUNCH.fullmatch(value)
    if launch and (subject := _subject(launch["subject"])):
        return subject, launch["details"], bool(re.search(r"successfully|sucesso", launch["verb"], re.I)), "mission", None
    nominal = _NOMINAL.fullmatch(value)
    if nominal and (subject := _subject(nominal["pt_subject"] or nominal["en_subject"])):
        return subject, nominal["details"], False, "mission", None
    vehicle_mission = _VEHICLE_MISSION.fullmatch(value)
    if vehicle_mission:
        subject = _subject(vehicle_mission["subject"])
        vehicle = _object_identity(vehicle_mission["vehicle"])
        if subject and vehicle:
            return subject, vehicle_mission["details"], False, "vehicle_mission", vehicle
    vehicle_payload = _VEHICLE_PAYLOAD.fullmatch(value)
    if vehicle_payload:
        payload = _object_identity(vehicle_payload["payload"])
        vehicle = _object_identity(vehicle_payload["vehicle"])
        if payload and vehicle:
            return (payload, None, None), vehicle_payload["details"], False, "vehicle_payload", vehicle
    return None


def _details(value):
    value = value.strip().strip(",").strip()
    clock = None
    # Location phrases may themselves contain "at". Only a final, fully
    # parsed clock can be removed; an earlier place connector is not a time.
    timed = next(((match, parsed) for match in reversed(list(re.finditer(
        r"\s+(?:at|às|as)\s+", " " + value, re.I)))
        if (parsed := _TIME.fullmatch((" " + value)[match.end():]))), None)
    if timed:
        time_match, parsed = timed
        hour, minute = int(parsed["hour"]), int(parsed["minute"])
        meridiem = (parsed["meridiem"] or "").replace(".", "").casefold()
        if minute > 59 or (meridiem and not 1 <= hour <= 12) or (not meridiem and hour > 23):
            return None
        if meridiem:
            hour = hour % 12 + (12 if meridiem == "pm" else 0)
        clock = (hour, minute, parsed["zone"].upper() if parsed["zone"] else None)
        value = (" " + value)[:time_match.start()].strip()
    if not value:
        return None, clock
    location = re.fullmatch(r"(?:from|de|do|da)\s+(.+)", value, re.I)
    if location is None or _LOCATION.fullmatch(location[1]) is None:
        return None
    return " ".join(location[1].casefold().split()), clock


def _frame(text):
    if not isinstance(text, str) or not 15 <= len(text) <= 1200:
        return None
    text = " ".join(text.split()).rstrip(".").strip()
    # Normalize only the explicit Portuguese crew qualifier before testing
    # negation. No other negative clause can be transformed into an assertion.
    safe_text = re.sub(r"\bnão\s+tripulad[oa]\b", "uncrewed", text, flags=re.I)
    if _UNSAFE.search(_DATE.sub(" ", safe_text)) or any(char in text for char in ';!?"“”«»'):
        return None
    dates = list(_DATE.finditer(text))
    if len(dates) != 1 or (day := _day(dates[0][0])) is None:
        return None
    found = dates[0]
    before, after = text[:found.start()], text[found.end():]
    if re.fullmatch(r"(?:on|em)\s+", before, re.I):
        assertion = after.lstrip(", ")
        extras_after = ""
    else:
        bound = re.fullmatch(r"(.+?)\s+(?:on|em|no dia|na data de)\s+", before, re.I)
        if bound is None:
            return None
        assertion, extras_after = bound[1], after
    parsed = _assertion(assertion)
    if parsed is None:
        return None
    subject, extras_before, successful, identity_kind, vehicle = parsed
    # Two separate qualifier positions may otherwise hide conflicting times
    # or locations. One explicit qualifier sequence is sufficient.
    if extras_before.strip() and extras_after.strip():
        return None
    details = _details(extras_before or extras_after)
    if details is None:
        return None
    return _Launch(subject[0], day, subject[1], successful, details[0], details[1], identity_kind, vehicle,
                   subject[2])


def is_launch_date_claim(claim: str) -> bool:
    """Broader launch/date scope, not a statement that the claim is admissible.

    An explicit mission/flight, rocket or spacecraft/payload, launch
    predicate and calendar date or year suffice for scope. Extra objects,
    quantities, manner/attempt qualifiers,
    negation or plans stay scoped but receive no relation unless the whole
    claim also satisfies the strict completed-launch parser.
    """
    return bool(isinstance(claim, str) and (_SCOPE_LABEL.search(claim)
                or _SCOPE_VEHICLE.search(claim) or _SCOPE_PAYLOAD.search(claim))
                and _SCOPE_LAUNCH.search(claim) and (_DATE.search(claim) or _SCOPE_YEAR.search(claim)))


_LEAD_NUMBER_CONTINUATION = re.compile(
    r"^\s*(?:[-–—&]|and\b|e\b)\s*(?:[1-9]\d{0,2}|[IVXLCDM]{1,8})(?!\w)", re.I)


def _lead_mission_numbers(program, lead):
    words = re.split(r"[ -]+", program)
    pattern = (r"(?<!\w)" + r"[\s-]+".join(re.escape(word) for word in words)
               + r"[\s-]+([1-9]\d{0,2}|[IVXLCDM]{1,8})(?!\w)")
    matches = list(re.finditer(pattern, lead, re.I))
    # A slug delimiter before an ordinary path word is legitimate. A range
    # such as Aurora I-II or Aurora I and II does not identify one mission.
    ambiguous = any(_LEAD_NUMBER_CONTINUATION.match(lead[match.end():]) for match in matches)
    identities = {_number(match[1].upper()) for match in matches}
    identities.discard(None)
    return identities, ambiguous


def launch_lead_identity_priority(claim: str, lead: str) -> int:
    """Reading order only: exact numbered mission, unknown, different mission.

    A disputed year must not send the reader to a different mission that
    happens to share that year. Only a completely parsed mission claim can
    identify the requested program/number here; ambiguous or vehicle/payload
    claims keep the old ordering. A title/path remains an untrusted lead,
    never a body quote, a date, an eligibility filter or a factual relation.
    """
    left = _frame(claim)
    if left is None or left.identity_kind != "mission" or not isinstance(lead, str):
        return 0
    program, requested = left.identity
    identities, ambiguous = _lead_mission_numbers(program, lead)
    if ambiguous:
        return 1
    if requested in identities:
        return 0
    return 2 if identities else 1


_LEAD_LAUNCH_PENDING = re.compile(
    r"\b(?:scheduled|planned|planning|prepares?|preparing|preparation|countdown|fueling|fuelling|"
    r"rollout|attempts?|postponed|scrubbed|cancelled|canceled|expected|targeting|"
    r"previst[oa]s?|previsao|planejad[oa]s?|planeja|prepara|preparacao|contagem|tentativa|"
    r"adiad[oa]s?|cancelad[oa]s?|supostamente|teria|allegedly|rumou?r|boato|"
    r"false|falso|falsa|unconfirmed|unverified|uncertain|unclear|incert[oa]|talvez)\b"
    r"|\b(?:may|might|could|will|would)\s+(?!\d)\w"
    r"|\b(?:set|ready|due)\s+to\b|\b(?:next|proxima|proximo)\s+(?:week|month|semana|mes)\b"
    r"|\b(?:nao|nunca|jamais|not|never)\s+(?:(?:foi|was|has|been|yet|actually|successfully|really|ever)\s+){0,3}(?:lancad[oa]|launch\w*|decol\w*)\b"
    r"|\b(?:wasn['’]t|hasn['’]t|hadn['’]t|didn['’]t|isn['’]t|won['’]t|can['’]t|couldn['’]t|wouldn['’]t)"
    r"\s+(?:(?:been|have|yet|actually|successfully)\s+){0,3}(?:launch\w*|lift\w*|blast\w*)\b"
    r"|\bfailed\s+to\s+launch\b|\bconfirma\s+(?:o\s+)?lancamento\b"
    r"|\bchega\s+(?:a|na|the|at)\s+(?:plataforma|launch\s+pad)\b"
)
_LEAD_LAUNCH_COMPLETED = re.compile(
    r"\b(?:launched|launches|decolou|decola|partiu)\b"
    r"|\b(?:foi|foram)\s+lancad[oa]s?\b"
    r"|\b(?:lifted|lifts|blasted|blasts)\s+off\b"
    r"|\b(?:after|apos)\s+(?:(?:a|an|the|its|epic|historic|successful|o|um|historico)\s+){0,4}"
    r"(?:launch|liftoff|lancamento)\b"
    r"|\b(?:launch|lancamento)\s+(?:completed|concluido)\b"
)


def launch_lead_phase_priority(claim: str, lead: str) -> int | None:
    """Discovery only: completed report, unknown phase, preparation/forecast.

    Restrict this ordering to a fully parsed numbered mission claim. A wrong
    claimed year may need a completed report from a different year; a preview
    matching that allegation must not consume the read ahead of that report.
    No title/path supplies a body relation, launch date or source vote.
    Mixed numbered missions and questions cannot assert a completed phase.
    """
    left = _frame(claim)
    if left is None or left.identity_kind != "mission" or not isinstance(lead, str):
        return None
    normalized = "".join(char for char in unicodedata.normalize("NFD", lead.casefold())
                         if not unicodedata.combining(char))
    normalized = re.sub(r"[-_/]+", " ", normalized)
    if _LEAD_LAUNCH_PENDING.search(normalized):
        return 2
    program, requested = left.identity
    identities, ambiguous = _lead_mission_numbers(program, lead)
    if ambiguous or identities != {requested} or "?" in lead:
        return 1
    return 0 if _LEAD_LAUNCH_COMPLETED.search(normalized) else 1


def launch_date_relation(claim: str, quote: str, *, quote_role: str = "body") -> Relation | None:
    """Compare one literal BODY launch with the whole scoped claim.

    All claimed agency/crew/success/location/time qualifiers must be present and
    equal. Additional source detail is allowed. Different full dates refute
    only after this exact mission/flight and qualifier binding, never merely
    because two launch-related strings contain different years. A vehicle or
    payload frame may describe a repeated launch, so it can only support an
    equal date. Any explicitly claimed vehicle/object kind must also match.
    """
    if quote_role != "body":
        return None
    left, right = _frame(claim), _frame(quote)
    if left is None or right is None or left.identity != right.identity:
        return None
    if ((left.crew is not None and left.crew != right.crew)
            or (left.successful and not right.successful)
            or (left.location is not None and left.location != right.location)
            or (left.time is not None and left.time != right.time)
            or (left.agency is not None and left.agency != right.agency)):
        return None
    if left.identity_kind != "mission" and (left.identity_kind != right.identity_kind or left.vehicle != right.vehicle):
        return None
    if left.day != right.day and (left.identity_kind != "mission" or right.identity_kind != "mission"):
        return None
    return "supports" if left.day == right.day else "refutes"
