"""Literal World Cup title bindings, never a table of historical winners.

The Portuguese competition name ``Copa do Mundo`` conventionally denotes
senior men's national association football here. Explicit women's, youth,
club, futsal or other-sport qualifiers anywhere in quote/context veto that
convention. Bare English ``World Cup`` has no such default: FIFA or an
explicit men's football/soccer designation is required.
One closed Spanish recap can bind a named host/year, ``Mundial de Fútbol``
and an explicit title winner. Its ordinal counts that team's titles; it is
never the competition edition. Spanish category and nonassertion guards
apply to that recap and its context as well.

Only the caller's literal BODY quote supplies evidence. A quote may contain
at most three consecutive body sentences; headings and metadata must never
be joined by the caller. Context can veto a reading, never fill its fields.
Unrecognized/ambiguous frames abstain even when a model proposes a vote.
"""
from dataclasses import dataclass
import re
import unicodedata
from typing import Literal


Relation = Literal["supports", "refutes"]


@dataclass(frozen=True)
class CompetitionOutcome:
    competition: str
    year: int
    category: str
    winner: str


def _case_text(value):
    if not isinstance(value, str):
        return ""
    return " ".join("".join(character for character in unicodedata.normalize("NFKD", value)
                            if not unicodedata.combining(character)).split())


def _text(value):
    return _case_text(value).lower()


_YEAR = r"(?:18|19|20|21)\d{2}"
_NAME = r"[a-z]+(?:[ -][a-z]+){0,5}"
_PT_COMP = r"copa (?:do|no) mundo(?: da fifa)?(?: de futebol(?: masculino)?)?(?: masculino)?(?: da fifa)?(?: de)?\s+" + _YEAR
_EN_COMP = (r"(?:the )?(?:" + _YEAR + r"\s+(?:fifa |men's (?:football |soccer )|mens (?:football |soccer ))world cup"
            r"|(?:fifa |men's (?:football |soccer )|mens (?:football |soccer ))world cup(?: of| in)?\s+" + _YEAR + r")")
_COMP = re.compile(r"\b(?:" + _PT_COMP + r"|" + _EN_COMP + r")\b")
_SCOPE_COMP = re.compile(r"\bcopa (?:do|no) mundo\b|\bworld cup\b")
_OUTCOME_WORD = re.compile(r"\b(?:venceu|vence|venceram|vencera|ganhou|ganha|ganharam|conquistou|conquista|conquistaram|"
                           r"levou|levaram|titulo|taca|campea|campeao|vencedor|vencedora|"
                           r"won|wins|win|winner|champion|champions|title|trophy)\b")
_OTHER_CATEGORY = re.compile(
    r"\b(?:feminin[oa]s?|women|women's|womens|woman|ladies|girls?|meninas?|"
    r"sub[ -]?\d+|under[ -]?\d+|u[ -]?\d{2}|youth|junior|juniors|juvenil|juvenis|infantil|"
    r"base|olimpic[oa]s?|olympic|clubes?|clubs?|futsal|praia|beach|rua|street|"
    r"videogame|video game|games?|esports?|e-sports?|botao|literatura|literature|"
    r"rugby|cricket|hoquei|hockey|basquete|basketball|volei|volleyball|handebol|handball|"
    r"americano|australiano|american football|australian football|baseball|beisebol|softball|"
    r"tenis|tennis|golf|golfe|polo|natacao|swimming|esqui|ski|darts|snooker|"
    r"cegos|blind|paralimpic[oa]s?|paralympic|refugiados|refugees)\b"
)
_UNASSERTED = re.compile(
    r"\b(?:boato|rumor|rumour|supostamente|alegou|alega|allegedly|alleged|"
    r"previsao|previu|prediction|predicted|predicts|aposta|palpite|"
    r"pode|poderia|teria|talvez|may|might|could|would|will|sera|vai|iria|"
    r"falso|falsa|false|nao|not|never|nunca|negou|denied|denial|mentira|lie|untrue|incorrect|"
    r"afirmou|disse|claimed|claims|said|according|reportedly|fake|favorito|favorita|"
    r"nega|negava|desmentiu|desmentida|desmentido|"
    r"satira|satirico|ficcao|fictional|hypothetical|hipotetico)\b"
    r"|\bsegundo (?:um|uma|o|a|relatos|fontes)\b"
)
_BAD_STAGE = re.compile(r"\b(?:vice[ -]?campea[o]?|runner[ -]?up|third|terceiro|terceira|"
                        r"grupo|grupos|group|groups|semifinal|semi-final|quarter|quartas|oitavas|qualifying|eliminatorias)\b")
