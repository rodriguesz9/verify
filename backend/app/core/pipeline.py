import asyncio
from datetime import datetime, timedelta
import re
from app.core.gemini_analyzer import extract_claims_with_ai, generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text
from app.core.serper_client import search_news
from app.core.scam_detector import analyze_scam_indicators
from app.core.openrouter_service import analyze_with_openrouter


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
    if not openrouter_result or openrouter_result.get("error"):
        return gemini_result

    g_verdict = gemini_result.get("verdict", "Suspicious").lower()
    o_verdict = openrouter_result.get("verdict", "Suspicious").lower()
    g_score = float(gemini_result.get("score", 50))
    o_score = float(openrouter_result.get("score", 50))
    agree = _verdicts_agree(g_verdict, o_verdict)

    if agree:
        final_score = min(100, max(0, int((g_score + o_score) / 2 * 1.1)))
        note = "Ambos os modelos concordam na análise."
    else:
        final_score = int(g_score * 0.85)
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
    """Run OpenRouter analysis as secondary check."""
    try:
        result = await asyncio.wait_for(analyze_with_openrouter(text), timeout=45.0)
        return result if result else None
    except Exception as e:
        print(f"OpenRouter cross-check failed: {e}")
        return None


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
        "g1.globo", "globo.com", "bbc", "cnn", "folha.uol",
        "reuters", "agenciabrasil", "estadao", "uol.com",
        "correiobraziliense", "valor.globo", "exame.com",
        "gov.br", "wikipedia",
    ]
    is_trusted = any(t in hostname.lower() for t in trusted_domains)
    
    if is_trusted:
        return {"source_name": hostname, "is_trusted": True, "score": 88}
    
    return {"source_name": hostname, "is_trusted": False, "score": 50}


def analyze_temporal_context(serper_news: list, scrape_date: str = None) -> dict:
    now = datetime.utcnow()
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


async def run_pipeline(text: str, url: str | None = None) -> dict:
    source_url = url
    analysis_text = text

    scam_info = analyze_scam_indicators(analysis_text, source_url)

    ai_task = asyncio.create_task(detect_ai_text(analysis_text))
    domain_task = (
        asyncio.create_task(asyncio.to_thread(check_domain_reputation, source_url))
        if source_url
        else None
    )

    claims = await extract_claims_with_ai(analysis_text)
    fact_check_queries = claims[:5] or [analysis_text[:200]]
    fact_tasks = [
        asyncio.create_task(query_fact_check_api(query[:200]))
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
    
    await asyncio.gather(*tasks)
    
    fact_checks = []
    seen_fact_checks: set[tuple[str, str | None]] = set()
    for task in fact_tasks:
        for fact_check in task.result():
            key = (fact_check.claim_text.casefold(), fact_check.url)
            if key in seen_fact_checks:
                continue
            seen_fact_checks.add(key)
            fact_checks.append(fact_check)

    ai_forensics = ai_task.result()
    domain_info = domain_task.result() if domain_task else { "score": None, "note": "Nenhuma URL fornecida" }

    serper_news_results = []
    seen_links: set[str] = set()
    for task in serper_news_tasks:
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

    ai_task = asyncio.create_task(_run_gemini_check(analysis_text, context))
    openrouter_task = asyncio.create_task(_run_openrouter_check(analysis_text))

    ai, openrouter_result = await asyncio.gather(ai_task, openrouter_task)
    ai = _merge_verdicts(ai, openrouter_result)
    ai["claims"] = claims
    ai["scam_analysis"] = scam_info

    if scam_info["is_scam"]:
        ai["verdict"] = "Scam"
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
            "text_ai_probability": ai_forensics.get("ai_probability", 0),
            "fact_checks_count": len(fact_checks),
            "serper_news_count": len(serper_news_results),
            "domain_score": domain_info.get("score"),
            "earliest_known_date": (temporal_info.get("dates_found") or [None])[0],
            "temporal_info": temporal_info,
            "source_info": source_info,
            "openrouter_available": openrouter_result is not None and not openrouter_result.get("error"),
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