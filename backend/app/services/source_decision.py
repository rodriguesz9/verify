"""Combine server-validated source comparisons with published claim reviews.

No model, search, network or score averaging lives here. A partial/unsupported
source comparison cannot replace a decisive published review or approve an
uncovered part of a submitted text.
"""
from copy import deepcopy

from app.services.claim_policy import input_claims, normalize_claim
from app.services.source_corroboration import is_original_record_claim

POLICY_VERSION = "2026-10-23.1"
SOURCE_SCORE_SEMANTICS = "not_calibrated_source_corroboration"
_STATES = {"corroborated": "supported", "refuted": "refuted", "conflicting": "conflicting"}


def apply_source_decision(text, report, comparison):
    result = deepcopy(report)
    # Scam triage, mixed or conflicting published reviews have their own scope;
    # source comparison never silently cancels these existing warnings.
    if (report.get("verdict") == "Scam" or report.get("veracity_status") != "unverified"
            or not isinstance(comparison, dict)
            or comparison.get("version") != "source_corroboration_v1"
            or comparison.get("decision_role") != "grounded_source_comparison"
            or comparison.get("status") not in {"success", "partial"}):
        return result
    parts = input_claims(text)
    originals = report.get("claim_assessments")
    comparisons = comparison.get("claims")
    if (not parts or not isinstance(originals, list)
            or len(originals) != min(len(parts), 5) or not isinstance(comparisons, list)
            or len({normalize_claim(part) for part in parts}) != len(parts)):
        return result
    complete_input = len(parts) <= len(originals)
    by_claim = {}
    for item in comparisons:
        if isinstance(item, dict) and isinstance(item.get("claim"), str):
            key = normalize_claim(item["claim"])
            if key in by_claim:
                return result  # Ambiguous repeated identity is not coverage.
            by_claim[key] = item
    merged, used_sources, used_reviews = [], False, False
    for part, original in zip(parts, originals):
        if not isinstance(original, dict) or normalize_claim(original.get("claim", "")) != normalize_claim(part):
            return result
        decision = deepcopy(original)
        if original.get("status") in {"supported", "refuted", "conflicting"}:
            used_reviews = True
        else:
            source = by_claim.get(normalize_claim(part), {})
            state = _STATES.get(source.get("status"))
            evidence = source.get("evidence")
            if state and isinstance(evidence, list):
                expected = {"supports"} if state == "supported" else {"refutes"} if state == "refuted" else {"supports", "refutes"}
                usable = [e for e in evidence if isinstance(e, dict)
                    and e.get("relation") in expected and isinstance(e.get("publisher_family"), str)
                    and e.get("publisher_family") and isinstance(e.get("excerpt"), str)
                    and e.get("excerpt") and e.get("source_role") != "submitted_source"]
                families = {e["publisher_family"] for e in usable}
                relations = {e["relation"] for e in usable}
                original_record = any(is_original_record_claim(part, item) for item in usable)
                required = (len(families) >= 2 or original_record) and (state != "conflicting" or relations == expected)
                if required:
                    decision.update(status=state, evidence=deepcopy(usable), evidence_mode="retrieved_sources",
                        explanation=source.get("explanation") or "Comparação fundamentada nos trechos das fontes consultadas.",
                        excluded_evidence=deepcopy(source.get("excluded_evidence", [])))
                    used_sources = True
        merged.append(decision)
    if not used_sources:
        return result
    states = {d["status"] for d in merged}
    truth = ("supported" if complete_input and states == {"supported"} else "refuted" if complete_input and states == {"refuted"}
             else "conflicting" if "conflicting" in states else "mixed" if {"supported", "refuted"} <= states else "unverified")
    descriptions = {
        "supported": "A informação foi verificada como verdadeira nos trechos de fontes independentes consultadas. Confira as fontes, datas e contexto: a análise pode errar e não comprova a origem de uma imagem, áudio ou vídeo.",
        "refuted": "A informação foi verificada como falsa nos trechos de fontes independentes consultadas. Confira a explicação, as datas e o contexto: a análise pode errar e vale somente para as afirmações analisadas.",
        "conflicting": "As fontes consultadas apresentam informações em desacordo. É necessária conferência humana antes de concluir.",
        "mixed": "A mensagem contém afirmações verificadas como verdadeiras e outras como falsas nas fontes consultadas. Não cabe um único resultado para todo o conteúdo.",
        "unverified": "Foi possível verificar partes da mensagem nas fontes consultadas, mas outras partes ficaram sem confirmação. Não foi possível dizer se a mensagem inteira é verdadeira ou falsa.",
    }
    single_record = any(decision.get("evidence_mode") == "retrieved_sources"
        and len({item.get("publisher_family") for item in decision.get("evidence", [])}) < 2
        and any(is_original_record_claim(decision["claim"], item) for item in decision.get("evidence", [])) for decision in merged)
    if single_record and truth in {"supported", "refuted"}:
        descriptions[truth] = ("A afirmação sobre o que a instituição publicou foi verificada como " + ("verdadeira" if truth == "supported" else "falsa")
            + " no registro original consultado. Foi consultada a publicação da própria instituição, não duas fontes independentes; confira o trecho e a data. Isso não comprova que o fenômeno descrito realmente ocorreu.")
    result.update(claim_assessments=merged, veracity_status=truth,
        verdict="Authentic" if truth == "supported" else "False" if truth == "refuted" else "Suspicious",
        analysis_status="partial" if truth in {"supported", "refuted"} else "inconclusive",
        summary=descriptions[truth], plain_explanation=descriptions[truth],
        whatsapp_share_text="🔎 Verify: " + descriptions[truth], confidence=None, authenticity_percentage=None,
        veracity_decision_basis="mixed_evidence" if used_reviews else "retrieved_sources",
        original_record_only=single_record,
        veracity_decision_coverage_complete=complete_input and all(d["status"] in {"supported", "refuted", "conflicting"} for d in merged),
        policy_version=POLICY_VERSION, score=0, score_semantics=SOURCE_SCORE_SEMANTICS)
    # The non-null integer is retained only for the legacy DB column. All
    # presenters/history/stats must omit it under this explicit semantics.
    result["limitations"] = [*result.get("limitations", []),
        "Cruzamento de documentos recuperados com comparação assistida por IA; fontes e comparação podem errar. Não é uma certificação factual.",
        "O resultado vale para as afirmações e trechos lidos, não para todas as fontes existentes ou um artigo inteiro. Não há porcentagem de precisão calibrada."]
    return result