_BAD_NAME = re.compile(r"\b(?:em|no|na|apos|antes|segundo|quando|porque|mas|e|ou|and|or|but|"
                       r"after|before|at|on|in|para|por|time|team|campea|campeao|final|torneio|"
                       r"ela|ele|eles|elas|it|they|selecao|selecoes|uma|um|partida|jogo|match|game|"
                       r"invicto|invicta|undefeated|novamente|again|obviamente|obviously|amador|amadora|que|who|which)\b")
_FRAME = {"competition": "fifa-world-cup", "category": "senior-men-national-association-football"}

# Language aliases identify teams, not winners or competition editions.
_TEAM_ALIASES = {
    "brazil": "brasil", "germany": "alemanha", "france": "franca", "spain": "espanha",
    "england": "inglaterra", "italy": "italia", "uruguay": "uruguai", "croatia": "croacia",
    "netherlands": "paises baixos", "holland": "paises baixos", "holanda": "paises baixos",
    "japan": "japao", "south korea": "coreia do sul", "united states": "estados unidos",
    "alemania": "alemanha", "francia": "franca", "espana": "espanha",
    "paises bajos": "paises baixos", "japon": "japao", "corea del sur": "coreia do sul",
}

# Plural Portuguese demonyms identify the same existing national teams.
# No edition, title count or historical result belongs in this language map.
_PT_TEAM_DEMONYMS = {
    "alemaes": "alemanha", "brasileiros": "brasil", "franceses": "franca",
    "espanhois": "espanha", "ingleses": "inglaterra", "italianos": "italia",
    "uruguaios": "uruguai", "croatas": "croacia", "neerlandeses": "paises baixos",
    "holandeses": "paises baixos", "japoneses": "japao", "sul-coreanos": "coreia do sul",
}


_TEAM_PREFIX = re.compile(r"^(?:(?:o|a|the)\s+)?(?:(?:selecao(?: nacional)?(?: d[oae])?|national team of)\s+)?")


def _identity(value, literal=None):
    prefix = _TEAM_PREFIX.match(value)
    name = value[prefix.end():].strip()
    if not re.fullmatch(_NAME, name) or _BAD_NAME.search(name):
        return None
    if literal is not None:
        # Proper-name case keeps adverbs/adjectives outside the winner slot.
        # Lowercase aliases are accepted only when explicitly known, not by
        # turning arbitrary prose into an invented national-team identity.
        words = literal[prefix.end():].strip().replace("-", " ").split()
        proper = bool(words and all(word[0].isupper() or word.lower() in {"de", "do", "da", "dos", "das", "of"}
                                    for word in words) and words[0][0].isupper() and words[-1][0].isupper())
        if not proper and name not in _TEAM_ALIASES and name not in _TEAM_ALIASES.values():
            return None
    return _TEAM_ALIASES.get(name, name)


def is_competition_outcome_claim(claim) -> bool:
    """Scope guard, deliberately broader than the admissible claim grammar.

    A World Cup outcome with extra qualifiers stays inside this scope but
    cannot receive a relation unless the *entire* literal claim parses.
    """
    text = _text(claim)
    return bool(_SCOPE_COMP.search(text) and _OUTCOME_WORD.search(text))


def _safe(text):
    return bool(text and not (_OTHER_CATEGORY.search(text) or _UNASSERTED.search(text)
                             or any(character in text for character in ('?', '"', '“', '”', '«', '»'))))


def _frame(competition, winner, literal=None):
    name = _identity(winner, literal)
    years = re.findall(_YEAR, competition)
    return CompetitionOutcome(**_FRAME, year=int(years[0]), winner=name) if name and len(years) == 1 else None


