"""Bounded lexical admission of news CONTEXT, never evidence of truth.

Literal sentence anchors deliberately sacrifice recall (synonyms, incomplete
snippets). Generated search hints, publisher reputation and URL domains cannot
make an unrelated result relevant. No snippet is rewritten or fact-check used.
"""
import re
import unicodedata

NEWS_RELEVANCE_VERSION = "literal_context_anchors_v1"
MAX_CONTEXT_ITEMS = 15  # three searches, five provider results each
_GENERIC = set("a o as os um uma uns umas de da do das dos em no na nos nas e ou que por para com sem se ao aos pelo pela pelos pelas seu sua seus suas este esta isso esse essa ser sao foi era esta tem ter ha mais como quando onde agora hoje ontem amanha nao nem nunca jamais falso falsa falsos falsas verdade verdadeiro verdadeira noticia noticias veja saiba confira confirme canal oficial pague pagar noticia diz disse sobre".split())
_NEGATION = {"nao", "nem", "nunca", "jamais", "falso", "falsa", "falsos", "falsas"}
_NUMBER = re.compile(r"\d+(?:[.,:/-]\d+)*")


def _normal(value):
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(char))


def _parts(value):
    if not isinstance(value, str):
        return []
    # Do not split a decimal or date at its internal punctuation.
    return [part for part in re.split(r"(?<=[!?])\s+|(?<!\d)\.\s+|\n+", _normal(value[:5000])) if part.strip()][:20]


def _features(part):
    words = set(re.findall(r"[a-z]+", part))
    anchors = {word for word in words if len(word) >= 3 and word not in _GENERIC}
    numbers = set(_NUMBER.findall(part))
    return anchors, bool(words & _NEGATION), numbers


def filter_context_news(text, items):
    """Return admitted items and counts; absence means no usable news context.

    Matching anchors do NOT establish semantic equivalence, authenticity or
    truth. Explicitly different numbers/negation are excluded conservatively;
    missing numeric details alone do not exclude otherwise related context.
    """
    literal = [_features(part) for part in _parts(text)]
    kept = []
    reasons = {"insufficient_literal_anchors": 0, "negation_mismatch": 0,
               "numeric_mismatch": 0, "invalid_item": 0}
    for item in items[:MAX_CONTEXT_ITEMS]:
        if not isinstance(item, dict):
            reasons["invalid_item"] += 1
            continue
        candidates = [_features(part) for field in ("title", "snippet")
                      for part in _parts(item.get(field, ""))]
        reason = "insufficient_literal_anchors"
        matched = False
        for anchors, negative, numbers in literal:
            for other, other_negative, other_numbers in candidates:
                if len(anchors & other) < 2:
                    continue
                if negative != other_negative:
                    reason = "negation_mismatch"
                    continue
                # A differing explicit amount/date is not a matching context
                # slice. Do not infer any quantity omitted by a search snippet.
                if numbers and other_numbers and not numbers <= other_numbers:
                    reason = "numeric_mismatch"
                    continue
                matched = True
                break
            if matched:
                break
        if matched:
            kept.append(item)
        else:
            reasons[reason] += 1
    return kept, {"version": NEWS_RELEVANCE_VERSION, "decision_role": "context_only",
                  "minimum_literal_anchors": 2, "candidates_checked": min(len(items), MAX_CONTEXT_ITEMS),
                  "excluded_count": sum(reasons.values()), "excluded_reasons": reasons,
                  "unprocessed_count": max(0, len(items) - MAX_CONTEXT_ITEMS),
                  "limitation": "Correspondência lexical conservadora, não equivalência semântica nem prova de verdade; sinônimos e resumos incompletos podem ser excluídos."}
