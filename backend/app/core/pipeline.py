import asyncio
from app.core.gemini_analyzer import generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text
from app.models.schemas import AnalysisResponse

async def run_pipeline(text: str, url: str | None = None) -> AnalysisResponse:
    """
    Antigravity Core Pipeline (TEXT/URL):
    1. Parallel Fact Checking & AI Text Detection
    2. Parallel Domain Reputation
    3. Final Orchestration with Gemini 3.1 Lite
    """
    # Parallel forensic collection
    fact_task   = asyncio.create_task(query_fact_check_api(text[:200]))
    ai_task     = asyncio.create_task(detect_ai_text(text))
    
    tasks = [fact_task, ai_task]
    if url:
        domain_task = asyncio.create_task(asyncio.to_thread(check_domain_reputation, url))
        tasks.append(domain_task)
    
    await asyncio.gather(*tasks)
    
    fact_checks = fact_task.result()
    ai_forensics = ai_task.result()
    domain_info = domain_task.result() if url else {"score": 70, "note": "Texto direto"}

    # Consolidate technical context
    context = {
        "gptzero": ai_forensics,
        "domain": domain_info,
        "fact_checks": [fc.model_dump() for fc in fact_checks[:3]],
        "source_url": url,
    }

    # Final Orchestration
    ai = await generate_final_report(text, context)

    return AnalysisResponse(
        score              =int(ai.get("score", 50)),
        semantic_score     =int(ai.get("semantic_score", 50)),
        domain_score       =domain_info.get("score", 70),
        sensationalism     =int(ai.get("sensationalism", 50)),
        verdict            =ai.get("verdict", "SUSPEITO"),
        summary            =ai.get("summary", ""),
        red_flags          =ai.get("red_flags", []),
        positive_signals   =ai.get("positive_signals", []),
        logical_fallacies  =ai.get("logical_fallacies", []),
        emotional_triggers =bool(ai.get("emotional_triggers", False)),
        fact_checks        =fact_checks,
        domain_note        =domain_info.get("note", ""),
        source_url         =url,
        recommended_sources=ai.get("recommended_sources", []),
    )
