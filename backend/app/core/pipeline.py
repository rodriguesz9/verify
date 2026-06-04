import asyncio
from app.core.gemini_analyzer import extract_claims_with_ai, generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text


async def run_pipeline(text: str, url: str | None = None) -> dict:
    """
    Antigravity Core Pipeline (TEXT/URL).
    Returns raw analysis data and the final report.
    """
    source_url = url
    analysis_text = text

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
    
    tasks = [*fact_tasks, ai_task]
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

    context = {
        "gptzero": ai_forensics,
        "domain": domain_info,
        "claims": claims,
        "fact_checks": [fc.model_dump() for fc in fact_checks[:3]],
        "source_url": source_url,
    }

    ai = await generate_final_report(analysis_text, context)
    ai["claims"] = claims

    # Return structured dict for DB & API
    return {
        "report": ai,
        "claims": claims,
        "metrics": {
            "text_ai_probability": ai_forensics.get("ai_probability", 0),
            "fact_checks_count": len(fact_checks),
            "domain_score": domain_info.get("score"),
            "earliest_known_date": None
        },
        "fact_checks": fact_checks,
        "domain_info": domain_info
    }
