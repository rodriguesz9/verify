from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, field_validator
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
    texts: List[str] = Field(..., min_length=1, max_length=10)

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, texts):
        if any(not 10 <= len(sanitize(text).strip()) <= 5000 for text in texts):
            raise ValueError("Cada mensagem deve ter de 10 a 5000 caracteres.")
        return texts


async def _process_one(text: str, user: User | None, db: AsyncSession) -> dict:
    clean_text = sanitize(text)
    try:
        result = await run_pipeline(text=clean_text)
        ai = result["report"]
        ai["query_input"] = clean_text
        ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
        ai["serper_news"] = result.get("serper_news", [])
        metrics = result["metrics"]

        return ai, metrics
    except Exception:
        return {
            "query_input": clean_text,
            "verdict": "Suspicious",
            "score": 0,
            "summary": "Não foi possível analisar esta mensagem. Nenhum veredito conclusivo foi produzido.",
            "plain_explanation": "Não foi possível analisar esta mensagem.",
            "error": True,
            "analysis_status": "inconclusive",
        }, {}


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

    texts_to_check = body.texts

    await verify_limit(user, db, "TEXTUAL", requested=len(texts_to_check))

    # AsyncSession is not safe for concurrent writes. Analyze concurrently, persist serially.
    tasks = [_process_one(text, None, db) for text in texts_to_check]
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
                "analysis_status": "inconclusive",
            })
        else:
            report, metrics = r
            clean_results.append(report)
            if user and not report.get("error"):
                verification = Verification(user_id=user.id, content_type=ContentType.TEXT,
                    verdict_score=report["score"], verdict_label=report["verdict"],
                    ai_summary=report["summary"], raw_result=report)
                db.add(verification)
                await db.flush()
                db.add(AnalysisMetrics(verification_id=verification.id,
                                       text_ai_probability=metrics.get("text_ai_probability")))

    if user:
        await db.commit()

    return {"results": clean_results}