_SUBJECT = r"(?P<winner>(?:(?:o|a|the) )?(?:(?:selecao(?: nacional)?(?: d[oae])?|national team of) )?" + _NAME + r")"
_COMP_CAPTURE = r"(?P<competition>" + _PT_COMP + r"|" + _EN_COMP + r")"
_PT_ACTIVE = re.compile(_SUBJECT + r" (?:venceu|ganhou|conquistou) (?:a |o titulo d[ae] |a taca d[ae] )" + _COMP_CAPTURE)
_PT_CHAMPION = re.compile(_SUBJECT + r" (?:foi|e|tornou-se) (?:a |o )?(?:campea|campeao)(?: mundial)? d[ae] " + _COMP_CAPTURE)
_PT_PASSIVE = re.compile(r"(?:a )?" + _COMP_CAPTURE + r" foi (?:vencida|conquistada) pel[oa] " + _SUBJECT)
_PT_INVERSE = re.compile(r"[oa] (?:campeao|campea) d[ae] " + _COMP_CAPTURE + r" foi " + _SUBJECT)
_EN_ACTIVE = re.compile(_SUBJECT + r" (?:won|has won) " + _COMP_CAPTURE)
_EN_CHAMPION = re.compile(_SUBJECT + r" (?:was|were|is|are)(?: crowned)? (?:the )?champions? of " + _COMP_CAPTURE)
_CLAIM_PATTERNS = (_PT_ACTIVE, _PT_CHAMPION, _PT_PASSIVE, _PT_INVERSE, _EN_ACTIVE, _EN_CHAMPION)

# A completed sports recap can use the historical present ("Zeta win ...").
# This is quote-only: the original claim grammar is not shortened to its
# first clause. Consume the entire literal recap, including its closed
# scorer/opponent/venue complement, rather than discarding arbitrary prose.
_RECAP_PLACE = r"[a-z]+(?: (?!in\b)[a-z]+){0,5}"
_SCORER = r"[a-z]+(?:[ -][a-z]+){0,2}"
_RECAP_SUBJECT = r"(?P<winner>(?:the )?(?:national team of )?[a-z]+(?:[ -][a-z]+){0,5}?)"
_EN_TITLE_RECAP = re.compile(
    _RECAP_SUBJECT + r" (?:has won|win|wins|won) " + _COMP_CAPTURE
    + r" thanks to (?P<scorer>" + _SCORER + r")[’']s (?:superb )?(?:extra-time )?winner"
    + r" against (?:the )?(?P<opponent>" + _NAME + r") at (?:the )?"
    + r"(?P<venue>" + _RECAP_PLACE + r")(?: in (?P<city>" + _NAME + r"))?\.?"
)
_PT_TITLE_RECAP = re.compile(
    r"com gol de (?P<scorer>" + _SCORER + r") no (?:primeiro|segundo) tempo"
    r"(?: da prorrogacao)?, os (?P<demonym>" + "|".join(_PT_TEAM_DEMONYMS)
    + r") conquistaram a (?P<competition>" + _PT_COMP + r")\.?"
)
_PT_RECAP_CONTEXT = re.compile(
    r"\b(?:veteran[oa]s?|masters?|lendas|amador[ae]s?|fictici[oa]s?|inventad[oa]s?|"
    r"imaginari[oa]s?|fantasia|simulad[oa]s?|simulacao|hipotese)\b"
)


def _portuguese_title_recap(quote):
    text, literal = _text(quote), _case_text(quote)
    match = _PT_TITLE_RECAP.fullmatch(text)
    if match is None or _PT_RECAP_CONTEXT.search(text):
        return None
    scorer = literal[match.start("scorer"):match.end("scorer")]
    if not scorer[0].isupper() or _identity(match["scorer"], scorer) is None:
        return None
    return _frame(match["competition"], _PT_TEAM_DEMONYMS[match["demonym"]])


# A single complete Spanish BODY assertion. Neither a host/year headline nor
# an ordinal title count alone supplies a winner or competition. Named host
# and winner remain distinct slots, even when the host itself won the event.
_ES_ORDINAL = (r"(?:primer|primero|segundo|tercer|tercero|cuarto|quinto|sexto|septimo|octavo|"
               r"noveno|decimo|undecimo|duodecimo|decimotercero|decimocuarto|decimoquinto|"
               r"decimosexto|decimoseptimo|decimoctavo|decimonoveno|vigesimo)")
