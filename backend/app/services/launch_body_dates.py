"""Literal completed-launch body dates, never a date inferred from URL/title.

Closed PT passive, agency-active and mission-subject grammars connect one completed launch
to an attached explicit relative weekday/day. Publication must come from the
caller's publication metadata. A dated internal reading requires revalidation
of the entire literal BODY frame; it never replaces that original quote.
These helpers do not infer instrument ownership or decide any verdict.
"""
from datetime import date
import re

from app.services.launch_relations import _frame as _launch_frame, _object_identity


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
_ACTIVE_RELATIVE = (
    r"(?:(?i:na\s+manhã|na\s+madrugada|na\s+tarde|na\s+noite)\s+(?i:dest[ae])|(?i:nest[ae]))\s+"
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
_NUMBERED_MISSION = _PROPER_NAME + r"\s+(?:[1-9]\d{0,2}|[IVXLCDM]{1,8})"
_ACTIVE_COMPLEMENT = (
    r",\s+(?i:primeiro voo do foguete)\s+" + _FLIGHT_NAME
    + r"(?:\s+\(" + _PROPER_NAME + r"\))?\s+(?i:com a cápsula)\s+" + _FLIGHT_NAME
    + r",\s+(?i:destinada a levar humanos de volta)\s+(?i:à|ao)\s+" + _PROPER_NAME
)
_ACTIVE_FRAME = re.compile(
    r"^\s*(?:(?i:a|o)\s+)?(?P<agency>" + _AGENCY + r")\s+(?i:lançou)\s+"
    r"(?P<expression>" + _ACTIVE_RELATIVE + r")\s+(?i:a missão)\s+"
    r"(?P<name>" + _NUMBERED_MISSION + r")(?P<complement>" + _ACTIVE_COMPLEMENT + r")?\s*\.?\s*$"
)
_ACTIVE_DATE_ONLY_CLAIM = re.compile(
    r"(?i:a missão)\s+(?P<name>" + _NUMBERED_MISSION + r")\s+"
    r"(?i:foi lançada em)\s+(?i:" + _ABSOLUTE + r")\.?"
)
_ACTIVE_UNSAFE = re.compile(
    r"\b(?:se|caso|sem|segundo|conforme|reportagem|relato|relatou|reportou|"
    r"fict[íi]ci[oa]s?|ficção|ficcao|simulad[oa]s?|simula[çc][ãa]o|hip[óo]tese|"
    r"hipot[ée]tic[oa]s?|inventad[oa]s?|imagin[áa]ri[oa]s?|fantasia|sonho|"
    r"supost[oa]s?|alegad[oa]s?|sat[íi]ric[oa]s?|s[áa]tira|possivelmente|aparentemente|"
    r"publicad[oa]|atualizad[oa])\b"
    r"|[;!?\"“”«»'‘’]", re.I,
)
_FIRST_FLIGHT_COMPLEMENT = (
    r",\s+(?i:no primeiro voo do (?:super)?foguete)\s+"
    + _FLIGHT_NAME + r"(?:\s+\(" + _PROPER_NAME + r"\))?"
    + r"\s+(?i:com a cápsula)\s+" + _FLIGHT_NAME
    + r"(?:,\s+(?i:destinada a levar humanos de volta)\s+(?i:à|ao)\s+" + _PROPER_NAME + r")?,\s*"
)
_MISSION_SUBJECT_FRAME = re.compile(
    r"^\s*(?:(?i:a|o)\s+)?(?i:missão)\s+(?P<name>" + _NUMBERED_MISSION + r")"
    + r"(?P<complement>" + _FIRST_FLIGHT_COMPLEMENT + r")?\s+"
    + r"(?P<verb>(?i:partiu|decolou))\s+(?P<expression>" + _ACTIVE_RELATIVE + r")\s*\.?\s*$"
)
_PLANNING_LABEL = re.compile(
    r"(?:^|[.!?\n]\s*)(?:previs[ãa]o(?:\s+de\s+lan[çc]amento)?"
    r"|plano(?:\s+para\s+o\s+voo|\s+do\s+voo|\s+de\s+lan[çc]amento)?"
    r"|planejamento(?:\s+do\s+voo|\s+de\s+lan[çc]amento)?|forecast|launch\s+plan)\s*:\s*$", re.I,
)
_PLANNED_MISSION = re.compile(
    r"^\s*(?i:a missão)(?:\s+(?P<name>" + _NUMBERED_MISSION + r"))?\s+"
    r"(?i:será lançada|vai ser lançada|vai decolar|irá decolar|decolará)\b[^.!?\n]{0,180}[.!?]?\s*$"
)


def _active_mission(quote):
    if (not isinstance(quote, str) or not 20 <= len(quote) <= 1200
            or _OUT_OF_SCOPE.search(quote) or _ACTIVE_UNSAFE.search(quote)):
        return None
    match = _ACTIVE_FRAME.fullmatch(quote)
    identity = _object_identity(match["name"]) if match else None
    return (match, identity) if identity is not None else None


def _mission_subject(quote):
    """One completed liftoff; departure needs explicit first-flight context.

    A bare 'partiu' may describe transport to a pad. Require the closed
    nominal rocket/capsule complement for it; unknown appositives, actions
    and destinations cannot be stripped to make a match. The sole parsed
    positive predicate is the only occurrence exempt from the unsafe veto.
    """
    if (not isinstance(quote, str) or not 20 <= len(quote) <= 1200
            or _ACTIVE_UNSAFE.search(quote)):
        return None
    match = _MISSION_SUBJECT_FRAME.fullmatch(quote)
    if match is None or (match["verb"].casefold() == "partiu" and not match["complement"]):
        return None
    if any(found.span() != match.span("verb") for found in _OUT_OF_SCOPE.finditer(quote)):
        return None
    identity = _object_identity(match["name"])
    return (match, identity) if identity is not None else None


def launch_body_has_scoped_plan(quote, context):
    """A local forecast label or the same mission's adjacent planned launch.

    Future purpose and a different named mission do not qualify the completed
    event. Only a closed launch plan about this mission can defeat it; never
    drop that context merely because an internal date reading was generated.
    """
    frame = _active_mission(quote) or _mission_subject(quote)
    if frame is None or not isinstance(context, str):
        return False
    def same_mission_plan(statement):
        match = _PLANNED_MISSION.fullmatch(statement)
        return bool(match and (match["name"] is None or _object_identity(match["name"]) == frame[1]))

    parts = context.split(quote)
    if len(parts) == 1:
        # No reliable placement: a scoped plan must not become harmless just
        # because the caller omitted the quotation from the context.
        return bool(_PLANNING_LABEL.search(context) or any(same_mission_plan(statement)
                    for statement in re.split(r"(?<=[.!?])\s+", context.strip())))
    for before, after in zip(parts, parts[1:]):
        if _PLANNING_LABEL.search(before):
            return True
        # Only immediately adjacent statements own this limited relation.
        # When the same quote repeats, any planned occurrence makes its
        # placement ambiguous; repetition cannot erase the governing plan.
        adjacent = (re.split(r"(?<=[.!?])\s+", before.strip())[-1],
                    re.split(r"(?<=[.!?])\s+", after.strip())[0])
        if any(same_mission_plan(statement) for statement in adjacent):
            return True
    return False


def launch_date_claim_matches_body(claim, quote):
    """Restrict relative-date support to the same named, date-only claim.

    No agency, launch site, time-of-day, success or other claimed qualifier
    may disappear during normalization of the source's relative expression.
    A calendar/chronology and support/refutation comparison still runs later.
    """
    if not isinstance(claim, str) or not isinstance(quote, str):
        return False
    active = _active_mission(quote) or _mission_subject(quote)
    if active is not None:
        # The object is explicitly a numbered mission, not a vehicle inferred
        # to stand for it. The existing parser owns Roman/numeric equivalence.
        left = _launch_frame(claim)
        return bool(_ACTIVE_DATE_ONLY_CLAIM.fullmatch(claim.strip()) and left is not None
                    and left.identity_kind == "mission" and left.identity == active[1]
                    and left.agency is None and left.crew is None and not left.successful
                    and left.location is None and left.time is None)
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
    subject = _mission_subject(quote)
    if _OUT_OF_SCOPE.search(quote) and subject is None:
        return None
    match = _FRAME.fullmatch(quote)
    active = _active_mission(quote) if match is None else None
    if match is None and active is None and subject is None:
        return None
    if active is not None:
        match = active[0]
    elif subject is not None:
        match = subject[0]
    elif (match["intro_name"] and " ".join(match["intro_name"].casefold().split())
            != " ".join(match["name"].casefold().split())):
        return None
    if (int(match["day"]) != published.day
            or match["month"] and int(match["month"]) != published.month
            or match["weekday"].casefold() != _WEEKDAYS[published.weekday()]):
        return None
    anchor = {"kind": "explicit_launch_body_date", "expression": match["expression"],
              "publication_date": publication_date}
    if active is not None:
        anchor.update(kind="explicit_active_mission_launch_body_date",
                      mission_identity={"program": active[1][0], "number": active[1][1]})
    elif subject is not None:
        anchor.update(kind="explicit_mission_subject_launch_body_date",
                      mission_identity={"program": subject[1][0], "number": subject[1][1]})
    return anchor


def launch_body_dated_reading(quote, anchor):
    """Revalidate the complete literal frame before returning internal text.

    Active prose may contain only the closed nominal vehicle/capsule/purpose
    complement above. This proves a mission/date reading without treating a
    vehicle as the mission or approving any additional claimed qualifier.
    Callers must separately require launch_date_claim_matches_body, preserve
    the original quote, and retain chronology, provenance and context guards.
    """
    if (not isinstance(anchor, dict)
            or anchor != launch_body_temporal_anchor(quote, anchor.get("publication_date"))):
        return None
    if anchor["kind"] == "explicit_launch_body_date":
        return quote.replace(anchor["expression"], "em " + anchor["publication_date"], 1)
    active = _active_mission(quote) or _mission_subject(quote)
    if active is None:
        return None
    reading = "A missão " + active[0]["name"] + " foi lançada em " + anchor["publication_date"] + "."
    parsed = _launch_frame(reading)
    return reading if parsed is not None and parsed.identity == active[1] else None
