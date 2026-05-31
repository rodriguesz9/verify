import asyncio
from app.core.gemini_analyzer import generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text
from app.models.schemas import AnalysisResponse

async def run_pipeline(text: str, url: str | None = None) -> dict:
    """
    Antigravity Core Pipeline (TEXT/URL).
    Returns raw analysis data and the final report.
    """
    fact_task   = asyncio.create_task(query_fact_check_api(text[:200]))
    ai_task     = asyncio.create_task(detect_ai_text(text))
    
    tasks = [fact_task, ai_task]
    if url:
        domain_task = asyncio.create_task(asyncio.to_thread(check_domain_reputation, url))
        tasks.append(domain_task)
    
    await asyncio.gather(*tasks)
    
    fact_checks = fact_task.result()
    ai_forensics = ai_task.result()
    domain_info = domain_task.result() if url else { "score": None, "note": "Nenhuma URL fornecida" }

    context = {
        "gptzero": ai_forensics,
        "domain": domain_info,
        "fact_checks": [fc.model_dump() for fc in fact_checks[:3]],
        "source_url": url,
    }
    
    ai = await generate_final_report(text, context)

    # Return structured dict for DB & API
    return {
        "report": ai,
        "metrics": {
            "text_ai_probability": ai_forensics.get("ai_probability", 0),
            "fact_checks_count": len(fact_checks),
            "domain_score": domain_info.get("score"),
            "earliest_known_date": None
        },
        "fact_checks": fact_checks,
        "domain_info": domain_info
    }