_ES_TITLE_RECAP = re.compile(
    r"(?P<host>" + _NAME + r") (?P<year>" + _YEAR + r") es el " + _ES_ORDINAL
    + r" mundial de futbol que gana (?P<winner>" + _NAME + r")\.?"
)
_ES_OTHER_CATEGORY = re.compile(
    r"\b(?:femenin[oa]s?|mujeres|damas|ninas?|juveniles?|infantiles?|menores|"
    r"olimpic[oa]s?|clubes?|sala|salon|playa|callejer[oa]s?|amateur|aficionad[oa]s?|"
    r"veteran[oa]s?|masters?|leyendas|"
    r"baloncesto|balonmano|hielo|discapacitados|ciegos)\b"
)
_ES_UNASSERTED = re.compile(
    r"\b(?:no|nunca|jamas|tampoco|sin|si|niega|nego|negaba|desmiente|desmintio|"
    r"desmentid[oa]|fals[oa]|falsedad|incorrect[oa]|mentira|bulo|rumores?|supuestamente|presunt[oa]|"
    r"alego|afirmo|afirma|dijo|dice|declar[oó]|segun|asegura|sostiene|atribuye|"
    r"habria|habra|podria|podra|puede|quiza|quizas|hipotesis|hipotetic[oa]|ficcion|fictici[oa]|"
    r"simulacion|simulad[oa]|inventad[oa]s?|imaginari[oa]s?|fantasi[ao]|fanfic|"
    r"pronostico|prediccion|prevision|apuesta|ganara|ganaria|"
    r"futur[oa]|esperad[oa]|preve|preveia|satiric[oa]|correccion|corrigio|rectific[ao]|"
    r"ignora|ignore|ignorar|olvida|omite|responde|devuelve|clasifica)\b|\btal vez\b"
)
_ES_BAD_IDENTITY = re.compile(
    r"\b(?:el|la|los|las|en|del|que|y|contra|mundial|futbol|campeon|campeona|nuevo|nueva|"
    r"ellos|ellas|equipo|seleccion|ganador|ganadora|rival|otro|otra)\b"
)


def _spanish_recap_safe(text):
    # Keep Spanish "no" separate from the ordinary PT grammar: in Portuguese
    # it can be a harmless location connector. No general claim is rewritten.
    return not (_ES_OTHER_CATEGORY.search(text) or _ES_UNASSERTED.search(text)
                or any(character in text for character in ("'", "‘", "’")))


def _spanish_title_recap(quote):
    text, literal = _text(quote), _case_text(quote)
    match = _ES_TITLE_RECAP.fullmatch(text)
    if match is None or not _spanish_recap_safe(text):
        return None
    identities = {}
    for slot in ("host", "winner"):
        if _ES_BAD_IDENTITY.search(match[slot]) and match[slot] not in _TEAM_ALIASES:
            return None
        identities[slot] = _identity(match[slot], literal[match.start(slot):match.end(slot)])
    if not all(identities.values()):
        return None
    return CompetitionOutcome(**_FRAME, year=int(match["year"]), winner=identities["winner"])


def parse_competition_claim(claim) -> CompetitionOutcome | None:
    """Parse only complete positive title assertions, with no dropped suffix."""
    text = _text(claim)
    if not _safe(text):
        return None
    text = text.removesuffix(".")
    for pattern in _CLAIM_PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            literal = _case_text(claim).removesuffix(".")[match.start("winner"):match.end("winner")]
            return _frame(match["competition"], match["winner"], literal)
    return None


def competition_lead_priority(claim, lead) -> int:
    """Order discovery only; never derive a winner or evidence from a title.

    A first-party page about commemorative coins must not outrank a match
    recap solely because its host is official. Keep every candidate eligible
    and avoid using the claimed team to select agreeable search results.
    Ambiguous/qualified claims retain their existing discovery order.
    """
    parsed = parse_competition_claim(claim)
    if parsed is None:
        return 0
    text = _text(lead).replace("-", " ").replace("_", " ")
    if not _SCOPE_COMP.search(text):
        return 2
    years = set(re.findall(_YEAR, text))
    ancillary = re.search(
        r"\b(?:moedas?|coins?|comemorativ[oa]s?|commemorative|numismatic[oa]s?|"
        r"numismatic|cedulas?|banknotes?|circular|resolucao|ingressos?|tickets?)\b", text)
    if _OTHER_CATEGORY.search(text) or ancillary or (years and str(parsed.year) not in years):
        return 3
    if str(parsed.year) in years:
        return 0 if _OUTCOME_WORD.search(text) else 1
    return 2


