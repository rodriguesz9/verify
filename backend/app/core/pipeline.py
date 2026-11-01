import asyncio
from app.core.gemini_client import gemini_timeout_seconds
from datetime import datetime, timezone
import re
import os
from app.core.gemini_analyzer import extract_claims_with_ai, generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text
from app.core.serper_client import search_news, search_web, NewsSearch, MAX_NEWS_QUERY_CHARS
from app.core.scam_detector import analyze_scam_indicators
from app.core.openrouter_service import analyze_with_openrouter, analyze_retrieved_evidence_with_openrouter
from app.services.claim_policy import text_report, input_claims
from app.services.factual_queries import build_fact_check_queries
from app.services.source_attribution import collect_source_attribution
from app.services.source_registry import source_identity
from app.services.report_explanation import enrich_grounded_report
from app.services.content_risk import classify_unsubstantiated_content


def _verdicts_agree(v1: str, v2: str) -> bool:
    """Check if two verdicts point to the same direction."""
    a = v1.lower().strip() if v1 else ""
    b = v2.lower().strip() if v2 else ""
    positive = {"authentic", "true", "verdadeiro"}
    negative = {"ai_generated", "manipulated", "suspicious", "scam", "fake", "falso", "enganoso"}
    a_pos = a in positive
    a_neg = a in negative
    b_pos = b in positive
    b_neg = b in negative
    if a_pos and b_pos:
        return True
    if a_neg and b_neg:
        return True
    return False


def _merge_verdicts(gemini_result: dict, openrouter_result: dict) -> dict:
    """Merge Gemini and OpenRouter results using consensus."""
    if not openrouter_result or openrouter_result.get("error") or gemini_result.get("analysis_status") == "inconclusive":
        return gemini_result

    g_verdict = gemini_result.get("verdict", "Suspicious").lower()
    o_verdict = openrouter_result.get("verdict", "Suspicious").lower()
    g_score = float(gemini_result.get("score", 50))
    o_score = float(openrouter_result.get("score", 50))
    agree = _verdicts_agree(g_verdict, o_verdict)

    if agree:
        final_score = int(g_score)
        note = "Modelos concordam; concordância não comprova a alegação nem aumenta a precisão medida."
    else:
        final_score = int(g_score)
        note = "Modelos divergentes. Aplicação com Gemini (primário). Revise manualmente."

    merged = dict(gemini_result)
    merged["score"] = final_score
    merged["divergent"] = not agree
    merged["agreement_note"] = note
    merged["model_used"] = f"gemini+openrouter ({gemini_result.get('model_used', 'gemini')}/{openrouter_result.get('model_used', 'openrouter')})" if agree else f"gemini (openrouter divergente)"
    merged["openrouter_summary"] = openrouter_result.get("summary", "")
    merged["openrouter_explanation"] = openrouter_result.get("plain_explanation", "")

    return merged


async def _run_openrouter_check(text: str) -> dict | None:
    """Free auxiliary extraction, not a second opinion on truth."""
    try:
        return await asyncio.wait_for(analyze_with_openrouter(text), timeout=27.0)
    except Exception:
        return {"available": False, "status": "timeout", "claims": [],
                "reason": "Extração auxiliar OpenRouter indisponível.", "decision_role": "search_hints_only", "free_only": True}


async def _run_gemini_check(text: str, context: dict) -> dict:
    """Run Gemini final report."""
    return await generate_final_report(text, context)


def _claim_key(value: str) -> str:
    """Normalize claim identity without trying to infer its meaning."""
    return re.sub(r"\W+", " ", value.casefold(), flags=re.UNICODE).strip()


