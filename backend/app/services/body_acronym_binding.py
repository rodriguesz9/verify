"""Literal BODY definitions may resolve a later acronym subject.

This helper supplies identity only. It never supplies an event, date, agency,
qualifier, truth value, or source vote. The original quote is unchanged. The
caller must run its ordinary passage/context/quantity guards and model review.

Supported scope is deliberately small: an initial multiword claim subject,
an explicit parenthesized ``também conhecido como`` / ``also known as`` BODY
definition, and a later BODY sentence starting with that uppercase acronym.
All intervening text, including headings, stays in bounded model context.
"""
import re


VERSION = "explicit_body_acronym_v1"
MAX_DISTANCE = 24
MAX_CONTEXT = 3600
MAX_SENTENCES = 5000
_WORD = r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ’'-]*"
_CLAIM_SUBJECT = re.compile(
    r"^\s*(?:(?i:o|a|os|as|the)\s+)?(?P<entity>" + _WORD
    + r"(?:\s+" + _WORD + r"){1,9}?)\s+"
    r"(?:(?i:não|nao|not)\s+)?(?i:foi|foram|é|são|era|eram|was|were|is|are)\b")
_QUOTE_SUBJECT = re.compile(
    r"^\s*(?:(?i:o|a|os|as|the)\s+)?(?P<alias>[A-Z][A-Z0-9]{1,9})(?=\s)")
_MARKER = re.compile(
    r"\(\s*(?i:também\s+conhecid[oa]s?\s+como|also\s+known\s+as)\s+"
    r"(?P<alias>[A-Z][A-Z0-9]{1,9})"
    r"(?:\s+(?i:ou|or)\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ’'-]{1,40}){0,2}\s*\)")
_UNSAFE_DEFINITION = re.compile(
    r"\b(?:não|nao|not|never|nunca|jamais|nem|talvez|pode|poderia|may|might|could|"
    r"se|caso|if|unless|seria|would|supostamente|supost[oa]|allegedly|alleged|"
    r"rumou?r|boato|alegou|claimed|fict[íi]ci[oa]s?|fiction(?:al)?|"
    r"hipot[ée]tic[oa]s?|hypothetical|simulad[oa]s?|simulated|"
    r"anteriormente|formerly)\b", re.I)
_REDEFINITION = re.compile(
    r"\b(?:significa|significava|representa|representava|means|meant|stands\s+for|"
    r"stood\s+for|passou\s+a|agora|now|renomead[oa]|renamed)\b", re.I)
_ANCHOR_KEYS = {"kind", "entity", "alias", "definition", "definition_index"}


def _subject(claim):
    if not isinstance(claim, str) or not 0 < len(claim) <= 5000:
        return None
    match = _CLAIM_SUBJECT.match(claim)
    if match is None or not 4 <= len(match["entity"]) <= 100:
        return None
    return match


def _name_before_marker(sentence, marker, entity):
    """Only the initial complete subject may own this definition.

    A suffix match would borrow the identity of a replica, drawing, owner's
    instrument or other subordinate noun. Unknown byline/UI contamination
    must be fixed structurally by the reader; it cannot be silently ignored.
    """
    name = re.compile(r"\s*(?:(?:o|a|os|as|the)\s+)?"
                      + re.escape(entity).replace(r"\ ", r"\s+") + r"\s*", re.I)
    return name.fullmatch(sentence[:marker.start()]) is not None


def _defined_alias(sentence, entity, alias):
    markers = list(_MARKER.finditer(sentence))
    return (len(markers) == 1 and markers[0]["alias"] == alias
            and _name_before_marker(sentence, markers[0], entity)
            and not _UNSAFE_DEFINITION.search(sentence))