_FINAL_COMP = re.compile(r"\b(?:final|grande decisao|grand final|championship final) (?:da|do|of (?:the )?)\s*(?:" + _PT_COMP + r"|" + _EN_COMP + r")\b")
_OTHER_COMP = re.compile(r"\b(?:copa|cup|campeonato|championship|torneio|tournament|league|liga|mundial)\b")
_ORDINAL = r"(?:(?:primeiro|segundo|terceiro|quarto|quinto|sexto|setimo|oitavo|nono|decimo|\d+[oa]?) )?"
_PT_TITLE_TAIL = re.compile(
    r"(?: por \d+ (?:a|x) \d+)?"
    r"(?:,? com (?:o |um )?gol (?:do|da|de) (?:jovem )?(?P<scorer>" + _SCORER + r")(?: na prorrogacao)?)?"
    r"(?: na prorrogacao)?,? e (?:conquistou|ganhou|levou) (?:o |seu |a |sua )?" + _ORDINAL
    + r"(?:titulo|taca)(?: na historia das copas| do torneio| da competicao| dessa edicao)?\.?"
)
_EN_TITLE_TAIL = re.compile(
    r"(?:(?: by)? \d+\s*[-–:]\s*\d+)?(?: in extra time)?,? and (?:won|claimed|lifted) (?:the |its )?"
    r"(?:title|trophy)(?: of the tournament| of the competition| in that edition)?\.?"
)
_LOCAL_PT_WINNER = re.compile(
    r"(?:na ocasiao,? |nessa final,? |na final,? |entao,? )?" + _SUBJECT
    + r" (?:venceu|derrotou|bateu) (?:a |o )?(?P<opponent>" + _NAME + r")(?= (?:por|pelo)|,| e )"
)
_LOCAL_PT_CHAMPION = re.compile(
    r"(?:na ocasiao,? |nessa edicao,? |nesse torneio,? )?" + _SUBJECT
    + r" (?:foi|tornou-se|sagrou-se) (?:a |o )?(?:campea|campeao) (?:do torneio|da competicao|dessa edicao)\.?"
)
_LOCAL_EN_WINNER = re.compile(
    r"(?:in (?:that|the) final,? |on that occasion,? )?" + _SUBJECT
    + r" (?:beat|defeated) (?:the )?(?P<opponent>" + _NAME + r")(?= \d| by |,| and )"
)
_LOCAL_EN_CHAMPION = re.compile(
    r"(?:in that edition,? )?" + _SUBJECT
    + r" (?:was|were)(?: crowned)? (?:the )?champions? of (?:the tournament|the competition|that edition)\.?"
)
_FINALISTS = re.compile(r"\b(?:foi entre|entre|between|reuniu|com|foi|opos|teve) (?:a |o |the )?(?P<first>" + _NAME
                       + r") (?:e|and|contra|versus|vs) (?:a |o |the )?(?P<second>" + _NAME + r")(?=[.,]|$)")
_FINALISTS_FIRST = re.compile(r"^(?:a |o |the )?(?P<first>" + _NAME + r") (?:e|and) (?:a |o |the )?(?P<second>"
                             + _NAME + r") (?:disputaram|jogaram|fizeram|faziam|played|contested) (?:a |the )?final\b")
_PARTICIPANTS = re.compile(r"\b(?:entre|between|reuniu|opos|teve|disputaram|jogaram|fizeram|faziam|played|contested|"
                           r"participantes|participants|finalistas|duelaram|enfrentaram)\b")
_PROPER_PAIR = re.compile(r"\b[A-Z][A-Za-z-]*(?: [A-Z][A-Za-z-]*){0,3} (?:e|and|contra|versus|vs) [A-Z][A-Za-z-]*\b")
_ANCHOR_LOCATION = re.compile(
    r" (?:aconteceu|ocorreu|foi realizada|foi disputada|happened|took place|was played)"
    r" (?:no|na|em|in|at) (?P<venue>" + _NAME + r")\.?"
)
_ANCHOR_PARTICIPANTS = re.compile(
    r" (?:reuniu|opos|teve|foi entre|foi|was between) (?:a |o |the )?(?P<first>" + _NAME
    + r") (?:e|and|contra|versus|vs) (?:a |o |the )?(?P<second>" + _NAME
    + r")(?:, (?:no|na|em|in|at) (?P<venue>" + _NAME + r"))?\.?"
)
_ANCHOR_PAIR_PREFIX = re.compile(
    r"(?:a |o |the )?(?P<first>" + _NAME + r") (?:e|and) (?:a |o |the )?(?P<second>"
    + _NAME + r") (?:disputaram|jogaram|fizeram|faziam|played|contested) (?:a |the )?"
)
_ANCHOR_VENUE_ONLY = re.compile(r"(?: (?:no|na|em|in|at) (?P<venue>" + _NAME + r"))?\.?")
_ANCHOR_NARRATIVE = re.compile(
    r"(?:(?:da|do) (?P<source>" + _NAME + r")\s*adicionar (?P<repeated_source>" + _NAME + r") ao )?"
    r"ha (?:\d+|um|dois|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|vinte) anos, "
    r"(?:o|a) (?P<venue>" + _NAME + r") era palco da "
)
_ANCHOR_NARRATIVE_TAIL = re.compile(
    r"(?:, e fechava com chave de ouro um dos mundiais mais (?:vibrantes|emocionantes|disputados) "
    r"ja presenciad[oa]s? pelos torcedores)?\.?"
)
_ANCHOR_GENERIC_VENUE = re.compile(r"(?:o estadio|a arena) (?:foi|era) palco da ")
_ANCHOR_NAMED_VENUE = re.compile(r"(?:(?:o|a) )?(?P<venue>" + _NAME + r") (?:foi|era) palco da ")