def _promote_semantic_evidence(ai: dict, generated: dict, assessments: list[dict], text: str) -> None:
    """Turn grounded semantic relations into the canonical textual decision.

    Gemini may interpret a negation or paraphrase, but only an assessment whose
    quoted text was validated against a retrieved source can vote. Snippets are
    context, not proof. Claim identity stays conservative: the model cannot
    introduce a new claim that was not in the submitted text.
    """
    submitted_claims = {_claim_key(text)}
    submitted_claims.update(_claim_key(item) for item in input_claims(text))
    eligible = []
    for assessment in assessments:
        if not isinstance(assessment, dict) or not assessment.get("evidence_validated"):
            continue
        relation = assessment.get("assessment")
        if relation not in {"supports", "contradicts"}:
            continue
        claim = assessment.get("claim")
        if not isinstance(claim, str) or _claim_key(claim) not in submitted_claims:
            continue
        sources = [source for source in assessment.get("sources", [])
                   if isinstance(source, dict)
                   and source.get("source_scope") in {"full_article", "fact_check"}
                   and isinstance(source.get("url"), str)
                   and isinstance(source.get("quote"), str)
                   and source["quote"].strip()]
        if not sources:
            continue
        eligible.append((assessment, sources))

    if not eligible:
        return

    relations = {assessment["assessment"] for assessment, _ in eligible}
    status = ("conflicting" if relations == {"supports", "contradicts"}
              else "supported" if relations == {"supports"} else "refuted")
    evidence_by_claim = {}
    for assessment, sources in eligible:
        evidence_by_claim[_claim_key(assessment["claim"])] = [
            {"url": source["url"], "excerpt": source["quote"],
             "relation": "supports" if assessment["assessment"] == "supports" else "refutes",
             "source_role": "retrieved_source"}
            for source in sources
        ]

    canonical = []
    for assessment in ai.get("claim_assessments", []):
        if not isinstance(assessment, dict):
            continue
        key = _claim_key(assessment.get("claim", ""))
        matched = next((item for item, _ in eligible if _claim_key(item["claim"]) == key), None)
        if matched:
            relation = matched["assessment"]
            canonical.append({**assessment,
                              "status": "supported" if relation == "supports" else "refuted",
                              "explanation": matched.get("explanation", ""),
                              "evidence": evidence_by_claim[key],
                              "evidence_mode": "retrieved_sources",
                              "decision_role": "grounded_semantic_evidence"})
        else:
            canonical.append(assessment)

    ai["claim_assessments"] = canonical
    ai["veracity_status"] = status
    ai["analysis_status"] = "partial"
    ai["verdict"] = "Authentic" if status == "supported" else "False" if status == "refuted" else "Suspicious"
    ai["score"] = 90 if status == "supported" else 10 if status == "refuted" else 50
    ai["semantic_decision"] = {
        "status": status,
        "decision_role": "validated_semantic_evidence",
        "evidence_count": sum(len(sources) for _, sources in eligible),
    }


async def _retrieve_source_attribution(text: str, queries: list[str], source_url: str | None) -> dict:
    """One literal search and bounded retrieval of public pages.

    Source attribution cannot vote on the factual decision. Search snippets
    remain leads; only a complete sentence in a retrieved document can match.
    """
    deadline = 20
    plan = []
    try:
        async with asyncio.timeout(deadline):
            query = next((query for query in queries if 1 <= len(query.strip()) <= 500), None)
            leads = (await search_web(query) if query else NewsSearch(
                status="no_results", reason="Nenhuma frase completa cabe no limite da busca; nenhum texto foi cortado."))
            plan = [{"method": "whole_literal_claim",
                     "status": getattr(leads, "status", "success" if leads else "no_results")}] if query else []
            attribution = await collect_source_attribution(text, queries, source_url, search_results=leads)
            attribution.setdefault("coverage", {})["search_queries"] = plan
            attribution["coverage"]["max_search_queries"] = 1
            attribution["coverage"]["retrieval_deadline_seconds"] = deadline
            return attribution
    except Exception:
        return {"status": "error", "decision_role": "source_attribution_only", "matches": [],
                "reason": "A leitura das referências não foi concluída no prazo ou com segurança.",
                "limitations": ["Referências não confirmam automaticamente verdade, falsidade ou a página inteira."],
                "coverage": {"status": "error", "decision_role": "source_attribution_only",
                             "search_queries": plan, "max_search_queries": 1,
                             "retrieval_deadline_seconds": deadline}}


