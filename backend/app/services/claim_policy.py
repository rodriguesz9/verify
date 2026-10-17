"""ClaimReview decisions, not LLM guesses. Exact matching sacrifices recall.

Similarity cannot reliably preserve negation, quantities, dates or quotation.
"""
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit

POLICY_VERSION = "2026-10-10.1"
# Editorial families: related sites never count twice. Publishers can still err.
PUBLISHERS = {
    "aosfatos.org": "aosfatos", "boatos.org": "boatos",
    "lupa.uol.com.br": "lupa", "agencialupa.org": "lupa",
    "estadao.com.br": "estadao", "checamos.afp.com": "afp",
    "factcheck.afp.com": "afp", "reuters.com": "reuters",
    "apnews.com": "ap", "fullfact.org": "fullfact",
}
RATINGS = {"true": "supported", "verdadeiro": "supported", "verdadeira": "supported",
           "false": "refuted", "falso": "refuted", "falsa": "refuted"}
RELATIVE_TIME = re.compile(r"\b(hoje|ontem|amanh[ãa]|agora|nesta semana|neste m[eê]s|neste ano|este ano|atualmente|recentemente|"
                           r"semana passada|m[eê]s passado|ano passado|semana que vem|neste momento|[uú]ltim[oa]s? (dias?|horas?)|"
                           r"today|yesterday|tomorrow|now|currently|this week|last week|this year)\b", re.I)
_LITERAL_SEPARATOR = re.compile(r"(?<=[.!?])[\s\u200e\u200f]+|\n+")
_TITLE_ABBREVIATION = re.compile(r"\b(?:dr|dra|sr|sra|prof|profa)\.$", re.I)
_MONTH_ABBREVIATION = re.compile(r"\b(?:jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\.$", re.I)


def normalize_claim(text: str) -> str:
    # Preserve accents (avó/avô), negation, numbers and interior punctuation.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).casefold()).strip().removesuffix(".").strip()


def publisher_family(url: str | None) -> str | None:
    try:
        parsed = urlsplit(url or "")
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
            return None
        return next((family for domain, family in PUBLISHERS.items()
                     if host == domain or host.endswith("." + domain)), None)
    except ValueError:
        return None


def input_claims(text: str) -> list[str]:
    # Literal slices only. Do not separate a person's title from their name,
    # or alter internal punctuation in decimals/dates. All slices need coverage.
    parts, start = [], 0
    for separator in _LITERAL_SEPARATOR.finditer(text):
        if _TITLE_ABBREVIATION.search(text[:separator.start()]):
            continue
        # Keep abbreviated calendar dates literal. Splitting "Sept. 26" into
        # separate claims produces a meaningless numeric search and discards
        # the relation between the event and its date. A following number is
        # required; a month abbreviation cannot swallow an unrelated sentence.
        if (_MONTH_ABBREVIATION.search(text[:separator.start()])
                and re.match(r"\d{1,4}\b", text[separator.end():])):
            continue
        part = text[start:separator.start()].strip()
        if part:
            parts.append(part)
        start = separator.end()
    last = text[start:].strip()
    if last:
        parts.append(last)
    return parts


def _review_date_ok(value, now):
    if not isinstance(value, str):
        return False
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
        return date <= now
    except ValueError:
        return False


def decide_claim(text: str, reviews: list[dict], now: datetime) -> dict:
    matched, excluded = [], []
    ambiguous = bool(RELATIVE_TIME.search(text)) or any(char in text for char in ('?', '"', '“', '”', '«', '»'))
    for review in reviews:
        if not isinstance(review, dict):
            continue
        family = publisher_family(review.get("url"))
        relation = RATINGS.get(str(review.get("rating", "")).strip().casefold())
        same = normalize_claim(text) == normalize_claim(str(review.get("claim_text", "")))
        reason = (
            "Afirmação diferente; similaridade não basta." if not same else
            "Contexto relativo ou citação/pergunta exige revisão humana." if ambiguous else
            "Resultado sem origem de recuperação verificável." if review.get("retrieval_provider") != "google_fact_check" else
            "Publicador fora da lista editorial ou URL não segura." if not family else
            "Data da checagem ausente, inválida ou futura." if not _review_date_ok(review.get("review_date"), now) else
            "Avaliação ambígua/mista; não convertida em verdadeiro ou falso." if not relation else None)
        item = {**review, "publisher_family": family, "relation": relation,
                "match_method": "exact_normalized" if same else "unmatched"}
        if reason:
            excluded.append({**item, "exclusion_reason": reason})
        else:
            matched.append(item)
    supported = {r["publisher_family"] for r in matched if r["relation"] == "supported"}
    refuted = {r["publisher_family"] for r in matched if r["relation"] == "refuted"}
    status = ("conflicting" if supported and refuted else
              "supported" if len(supported) >= 2 else "refuted" if len(refuted) >= 2 else "unverified")
    reasons = {
        "supported": "Duas famílias editoriais distintas avaliaram a mesma afirmação como verdadeira.",
        "refuted": "Duas famílias editoriais distintas avaliaram a mesma afirmação como falsa.",
        "conflicting": "Checagens correspondentes discordam; conclusão exige revisão humana.",
        "unverified": "Faltam duas checagens editoriais distintas, válidas e correspondentes para concluir."}
    return {"claim": text, "status": status, "explanation": reasons[status],
            "evidence": matched, "excluded_evidence": excluded,
            "supporting_publishers": sorted(supported), "refuting_publishers": sorted(refuted)}


