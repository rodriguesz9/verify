import asyncio
from app.core.gemini_client import gemini_timeout_seconds
from datetime import datetime, timezone
import re
import os
from app.core.gemini_analyzer import extract_claims_with_ai, generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text
from app.core.serper_client import search_news
from app.core.scam_detector import analyze_scam_indicators
from app.core.openrouter_service import analyze_with_openrouter
from app.services.claim_policy import text_report, input_claims


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


async def run_pipeline(text: str, url: str | None = None, *, use_ai_extraction: bool = True) -> dict:
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
    fact_check_queries = list(dict.fromkeys([analysis_text, *input_claims(analysis_text), *claims]))[:5]
    ai_task = asyncio.create_task(detect_ai_text(analysis_text))
    domain_task = (asyncio.create_task(asyncio.to_thread(check_domain_reputation, source_url)) if source_url else None)
    fact_tasks = [
        asyncio.create_task(query_fact_check_api(query))
        for query in fact_check_queries
    ]

    serper_news_queries = claims[:3] or [analysis_text[:200]]
    serper_news_tasks = [
        asyncio.create_task(search_news(query[:200]))
        for query in serper_news_queries
    ]
    tasks = [*fact_tasks, *serper_news_tasks, ai_task]
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
    seen_links: set[str] = set()
    for task in serper_news_tasks:
        if task.exception():
            continue
        for item in task.result():
            link = item.get("link")
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            serper_news_results.append(item)

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
        "source_url": source_url,
        "temporal_context": temporal_info,
        "dates_in_content": dates_in_text,
        "source_info": source_info,
    }

    # Model extraction assists search, but NEVER votes on the final verdict.
    ai = text_report(analysis_text, context["fact_checks"], scam_info)
    ai["search_claims"] = claims
    ai["scam_analysis"] = scam_info
    ai["serper_news"] = serper_news_results
    queries = [{"status": "error" if task.exception() else getattr(task.result(), "status", "success" if task.result() else "no_results"),
                "reason": "Falha na consulta." if task.exception() else getattr(task.result(), "reason", None)} for task in fact_tasks]
    status = ("success" if fact_checks else "no_results" if any(q["status"] in {"success", "no_results"} for q in queries)
              else "not_configured" if all(q["status"] == "not_configured" for q in queries) else "error")
    ai["provider_coverage"] = {"google_fact_check": {
        "status": status, "queries": queries, "matches_returned": len(fact_checks),
        "reason": "Consulta concluída sem checagens correspondentes." if status == "no_results" else
                  next((q["reason"] for q in queries if q["reason"]), None)}}
    if use_ai_extraction:
        ai["provider_coverage"]["openrouter"] = {key: value for key, value in openrouter_result.items()
            if key in {"available", "status", "reason", "model_used", "decision_role", "free_only", "response_issue"}}
        if gemini_coverage is not None:
            ai["provider_coverage"]["gemini"] = gemini_coverage
    news_queries = [{"status": "error" if task.exception() else getattr(task.result(), "status", "success" if task.result() else "no_results"),
                     "reason": "Falha na busca de contexto." if task.exception() else getattr(task.result(), "reason", None)}
                    for task in serper_news_tasks]
    news_status = ("success" if serper_news_results else "no_results" if any(q["status"] in {"success", "no_results"} for q in news_queries)
                   else "not_configured" if all(q["status"] == "not_configured" for q in news_queries) else "error")
    ai["provider_coverage"]["serper"] = {"status": news_status, "queries": news_queries, "decision_role": "context_only",
                                          "matches_returned": len(serper_news_results),
                                          "reason": next((q["reason"] for q in news_queries if q["reason"]), None)}

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

    return {
        "report": ai,
        "claims": claims,
        "metrics": {
            "text_ai_probability": ai_forensics.get("ai_probability"),
            "fact_checks_count": len(fact_checks),
            "serper_news_count": len(serper_news_results),
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
        "domain_info": domain_info,
        "scam_analysis": scam_info,
        "temporal_context": temporal_info,
        "source_info": source_info,
    }