def extract_dates_from_text(text: str) -> list[str]:
    patterns = [
        r"\b(\d{2}[/\-.]\d{2}[/\-.]\d{2,4})\b",
        r"\b(\d{4}[/\-.]\d{2}[/\-.]\d{2})\b",
        r"\b(\d{1,2}\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro))\b",
        r"\b(hoje|ontem|há\s+\d+\s*[d-hm]|na\s+semana)\b",
        r"\b(\d{2}\s+(?:de\s+)?(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro))\b",
    ]
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend(matches)
    return found


def extract_source_from_url(url: str) -> dict:
    if not url:
        return {"source_name": "Nenhuma", "is_trusted": False, "score": 50}
    from urllib.parse import urlparse
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        hostname = url.lower()

    trusted_domains = [
        "globo.com", "bbc.com", "bbc.co.uk", "cnn.com", "cnnbrasil.com.br", "uol.com.br",
        "reuters.com", "ebc.com.br", "estadao.com.br", "correiobraziliense.com.br", "exame.com",
        "gov.br", "wikipedia.org",
    ]
    hostname = hostname.lower().rstrip(".")
    is_trusted = any(hostname == t or hostname.endswith("." + t) for t in trusted_domains)
    
    if is_trusted:
        return {"source_name": hostname, "is_trusted": True, "score": 88}
    
    return {"source_name": hostname, "is_trusted": False, "score": 50}


def _annotate_search_source(item: dict) -> dict:
    """Add a curated publisher-class label; reputation is not truth evidence."""
    link = item.get("link") if isinstance(item, dict) else None
    reputation_url = f"https://{link[7:]}" if isinstance(link, str) and link.startswith("http://") else link
    identity = source_identity(reputation_url) if isinstance(reputation_url, str) else None
    if identity and identity.get("source_type") == "primary":
        assessment = {"level": "primary", "label": "Fonte primária reconhecida",
                      "basis": "Domínio incluído na lista curada de fontes primárias."}
    elif identity and identity.get("source_type") == "editorial":
        assessment = {"level": "editorial", "label": "Veículo editorial reconhecido",
                      "basis": "Domínio incluído na lista curada de veículos editoriais."}
    else:
        assessment = {"level": "unclassified", "label": "Reputação não classificada",
                      "basis": "Não há classificação curada para este domínio; isso não significa que seja ruim."}
    return {**item, "publisher_assessment": assessment}


def analyze_temporal_context(serper_news: list, scrape_date: str = None) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    dates_found = []
    
    for item in serper_news:
        date_str = item.get("date", "")
        if date_str:
            dates_found.append(date_str)
    
    if not dates_found and scrape_date:
        dates_found.append(scrape_date)
    
    is_recent = False
    max_age_hours = 24
    
    if dates_found:
        try:
            first_date_str = dates_found[0]
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%Y %H:%M", "%B %d, %Y"]:
                try:
                    parsed = datetime.strptime(first_date_str[:len("2024-12-31T23:59:59")], fmt)
                    age = now - parsed
                    max_age_hours = min(max_age_hours, abs(age.total_seconds()) / 3600)
                    is_recent = age.total_seconds() < 7 * 24 * 3600
                    break
                except (ValueError, TypeError):
                    continue
        except Exception:
            pass
    
    return {
        "is_recent": is_recent,
        "max_age_hours": round(max_age_hours, 1),
        "dates_found": dates_found[:3],
        "news_count": len(serper_news),
    }


