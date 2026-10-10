"""Bounded literal retrieval queries; selection never changes checked claims.

Extractors may prioritize a sentence, but cannot paraphrase it or remove its
negation, amounts, dates or surrounding qualifiers. Query audit contains counts
and methods only, not user text. No provider is called by this helper.
"""
from app.services.claim_policy import input_claims, normalize_claim

QUERY_PLAN_VERSION = "literal_sentence_queries_v1"
MAX_FACT_CHECK_QUERY_CHARS = 5000


def build_fact_check_queries(text: str, extracted_claims, limit: int = 5) -> tuple[list[str], dict]:
    """Prioritize extracted literal sentences, retaining a full-input fallback.

    A partial literal hint selects its entire containing sentence. It is only
    a search hint, never a replacement proposition for ``claim_assessments``.
    With at least two query slots, reserve one for the complete input when it
    fits the provider's limit. Oversize queries are omitted, never truncated.
    """
    if not isinstance(text, str):
        raise TypeError("Query input must be text.")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Query limit must be a positive integer.")

    whole = text.strip()
    segments = input_claims(text)
    hints = extracted_claims if isinstance(extracted_claims, (list, tuple)) else []
    extracted_sentences = []
    valid_hints = rejected_hints = 0
    for hint in hints:
        if not isinstance(hint, str) or not hint.strip() or hint.strip() not in text:
            rejected_hints += 1
            continue
        literal = hint.strip()
        parents = [segment for segment in segments if literal in segment]
        if not parents:
            # A cross-sentence extraction cannot discard the surrounding input.
            # The complete literal input remains a separate fallback candidate.
            rejected_hints += 1
            continue
        valid_hints += 1
        extracted_sentences.extend(parents)

    candidates = {}

    def add_candidate(query, method):
        if query:
            candidates.setdefault(normalize_claim(query), {"text": query, "method": method})

    for sentence in extracted_sentences:
        add_candidate(sentence, "extracted_literal_sentence")
    add_candidate(whole, "whole_literal_input")
    for sentence in segments:
        add_candidate(sentence, "literal_sentence_fallback")

    admissible = {key: candidate for key, candidate in candidates.items()
                  if len(candidate["text"]) <= MAX_FACT_CHECK_QUERY_CHARS}
    selected = {}
    whole_key = normalize_claim(whole)
    reserve_whole = limit > 1 and whole_key in admissible
    hint_slots = limit - 1 if reserve_whole else limit
    for key, candidate in admissible.items():
        if candidate["method"] == "extracted_literal_sentence" and len(selected) < hint_slots:
            selected[key] = candidate
    if reserve_whole:
        selected.setdefault(whole_key, admissible[whole_key])
    for key, candidate in admissible.items():
        if len(selected) >= limit:
            break
        selected.setdefault(key, candidate)

    queried_segments = sum(normalize_claim(segment) in selected for segment in segments)
    audit = {
        "version": QUERY_PLAN_VERSION,
        "decision_role": "retrieval_only",
        "limit": limit,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "omitted_count": len(candidates) - len(selected),
        "oversize_candidate_count": len(candidates) - len(admissible),
        "extracted_received_count": len(hints),
        "extracted_valid_count": valid_hints,
        "extracted_rejected_count": rejected_hints,
        "literal_segment_count": len(segments),
        "literal_segments_queried": queried_segments,
        "literal_segments_not_queried_separately": len(segments) - queried_segments,
        "whole_text_queried": bool(whole) and whole_key in selected,
        "query_methods": [candidate["method"] for candidate in selected.values()],
        "truncated": False,
    }
    return [candidate["text"] for candidate in selected.values()], audit
