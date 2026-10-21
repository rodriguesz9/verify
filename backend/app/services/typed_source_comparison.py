"""Pure, bounded source-review matrix for complete, narrowly typed claims.

This module only selects immutable IDs from already prepared BODY passages.
It performs no retrieval, provider calls, source-family vote or verdict. The
caller must still decode the returned v2 JSON strictly and run its existing
assessment and aggregation. ``None`` means use the ordinary comparison path;
it never means that an unresolved but admissible passage was insufficient.
"""
import json
import re

from app.services.competition_relations import competition_outcome_relation, parse_competition_claim
from app.services.launch_relations import _frame as _launch_frame, launch_date_relation
from app.services.monetary_decisions import copom_record_relation, parse_copom_claim


COMPARISON_METHOD = "literal_typed_rules_v1"
_RELATIONS = ("supports", "refutes")
_MAX_CLAIMS = 5
_MAX_SOURCES = 3
_MAX_PASSAGES = 8
_MAX_BODY_CHARACTERS = 18000


def _claim_kind(claim):
    if parse_copom_claim(claim) is not None:
        return "copom_record"
    launch = _launch_frame(claim)
    # Vehicle/payload launches can recur. Keep this first deterministic path
    # restricted to the complete, explicitly numbered mission/flight frame.
    if launch is not None and launch.identity_kind == "mission" and launch_date_relation(claim, claim) == "supports":
        return "mission_launch"
    if parse_competition_claim(claim) is not None:
        return "competition_outcome"
    return None


def _literal_relation(kind, claim, passage):
    if kind == "copom_record":
        # Never infer an official decision's date from a generic news page,
        # hostname, headline or bare publication date. The helper revalidates
        # the exact proof; absence/invalid proof remains an unknown reading.
        proof = passage.get("official_record")
        return copom_record_relation(claim, passage["quote"], proof) if isinstance(proof, dict) else None
    if kind == "mission_launch":
        return launch_date_relation(claim, passage["quote"])
    return competition_outcome_relation(claim, passage["quote"], passage["context"])


def _valid_inputs(claims, sources):
    if (not isinstance(claims, list) or not 1 <= len(claims) <= _MAX_CLAIMS
            or not isinstance(sources, list) or not 1 <= len(sources) <= _MAX_SOURCES):
        return False
    claim_ids, source_ids, excerpt_ids = set(), set(), set()
    for claim in claims:
        if (not isinstance(claim, dict) or not isinstance(claim.get("claim_id"), str)
                or re.fullmatch(r"c[1-5]", claim["claim_id"]) is None or claim["claim_id"] in claim_ids
                or not isinstance(claim.get("claim"), str) or not 1 <= len(claim["claim"]) <= 5000):
            return False
        claim_ids.add(claim["claim_id"])
    body_characters = 0
    for source in sources:
        if (not isinstance(source, dict) or not isinstance(source.get("source_id"), str)
                or re.fullmatch(r"s[1-3]", source["source_id"]) is None or source["source_id"] in source_ids
                or not isinstance(source.get("retrieved_at"), str) or not 1 <= len(source["retrieved_at"]) <= 64
                or not isinstance(source.get("passages"), list) or not 1 <= len(source["passages"]) <= _MAX_PASSAGES):
            return False
        source_id = source["source_id"]
        source_ids.add(source_id)
        for passage in source["passages"]:
            if (not isinstance(passage, dict) or not isinstance(passage.get("excerpt_id"), str)
                    or re.fullmatch(re.escape(source_id) + r":e[1-9]\d{0,3}(?:-[1-9]\d{0,3})?", passage["excerpt_id"]) is None
                    or passage["excerpt_id"] in excerpt_ids
                    or ("source_id" in passage and passage["source_id"] != source_id)
                    or not isinstance(passage.get("quote"), str) or not 1 <= len(passage["quote"]) <= 1200
                    or not isinstance(passage.get("context"), str) or not passage["context"]):
                return False
            excerpt_ids.add(passage["excerpt_id"])
            body_characters += len(passage["quote"]) + len(passage["context"])
            if body_characters > _MAX_BODY_CHARACTERS:
                return False
    return True


def typed_review_matrix(claims, sources, guard, window_guard):
    """Return ``(strict_v2_json, deterministic_coverage)`` or ``None``.

    ``claims`` and ``sources`` are the server's prepared bounded lists.
    ``guard(claim_text, passage, relation, retrieved_at)`` admits a direction
    only by returning None. ``window_guard(claim_text, quote)`` additionally
    must return True for a BODY window. Both directions and every selected
    passage are examined, even after finding a representative or an unknown
    reading. At most one literal ID per source/direction is selected, keeping
    at most six evidence entries per claim without losing within-source
    contradictions.

    Unknown full-claim types, an unresolved but admissible passage, an
    admissible direction opposing the typed relation, or an invalid input
    contract make the whole matrix fall back. Only a passage rejected in
    both directions can be audited as insufficient without a typed reading.
    """
    if not callable(guard) or not callable(window_guard) or not _valid_inputs(claims, sources):
        return None
    kinds = [_claim_kind(item["claim"]) for item in claims]
    if any(kind is None for kind in kinds):
        return None
    rows, needs_fallback = [], False
    reviewed_pairs = reviewed_passages = selected_count = rejected_count = 0
    try:
        for item, kind in zip(claims, kinds):
            claim, reviews = item["claim"], []
            for source in sources:
                representatives = {}
                for passage in source["passages"]:
                    proposed = _literal_relation(kind, claim, passage)
                    admitted = {relation: guard(claim, passage, relation, source["retrieved_at"]) is None
                                for relation in _RELATIONS}
                    if passage.get("body_window") and window_guard(claim, passage["quote"]) is not True:
                        admitted = dict.fromkeys(_RELATIONS, False)
                    reviewed_passages += 1
                    if not any(admitted.values()):
                        rejected_count += 1
                    if proposed is None:
                        needs_fallback |= any(admitted.values())
                        continue
                    opposite = "refutes" if proposed == "supports" else "supports"
                    if proposed not in _RELATIONS or admitted[opposite]:
                        needs_fallback = True
                    elif admitted[proposed]:
                        representatives.setdefault(proposed, passage["excerpt_id"])
                evidence = [{"excerpt_id": representatives[relation], "relation": relation}
                            for relation in _RELATIONS if relation in representatives]
                selected_count += len(evidence)
                reviews.append({"source_id": source["source_id"],
                                "assessment": "evidence" if evidence else "insufficient", "evidence": evidence})
                reviewed_pairs += 1
            rows.append({"claim_id": item["claim_id"], "source_reviews": reviews})
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        # An invalid guard/provenance contract cannot become a partial review.
        return None
    if needs_fallback:
        return None
    coverage = {"comparison_method": COMPARISON_METHOD,
                "source_review_protocol": "claim_source_review_v2",
                "expected_source_pair_count": len(claims) * len(sources),
                "reviewed_source_pair_count": reviewed_pairs,
                "expected_passage_count": len(claims) * sum(len(source["passages"]) for source in sources),
                "reviewed_passage_count": reviewed_passages,
                "guard_rejected_passage_count": rejected_count,
                "selected_evidence_count": selected_count,
                "complete_source_review": True}
    return json.dumps({"claims": rows}, ensure_ascii=False), coverage