def _anchor_names_valid(match, literal):
    return all(_identity(value, literal[match.start(group):match.end(group)]) is not None
               for group, value in match.groupdict().items() if value is not None)


def _final_anchor_bound(anchor, literal):
    """A closed final clause, never a year followed by unrestricted prose.

    Both sides of the named final are consumed. A later edition, another
    decision or a new subject cannot hide in the same anchor sentence.
    """
    final = _FINAL_COMP.search(anchor)
    if not final:
        return False
    prefix, suffix = anchor[:final.start()], anchor[final.end():]
    literal_prefix, literal_suffix = literal[:final.start()], literal[final.end():]
    if prefix in {"a ", "the ", ""}:
        match = _ANCHOR_LOCATION.fullmatch(suffix) or _ANCHOR_PARTICIPANTS.fullmatch(suffix)
        return bool(match and _anchor_names_valid(match, literal_suffix))
    pair = _ANCHOR_PAIR_PREFIX.fullmatch(prefix)
    if pair:
        tail = _ANCHOR_VENUE_ONLY.fullmatch(suffix)
        return bool(tail and _anchor_names_valid(pair, literal_prefix) and _anchor_names_valid(tail, literal_suffix))
    # An explicitly named venue or the literal stadium/arena can directly
    # govern the final without a relative-time introduction. The whole
    # clause remains consumed, including its bounded narrative complement.
    if _ANCHOR_NARRATIVE_TAIL.fullmatch(suffix):
        if _ANCHOR_GENERIC_VENUE.fullmatch(prefix):
            return True
        venue = _ANCHOR_NAMED_VENUE.fullmatch(prefix)
        if venue and _anchor_names_valid(venue, literal_prefix):
            return True
    narrative = _ANCHOR_NARRATIVE.fullmatch(prefix)
    return bool(narrative and _anchor_names_valid(narrative, literal_prefix)
                and narrative["source"] == narrative["repeated_source"]
                and _ANCHOR_NARRATIVE_TAIL.fullmatch(suffix))