def text_report(text: str, reviews: list[dict], scam: dict | None = None, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    segments = input_claims(text)
    whole = decide_claim(text, reviews, now)
    whole_matched = whole["status"] in {"supported", "refuted", "conflicting"}
    decisions = [whole] if whole_matched else [decide_claim(part, reviews, now) for part in segments[:5]]
    complete = len(segments) <= 5 or whole_matched
    states = {item["status"] for item in decisions}
    truth = ("supported" if complete and states == {"supported"} else
             "refuted" if complete and states == {"refuted"} else
             "conflicting" if "conflicting" in states else
             "mixed" if {"supported", "refuted"} <= states else "unverified")
    descriptions = {
        "supported": "A informação foi corroborada por checagens editoriais distintas para a mesma afirmação. Isso não certifica a autenticidade de uma mídia.",
        "refuted": "A afirmação foi refutada por checagens editoriais distintas. Abra as fontes para consultar os argumentos e o contexto da refutação.",
        "conflicting": "Checagens correspondentes discordaram. É necessária revisão humana antes de concluir.",
        "mixed": "Há afirmações corroboradas e refutadas. Não cabe um único rótulo de verdadeiro ou falso para toda a mensagem.",
        "unverified": "Não há evidência correspondente suficiente para afirmar que a mensagem seja verdadeira ou falsa."}
    report = {"verdict": "Authentic" if truth == "supported" else "False" if truth == "refuted" else "Suspicious",
              "score": 90 if truth == "supported" else 10 if truth == "refuted" else 50,
              "score_semantics": "legacy_decision_index_not_probability",
              "veracity_status": truth, "authenticity_status": "not_applicable",
              "analysis_status": "partial" if truth in {"supported", "refuted"} else "inconclusive",
              "summary": descriptions[truth], "plain_explanation": descriptions[truth],
              "whatsapp_share_text": "🔎 Verify: " + descriptions[truth],
              "elderly_tip": "Confira fontes e data. Confirme pedidos financeiros por um canal conhecido.",
              "red_flags": [], "positives": [], "claims": [item["claim"] for item in decisions],
              "claim_assessments": decisions, "fact_checks": reviews,
              "confidence": None, "authenticity_percentage": None,
              "semantic_score": None, "sensationalism": None, "domain_score": None,
              "policy_version": POLICY_VERSION, "model_used": "retrieved_evidence_policy",
              "limitations": ["Classificação atribuída às checagens consultadas; fontes também podem errar ou ser atualizadas.",
                              "Correspondência exata conservadora pode deixar paráfrases corretas sem conclusão.",
                              "Notícia relacionada, estilo e concordância entre modelos não provam verdade ou falsidade."]}
    if not complete:
        report["limitations"].append("Limite de cinco segmentos: mensagem não foi integralmente checada.")
    if scam and scam.get("is_scam"):
        report.update(verdict="Scam", score=15, analysis_status="partial",
                      summary="Há sinais de possível golpe. Isso não comprova falsidade de cada afirmação ou identidade do remetente.")
        report["plain_explanation"] = report["summary"]
        report["whatsapp_share_text"] = "⚠️ Verify: " + report["summary"]
        report["red_flags"] = [f"Alerta de Golpe: {p['category']} - {p['description']}" for p in scam.get("detected_patterns", [])]
    return report
