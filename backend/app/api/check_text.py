from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
import asyncio
from app.models.schemas import AnalysisRequest
from app.core.pipeline import run_pipeline
from app.core.security import sanitize
from app.core.auth import get_optional_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType

router = APIRouter()


class BatchAnalysisRequest(BaseModel):
    texts: List[str]


async def _process_one(text: str, user: User | None, db: AsyncSession) -> dict:
    clean_text = sanitize(text)
    try:
        result = await run_pipeline(text=clean_text)
        ai = result["report"]
        ai["query_input"] = clean_text
        ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
        ai["serper_news"] = result.get("serper_news", [])
        metrics = result["metrics"]

        if user:
            v = Verification(
                user_id=user.id,
                content_type=ContentType.TEXT,
                verdict_score=ai["score"],
                verdict_label=ai["verdict"],
                ai_summary=ai["summary"],
                raw_result=ai
            )
            db.add(v)
            await db.flush()

            m = AnalysisMetrics(
                verification_id=v.id,
                text_ai_probability=metrics["text_ai_probability"]
            )
            db.add(m)

        return ai
    except Exception as e:
        return {
            "query_input": clean_text,
            "verdict": "Suspicious",
            "score": 0,
            "summary": f"Erro ao analisar: {str(e)[:80]}",
            "plain_explanation": "Não foi possível analisar esta mensagem.",
            "error": True,
        }


@router.post("/check-text")
async def check_text(
    body: AnalysisRequest,
    user: User | None = Depends(get_optional_user),
    db:   AsyncSession = Depends(get_db),
):
    await verify_limit(user, db, "TEXTUAL")
    clean_text = sanitize(body.text)

    result = await run_pipeline(text=clean_text)
    ai = result["report"]
    ai["query_input"] = clean_text
    ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
    ai["serper_news"] = result.get("serper_news", [])
    metrics = result["metrics"]

    if user:
        v = Verification(
            user_id=user.id,
            content_type=ContentType.TEXT,
            verdict_score=ai["score"],
            verdict_label=ai["verdict"],
            ai_summary=ai["summary"],
            raw_result=ai
        )
        db.add(v)
        await db.flush()

        m = AnalysisMetrics(
            verification_id=v.id,
            text_ai_probability=metrics["text_ai_probability"]
        )
        db.add(m)
        await db.commit()

    return ai


@router.post("/check-text-batch")
async def check_text_batch(
    body: BatchAnalysisRequest,
    user: User | None = Depends(get_optional_user),
    db:   AsyncSession = Depends(get_db),
):
    if not body.texts:
        return {"results": []}

    texts_to_check = body.texts[:10]

    await verify_limit(user, db, "TEXTUAL")

    tasks = [_process_one(text, user, db) for text in texts_to_check]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    clean_results = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            clean_results.append({
                "query_input": sanitize(body.texts[i]),
                "verdict": "Suspicious",
                "score": 0,
                "summary": "Erro interno na análise.",
                "error": True,
            })
        else:
            clean_results.append(r)

    if user:
        await db.commit()

    return {"results": clean_results}