def explicit_body_acronym_candidate(claim, raw, index, *, leading_context_indices=()):
    """Return original quote + complete bounded context + a literal anchor.

    Only one BODY sentence is resolved; no discontiguous quote is synthesized.
    The caller already validates its document, but malformed inputs fail closed.
    """
    subject = _subject(claim)
    if subject is None or not isinstance(raw, dict) or type(index) is not int:
        return None
    sentences = raw.get("sentences")
    if (not isinstance(sentences, list) or not 0 <= index < len(sentences) <= MAX_SENTENCES
            or any(not isinstance(value, str) for value in sentences)):
        return None
    roles = raw.get("sentence_roles", ["body"] * len(sentences))
    if (not isinstance(roles, list) or len(roles) != len(sentences)
            or any(not isinstance(role, str) or role not in {"body", "context"} for role in roles)
            or roles[index] != "body"):
        return None
    quote = sentences[index].strip()
    if not 20 <= len(quote) <= 1200:
        return None
    alias_subject = _QUOTE_SUBJECT.match(quote)
    if alias_subject is None:
        return None
    alias = alias_subject["alias"]
    if re.fullmatch(r"[IVXLCDM]+", alias):
        return None  # A flight/person ordinal is not an acronym definition.
    entity = subject["entity"]
    definitions = []
    for position, sentence in enumerate(sentences):
        for marker in _MARKER.finditer(sentence):
            if marker["alias"] != alias:
                continue
            # An explicit conflicting definition anywhere in the bounded
            # document, including a heading, prevents global alias borrowing.
            if not _name_before_marker(sentence, marker, entity):
                return None
            if roles[position] == "body" and _defined_alias(sentence, entity, alias):
                definitions.append(position)
    eligible = [position for position in definitions if 0 < index - position <= MAX_DISTANCE]
    if not eligible:
        return None
    definition_index = max(eligible)
    if (not isinstance(leading_context_indices, (tuple, list))
            or any(type(value) is not int or not 0 <= value < len(sentences)
                   for value in leading_context_indices)):
        return None
    context_indices = sorted(set(leading_context_indices) | set(
        range(max(0, definition_index - 1), min(len(sentences), index + 2))))
    context = " ".join(sentences[position].strip() for position in context_indices)
    if len(context) > MAX_CONTEXT or context.count(quote) != 1:
        return None
    # Unknown explicit redefinitions of this same acronym stay ambiguous.
    # Mere words about a different instrument's renamed/full name do not
    # change the already literal identity proof for the claimed instrument.
    alias_word = re.compile(r"\b" + re.escape(alias) + r"\b")
    for position, sentence in enumerate(sentences):
        if position != definition_index and alias_word.search(sentence) and _REDEFINITION.search(sentence):
            return None
    anchor = {"kind": VERSION, "entity": entity, "alias": alias,
              "definition": sentences[definition_index].strip(),
              "definition_index": definition_index}
    return {"quote": quote, "context": context, "body_acronym_anchor": anchor}


def body_acronym_claim_reading(claim, passage):
    """Revalidate identity proof before changing only the claimed subject.

    None means no anchor; False means an invalid anchor and must be rejected.
    A returned string still requires every ordinary evidence/context guard.
    """
    anchor = passage.get("body_acronym_anchor") if isinstance(passage, dict) else None
    if anchor is None:
        return None
    subject = _subject(claim)
    if (subject is None or not isinstance(anchor, dict) or set(anchor) != _ANCHOR_KEYS
            or anchor.get("kind") != VERSION or anchor.get("entity") != subject["entity"]
            or type(anchor.get("definition_index")) is not int
            or not 0 <= anchor["definition_index"] < MAX_SENTENCES):
        return False
    quote, context = passage.get("quote"), passage.get("context")
    alias, definition = anchor.get("alias"), anchor.get("definition")
    if (not isinstance(quote, str) or not 20 <= len(quote) <= 1200
            or not isinstance(context, str) or not 0 < len(context) <= MAX_CONTEXT
            or not isinstance(alias, str) or not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", alias)
            or re.fullmatch(r"[IVXLCDM]+", alias)
            or not isinstance(definition, str) or not 0 < len(definition) <= MAX_CONTEXT
            or context.count(quote) != 1 or context.count(definition) != 1
            or context.index(definition) >= context.index(quote)):
        return False
    alias_subject = _QUOTE_SUBJECT.match(quote)
    if (alias_subject is None or alias_subject["alias"] != alias
            or not _defined_alias(definition, subject["entity"], alias)):
        return False
    for statement in re.split(r"[.!?;]\s+", context.replace(definition, "", 1)):
        if re.search(r"\b" + re.escape(alias) + r"\b", statement) and _REDEFINITION.search(statement):
            return False
    return claim[:subject.start("entity")] + alias + claim[subject.end("entity"):]
