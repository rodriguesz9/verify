import asyncio
from app.core.gemini_analyzer import extract_claims_with_ai, generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text
from app.core.serper_client import search_news
from app.core.scam_detector import analyze_scam_indicators


async def run_pipeline(text: str, url: str | None = None) -> dict:
    """
    Verify Core Pipeline (TEXT/URL).
    Returns raw analysis data, scam detection, and final friendly report.
    """
    source_url = url
    analysis_text = text

    # Scam & Phishing quick heuristics
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

    context = {
        "scam_analysis": scam_info,
        "gptzero": ai_forensics,
        "domain": domain_info,
        "claims": claims,
        "fact_checks": [fc.model_dump() for fc in fact_checks],
        "serper_news": serper_news_results,
        "source_url": source_url,
    }

    ai = await generate_final_report(analysis_text, context)
    ai["claims"] = claims
    ai["scam_analysis"] = scam_info

    # If scam detector flagged critical patterns, ensure score and verdict reflect danger
    if scam_info["is_scam"]:
        # A confirmed local fraud pattern is stronger than the generic fallback
        # produced when an external LLM or fact-check provider is unavailable.
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
            "earliest_known_date": None
        },
        "fact_checks": fact_checks,
        "serper_news": serper_news_results,
        "domain_info": domain_info,
        "scam_analysis": scam_info
    }