def _sentences(text):
    # Abbreviations are not repaired by silently dropping text; uncertain
    # boundaries/more than three sentences conservatively fail the binding.
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _quote_frame(quote):
    text = _text(quote)
    if not _safe(text) or _BAD_STAGE.search(text):
        return None
    sentences = _sentences(text)
    if not 1 <= len(sentences) <= 3:
        return None
    direct = parse_competition_claim(quote)
    if direct:
        return direct
    spanish_recap = _spanish_title_recap(quote)
    if spanish_recap:
        return spanish_recap
    portuguese_recap = _portuguese_title_recap(quote)
    if portuguese_recap:
        return portuguese_recap
    recap = _EN_TITLE_RECAP.fullmatch(text)
    if recap:
        literal = _case_text(quote)
        named = {key: _identity(recap[key], literal[recap.start(key):recap.end(key)])
                 for key in ("winner", "scorer", "opponent", "venue", "city") if recap[key] is not None}
        if (all(named.values()) and named["winner"] != named["opponent"]
                and len(re.findall(_YEAR, text)) == 1):
            return _frame(recap["competition"], recap["winner"],
                          literal[recap.start("winner"):recap.end("winner")])
        return None
    competitions = list(_COMP.finditer(text))
    # Exactly one explicit competition/edition avoids borrowing a title from
    # another tournament or selecting one of several repeated events.
    if len(competitions) != 1 or len(re.findall(_YEAR, text)) != 1:
        return None
    competition = competitions[0]
    anchor_index = next((index for index, sentence in enumerate(sentences)
                         if _COMP.search(sentence)), None)
    if anchor_index is None:
        return None
    anchor = sentences[anchor_index]
    # A nearby final of a different tournament cannot bind the World Cup.
    # No additional competition reference may compete with this antecedent.
    literal_sentences = _sentences(_case_text(quote))
    if not _final_anchor_bound(anchor, literal_sentences[anchor_index]) or _OTHER_COMP.search(_COMP.sub("", anchor)):
        return None
    finalists = _FINALISTS.search(anchor) or _FINALISTS_FIRST.search(anchor)
    pair = {_identity(finalists["first"]), _identity(finalists["second"])} if finalists else None
    if pair and (None in pair or len(pair) != 2):
        return None
    if not pair and (_PARTICIPANTS.search(anchor) or _PROPER_PAIR.search(literal_sentences[anchor_index])):
        return None
    frames = []
    for index, sentence in enumerate(sentences):
        if index <= anchor_index:
            if index != anchor_index and (_OTHER_COMP.search(sentence) or _OUTCOME_WORD.search(sentence)):
                return None
            continue
        # A new decision/edition can be introduced without repeating its
        # competition name or year. Only the immediately following sentence
        # may inherit this final's competition/edition; never skip a bridge.
        if index != anchor_index + 1:
            if _OTHER_COMP.search(sentence) or _OUTCOME_WORD.search(sentence):
                return None
            continue
        # The local assertion must itself name the winner. A final with two
        # participants, a score, or a remembered historical winner is not one.
        champion = _LOCAL_PT_CHAMPION.fullmatch(sentence) or _LOCAL_EN_CHAMPION.fullmatch(sentence)
        if champion:
            literal = literal_sentences[index][champion.start("winner"):champion.end("winner")]
            frame = _frame(competition[0], champion["winner"], literal)
            if pair and (not frame or frame.winner not in pair):
                return None
            frames.append(frame)
            continue
        winner = _LOCAL_PT_WINNER.match(sentence) or _LOCAL_EN_WINNER.match(sentence)
        title_tail = ((_PT_TITLE_TAIL.fullmatch(sentence[winner.end():]) or _EN_TITLE_TAIL.fullmatch(sentence[winner.end():]))
                      if winner else None)
        if winner and title_tail:
            if title_tail.re is _PT_TITLE_TAIL and title_tail["scorer"]:
                scorer_start = winner.end() + title_tail.start("scorer")
                scorer_end = winner.end() + title_tail.end("scorer")
                if not _identity(title_tail["scorer"], literal_sentences[index][scorer_start:scorer_end]):
                    return None
            literal = literal_sentences[index][winner.start("winner"):winner.end("winner")]
            opponent_literal = literal_sentences[index][winner.start("opponent"):winner.end("opponent")]
            opponent = _identity(winner["opponent"], opponent_literal)
            frame = _frame(competition[0], winner["winner"], literal)
            if not opponent or not frame or frame.winner == opponent:
                return None
            if pair and {frame.winner, opponent} != pair:
                return None
            frames.append(frame)
            continue
        if _OTHER_COMP.search(sentence) or _OUTCOME_WORD.search(sentence):
            return None
    return frames[0] if len(frames) == 1 and frames[0] is not None else None


def competition_outcome_relation(claim, quote, context="") -> Relation | None:
    """Compare one complete claim with one caller-validated BODY window.

    Returns a proposed relation only when both complete title frames match
    competition, year and category. Different winners then refute the claim;
    a different year/category or incomplete literal evidence always abstains.
    The caller still validates literal provenance, independent sources and
    its usual nonassertion/instruction guards before admitting a model vote.
    """
    context_text = _text(context)
    if context_text and not _safe(context_text):
        return None
    if _ES_TITLE_RECAP.fullmatch(_text(quote)) and not _spanish_recap_safe(context_text):
        return None
    if _PT_TITLE_RECAP.fullmatch(_text(quote)) and _PT_RECAP_CONTEXT.search(context_text):
        return None
    claimed, observed = parse_competition_claim(claim), _quote_frame(quote)
    if not claimed or not observed:
        return None
    if (claimed.competition, claimed.year, claimed.category) != (observed.competition, observed.year, observed.category):
        return None
    return "supports" if claimed.winner == observed.winner else "refutes"