async def run_pipeline(text: str, url: str | None = None, *, use_ai_extraction: bool = True,
                       use_detailed_report: bool = False,
                       use_gemini_report: bool = False, allow_content_classification: bool = True) -> dict:
    source_url = url
    analysis_text = text

    scam_info = analyze_scam_indicators(analysis_text, source_url)

    openrouter_result = {"available": False, "status": "not_configured", "claims": [],
                         "decision_role": "search_hints_only", "free_only": True}
    gemini_coverage = None
    if use_ai_extraction and os.getenv("OPENROUTER_API_KEY", "").strip() and os.getenv("OPENROUTER_ENABLED", "true").lower() == "true":
        openrouter_result = await _run_openrouter_check(analysis_text)
    if openrouter_result.get("available"):
        claims = openrouter_result["claims"]
    elif use_ai_extraction:
        try:
            claims = await asyncio.wait_for(extract_claims_with_ai(analysis_text), gemini_timeout_seconds() + 2)
            gemini_coverage = getattr(claims, "coverage", {"status": "success", "decision_role": "search_hints_only"})
            claims = list(claims)
        except asyncio.TimeoutError:
            claims = []
            gemini_coverage = {"available": False, "status": "timeout", "decision_role": "search_hints_only",
                               "reason": "Extração Gemini não concluída no prazo; a consulta literal foi preservada."}
        except Exception:
            claims = []
            gemini_coverage = {"available": False, "status": "error", "decision_role": "search_hints_only",
                               "reason": "Extração Gemini indisponível; a consulta literal foi preservada."}
    else:
        # OCR/transcription is already extraction. Do not spend another LLM
        # request or let a slow helper cancel literal evidence retrieval.
        claims = []
    # Retrieve literal input as well as extraction. Model paraphrases are search
    # hints only: they cannot change the statement that receives the verdict.
    fact_check_queries, query_plan = build_fact_check_queries(analysis_text, claims, limit=5)
    ai_task = asyncio.create_task(detect_ai_text(analysis_text))
    domain_task = (asyncio.create_task(asyncio.to_thread(check_domain_reputation, source_url)) if source_url else None)
    fact_tasks = [
        asyncio.create_task(query_fact_check_api(query))
        for query in fact_check_queries
    ]

    serper_news_queries, news_query_plan = build_fact_check_queries(
        analysis_text, claims, limit=3, max_query_chars=MAX_NEWS_QUERY_CHARS)
    serper_news_tasks = [
        asyncio.create_task(search_news(query))
        for query in serper_news_queries
    ]
    serper_web_queries, web_query_plan = build_fact_check_queries(
        analysis_text, claims, limit=3, max_query_chars=MAX_NEWS_QUERY_CHARS)
    serper_web_queries = [query for query in serper_web_queries if query.strip()]
    serper_web_tasks = [asyncio.create_task(search_web(query)) for query in serper_web_queries]
    attribution_task = asyncio.create_task(_retrieve_source_attribution(
        analysis_text, fact_check_queries, source_url))
    tasks = [*fact_tasks, *serper_news_tasks, *serper_web_tasks, ai_task, attribution_task]
    if domain_task:
        tasks.append(domain_task)
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    fact_checks = []
    seen_fact_checks: set[tuple[str, str | None]] = set()
    for task in fact_tasks:
        if task.exception():
            continue
        for fact_check in task.result():
            key = (fact_check.claim_text.casefold(), fact_check.url)
            if key in seen_fact_checks:
                continue
            seen_fact_checks.add(key)
            fact_checks.append(fact_check)
    fact_checks = fact_checks[:30]

    ai_forensics = ai_task.result() if not ai_task.exception() else {"ai_probability": None}
    domain_info = domain_task.result() if domain_task and not domain_task.exception() else { "score": None, "note": "Domínio não analisado" }

    serper_news_results = []
    raw_news_count = 0
    seen_links: set[str] = set()
    for task in serper_news_tasks:
        if task.exception():
            continue
        for item in task.result():
            raw_news_count += 1
            link = item.get("link")
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            serper_news_results.append(item)

    unique_news_count = len(serper_news_results)
    serper_web_results = []
    raw_web_count = 0
    for task in serper_web_tasks:
        if task.exception():
            continue
        for item in task.result():
            raw_web_count += 1
            link = item.get("link")
            if link and link not in seen_links:
                seen_links.add(link)
                serper_web_results.append(item)
    unique_web_count = len(serper_web_results)
    # Search results remain context only; do not discard them via lexical anchor matching.
    serper_news_results = [_annotate_search_source(item) for item in serper_news_results]
    serper_web_results = [_annotate_search_source(item) for item in serper_web_results]

    dates_in_text = extract_dates_from_text(analysis_text)
    source_info = extract_source_from_url(source_url) if source_url else {"source_name": "Nenhuma", "is_trusted": False, "score": 50}
    temporal_info = analyze_temporal_context(serper_news_results)

    context = {
        "scam_analysis": scam_info,
        "gptzero": ai_forensics,
        "domain": domain_info,
        "claims": claims,
        "fact_checks": [fc.model_dump() for fc in fact_checks],
        "serper_news": serper_news_results,
        "serper_web": serper_web_results,
        "source_url": source_url,
        "temporal_context": temporal_info,
        "dates_in_content": dates_in_text,
        "source_info": source_info,
    }

    # Google Fact Check is supplementary context. It must never be the final
    # decision: its coverage is sparse and its editorial ratings are not a
    # substitute for semantic analysis of the retrieved material.
    ai = text_report(analysis_text, context["fact_checks"], scam_info)
    editorial_assessments = ai.get("claim_assessments", [])
    ai["editorial_complement"] = {
        "fact_checks": context["fact_checks"],
        "claim_assessments": editorial_assessments,
        "decision_role": "supplementary_context_only",
        "used_for_final_verdict": False,
    }
    # Keep the old assessment shape for clients, but prevent the legacy
    # literal rating from being rendered as the current decision.
    ai["claim_assessments"] = [
        {**item, "status": "unverified",
         "explanation": "Checagem editorial complementar; não usada sozinha para o resultado final.",
         "decision_role": "supplementary_context_only"}
        for item in editorial_assessments if isinstance(item, dict)
    ]
    ai["verdict"] = "Scam" if scam_info.get("is_scam") else "Suspicious"
    ai["score"] = 15 if scam_info.get("is_scam") else 50
    ai["veracity_status"] = "unverified"
    ai["analysis_status"] = "partial" if scam_info.get("is_scam") else "inconclusive"
    if not scam_info.get("is_scam"):
        ai["summary"] = "A análise semântica das fontes ainda não foi concluída; as checagens editoriais encontradas são apenas complemento."
        ai["plain_explanation"] = ai["summary"]
    ai["search_claims"] = claims
    ai["search_claims_decision_role"] = "search_hints_only"
    ai["scam_analysis"] = scam_info
    ai["serper_news"] = serper_news_results
    ai["serper_web"] = serper_web_results
    source_attribution = dict(attribution_task.result())
    ai["source_attribution"] = source_attribution
    queries = [{"status": "error" if task.exception() else getattr(task.result(), "status", "success" if task.result() else "no_results"),
                "reason": "Falha na consulta." if task.exception() else getattr(task.result(), "reason", None)} for task in fact_tasks]
    status = ("success" if fact_checks else "no_results" if any(q["status"] in {"success", "no_results"} for q in queries)
              else "not_configured" if all(q["status"] == "not_configured" for q in queries) else "error")
    ai["provider_coverage"] = {"google_fact_check": {
        "status": status, "queries": queries, "query_plan": query_plan, "matches_returned": len(fact_checks),
        "reason": "Consulta concluída sem checagens correspondentes." if status == "no_results" else
                  next((q["reason"] for q in queries if q["reason"]), None)}}
    ai["provider_coverage"]["web_references"] = {
        **source_attribution.get("coverage", {}),
        "status": "success" if source_attribution["status"] == "found" else source_attribution["status"],
        "decision_role": "source_attribution_only", "matches_returned": len(source_attribution.get("matches", [])),
        "reason": source_attribution.get("reason"),
    }
    if use_ai_extraction:
        ai["provider_coverage"]["openrouter"] = {key: value for key, value in openrouter_result.items()
            if key in {"available", "status", "reason", "model_used", "decision_role", "free_only", "response_issue"}}
        if gemini_coverage is not None:
            ai["provider_coverage"]["gemini"] = gemini_coverage
    news_queries = [{"status": "error" if task.exception() else getattr(task.result(), "status", "success" if task.result() else "no_results"),
                     "reason": "Falha na busca de contexto." if task.exception() else getattr(task.result(), "reason", None)}
                    for task in serper_news_tasks]
    news_status = ("not_requested" if not news_queries else "success" if serper_news_results else "no_results" if any(q["status"] in {"success", "no_results"} for q in news_queries)
                   else "not_configured" if all(q["status"] == "not_configured" for q in news_queries) else "error")
    ai["provider_coverage"]["serper"] = {"status": news_status, "queries": news_queries, "decision_role": "context_only",
                                          "query_plan": news_query_plan,
                                          "matches_returned": len(serper_news_results),
                                          "raw_matches_returned": raw_news_count, "unique_matches_returned": unique_news_count,
                                          "reason": "Busca omitida: nenhuma consulta cabe no limite de 500 caracteres; nenhum texto foi cortado." if news_status == "not_requested" else
                                                    "Busca concluída sem notícias; isso não prova falsidade." if news_status == "no_results" else next((q["reason"] for q in news_queries if q["reason"]), None)}
    web_queries = [{"status": "error" if task.exception() else getattr(task.result(), "status", "success" if task.result() else "no_results"),
                    "reason": "Falha na busca web." if task.exception() else getattr(task.result(), "reason", None)}
                   for task in serper_web_tasks]
    web_status = ("not_requested" if not web_queries else "success" if raw_web_count else
                  "no_results" if any(q["status"] in {"success", "no_results"} for q in web_queries) else
                  "not_configured" if all(q["status"] == "not_configured" for q in web_queries) else "error")
    ai["provider_coverage"]["serper_web"] = {
        "status": web_status, "queries": web_queries, "query_plan": web_query_plan,
        "decision_role": "context_only", "matches_returned": len(serper_web_results),
        "raw_matches_returned": raw_web_count, "unique_matches_returned": unique_web_count,
        "reason": "Nenhuma consulta de 1 a 500 caracteres disponível; nenhum texto foi cortado." if web_status == "not_requested" else
                  "Busca web concluída sem resultados." if web_status == "no_results" else
                  next((q["reason"] for q in web_queries if q["reason"]), None)}

    content_classification = (classify_unsubstantiated_content(
        analysis_text, ai, source_url, domain_info, source_attribution,
        [*serper_news_results, *serper_web_results])
        if allow_content_classification else None)
    if content_classification:
        for assessment in ai.get("claim_assessments", []):
            if isinstance(assessment, dict) and assessment.get("status") == "unverified":
                assessment.update(status="probably_false",
                    explanation=content_classification["explanation"],
                    classification_category=content_classification["category"])
        ai.update(
            veracity_status="probably_false",
            verdict="Suspicious",
            analysis_status="inconclusive",
            content_classification=content_classification,
            summary=content_classification["explanation"],
            plain_explanation=content_classification["explanation"],
            whatsapp_share_text="⚠️ Verify: " + content_classification["explanation"],
        )
        ai.setdefault("red_flags", []).append(
            content_classification["category"] + ": " + content_classification["category_description"])

    if scam_info["is_scam"]:
        ai["verdict"] = "Scam"
        ai["analysis_status"] = "partial"
        ai["summary"] = "Há padrões conhecidos de possível golpe nesta mensagem. Não pague taxas nem envie dados sem confirmar pelo canal oficial."
        ai["plain_explanation"] = "Foram encontrados sinais no conteúdo da mensagem, não uma comprovação da identidade do remetente ou uma investigação concluída."
        ai["whatsapp_share_text"] = "⚠️ O Verify identificou sinais de possível golpe. Não envie dinheiro nem dados antes de confirmar por um canal oficial."
        ai["score"] = min(ai.get("score", 10), 15)
        for pattern in scam_info["detected_patterns"]:
            red_flag = f"Alerta de Golpe: {pattern['category']} - {pattern['description']}"
            if "red_flags" in ai and red_flag not in ai["red_flags"]:
                ai["red_flags"].append(red_flag)
        if scam_info.get("suspicious_url") and scam_info.get("suspicious_url_reason"):
            ai.setdefault("red_flags", []).append(f"Link Suspeito: {scam_info['suspicious_url_reason']}")

    if use_gemini_report:
        report_context = {**context,
            "source_attribution": source_attribution,
            "provider_coverage": ai.get("provider_coverage", {}),
            "policy_assessment": {key: ai.get(key) for key in (
                "verdict", "veracity_status", "analysis_status", "claim_assessments", "summary")}}
        generated = await _run_gemini_check(analysis_text, report_context)
        generated_status = ("error" if not isinstance(generated, dict) or generated.get("model_used") == "fallback"
                            else "success")
        gemini_status = generated_status
        fallback_used = False
        if generated_status == "error":
            fallback = await analyze_retrieved_evidence_with_openrouter(analysis_text, report_context)
            if isinstance(fallback, dict) and fallback.get("model_used") != "fallback":
                generated = fallback
                generated_status = "success"
                fallback_used = True
                ai.setdefault("provider_coverage", {})["openrouter_semantic_fallback"] = {
                    "status": "success", "decision_role": "evidence_based_report",
                    "model_used": fallback.get("model_used"), "free_only": True,
                }
            else:
                ai.setdefault("provider_coverage", {})["openrouter_semantic_fallback"] = {
                    "status": fallback.get("status", "error") if isinstance(fallback, dict) else "error",
                    "decision_role": "evidence_based_report", "free_only": True,
                    "reason": fallback.get("reason") if isinstance(fallback, dict) else "Fallback indisponível.",
                }
        ai.setdefault("provider_coverage", {})["gemini_report"] = {
            "status": gemini_status, "decision_role": "evidence_based_report",
            "model_used": None if fallback_used else (generated.get("model_used") if isinstance(generated, dict) else None),
            "reason": "Gemini não gerou o relatório; explicação baseada na política de evidências foi mantida."
                      if gemini_status == "error" else None}
    if use_gemini_report and generated_status == "success":
            # Model interpretation is exposed as an evidence report. It does
            # not silently replace the policy verdict: callers can distinguish
            # semantic assessment from a confirmed fact.
            allowed_urls = {
                item.get("link") for item in [*serper_news_results, *serper_web_results]
                if isinstance(item, dict) and isinstance(item.get("link"), str)
            }
            source_text_by_url = {}
            source_scope_by_url = {}
            for item in [*serper_news_results, *serper_web_results]:
                if isinstance(item, dict) and isinstance(item.get("link"), str):
                    source_text_by_url[item["link"]] = " ".join(
                        str(item.get(field, "")) for field in ("title", "snippet", "source")
                    )
                    source_scope_by_url[item["link"]] = "snippet"
            for item in context.get("fact_checks", []):
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    allowed_urls.add(item["url"])
                    source_text_by_url[item["url"]] = " ".join(
                        str(item.get(field, "")) for field in ("claim_text", "rating", "publisher")
                    )
                    source_scope_by_url[item["url"]] = "fact_check"
            allowed_urls.update(
                item.get("url") for item in source_attribution.get("matches", [])
                if isinstance(item, dict) and isinstance(item.get("url"), str)
            )
            for item in source_attribution.get("matches", []):
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    source_text_by_url[item["url"]] = item.get("excerpt", "")
                    source_scope_by_url[item["url"]] = (
                        "submitted_source" if item.get("source_role") == "submitted_source" else "full_article")
            for item in source_attribution.get("semantic_documents", []):
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    allowed_urls.add(item["url"])
                    source_text_by_url[item["url"]] = item.get("text", "")
                    source_scope_by_url[item["url"]] = (
                        "submitted_source" if item.get("source_role") == "submitted_source" else "full_article")
            evidence_assessments = []
            for assessment in generated.get("claim_assessments", []):
                if not isinstance(assessment, dict):
                    continue
                sources = []
                for source in assessment.get("sources", []):
                    if not isinstance(source, dict) or source.get("url") not in allowed_urls:
                        continue
                    quote = source.get("quote", "")
                    if not isinstance(quote, str) or not quote.strip():
                        continue
                    source_text = source_text_by_url.get(source.get("url"), "")
                    if quote.strip() not in source_text:
                        continue
                    sources.append({key: source[key] for key in ("url", "title", "quote")
                                    if key in source and isinstance(source[key], str)}
                                   | {"source_scope": source_scope_by_url[source["url"]]})
                evidence_assessments.append({
                    "claim": assessment.get("claim", "")[:5000],
                    "assessment": assessment.get("assessment"),
                    "explanation": assessment.get("explanation", "")[:3000],
                    "sources": sources,
                    "evidence_validated": bool(sources),
                })
            ai["semantic_evidence_report"] = {
                "certainty": generated.get("certainty"),
                "claim_assessments": evidence_assessments,
                "decision_role": "evidence_interpretation_not_certainty",
                "source_validation": "url_must_be_retrieved_and_quote_required",
            }
            # Gemini interpretation supplies a candidate relation. The
            # validated relation below, not the model's free-form verdict,
            # controls the canonical textual result.
            if not scam_info.get("is_scam"):
                ai["verdict"] = generated.get("verdict", "Suspicious")
                ai["score"] = int(generated.get("score", 50))
                ai["analysis_status"] = "partial"
                ai["semantic_verdict"] = generated.get("verdict", "Suspicious")
                ai["semantic_score"] = generated.get("semantic_score")
                if generated.get("verdict") == "Authentic":
                    ai["veracity_status"] = "supported"
                elif generated.get("verdict") == "Suspicious":
                    ai["veracity_status"] = "unverified"
                else:
                    ai["veracity_status"] = "unverified"
            for field in ("summary", "plain_explanation", "elderly_tip", "whatsapp_share_text"):
                value = generated.get(field)
                if isinstance(value, str) and value.strip():
                    ai[field] = value.strip()[:5000]
            search_summary = generated.get("search_summary")
            if isinstance(search_summary, str) and search_summary.strip():
                ai["search_summary"] = search_summary.strip()[:5000]
            for field in ("red_flags", "positives"):
                values = generated.get(field)
                if isinstance(values, list):
                    valid = [item.strip()[:500] for item in values if isinstance(item, str) and item.strip()]
                    if field == "red_flags":
                        ai[field] = list(dict.fromkeys([*ai.get(field, []), *valid]))[:20]
                    else:
                        ai[field] = valid[:20]
            _promote_semantic_evidence(ai, generated, evidence_assessments, analysis_text)
            ai["report_model_used"] = generated.get("model_used")

    # Explanations are rendered after every decision/coverage layer. No extra
    # model call, new evidence, classification, probability or quota is added.
    if use_detailed_report:
        ai = enrich_grounded_report(ai)

    return {
        "report": ai,
        "claims": claims,
        "metrics": {
            "text_ai_probability": ai_forensics.get("ai_probability"),
            "fact_checks_count": len(fact_checks),
            "serper_news_count": len(serper_news_results),
            "serper_web_count": len(serper_web_results),
            "domain_score": domain_info.get("score"),
            "earliest_known_date": (temporal_info.get("dates_found") or [None])[0],
            "temporal_info": temporal_info,
            "source_info": source_info,
            "openrouter_available": bool(openrouter_result.get("available")),
            "divergent": ai.get("divergent", False),
            "agreement_note": ai.get("agreement_note", ""),
            "model_used": ai.get("model_used", "gemini"),
        },
        "fact_checks": fact_checks,
        "serper_news": serper_news_results,
        "serper_web": serper_web_results,
        "domain_info": domain_info,
        "scam_analysis": scam_info,
        "temporal_context": temporal_info,
        "source_info": source_info,
    }
