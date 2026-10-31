from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List
import asyncio
import html
from app.models.schemas import AnalysisRequest
from app.core.pipeline import run_pipeline
from app.core.security import sanitize
from app.core.auth import get_optional_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType
from app.services.extracted_text_review import verify_text_review, MAX_REVIEW_TOKEN_BYTES
from app.services.pdf_snapshot import attach_pdf_snapshot
from datetime import datetime, timezone

router = APIRouter()


class BatchAnalysisRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=10)

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, texts):
        if any(not 10 <= len(sanitize(text).strip()) <= 5000 for text in texts):
            raise ValueError("Cada mensagem deve ter de 10 a 5000 caracteres.")
        return texts


class ReviewedTextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=10, max_length=5000)
    review_token: str = Field(..., max_length=MAX_REVIEW_TOKEN_BYTES)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value):
        literal = value.strip()
        clean = sanitize(value)
        if not 10 <= len(literal) <= 5000 or html.unescape(clean) != html.unescape(literal):
            raise ValueError("Confira um texto de 10 a 5000 caracteres, sem marcação HTML.")
        # JSON/React render plain text. Reject markup instead of silently
        # removing it, and never turn a literal '&'/'<' into an HTML entity
        # in the confirmed statement or incorrectly mark it as a user edit.
        return literal


@router.post("/check-extracted-text")
async def check_extracted_text(body: ReviewedTextRequest, user: User | None = Depends(get_optional_user),
                               db: AsyncSession = Depends(get_db)):
    # Validate provenance/owner BEFORE quota, external retrieval or persistence.
    source = verify_text_review(body.review_token, user)
    await verify_limit(user, db, "TEXTUAL")
    result = await run_pipeline(text=body.text, use_ai_extraction=False, use_detailed_report=True,
                                use_gemini_report=True)
    report = {**result["report"], "content_type": "text", "query_input": body.text,
              "analyzed_at": datetime.now(timezone.utc).isoformat(),
              "fact_checks": [fc.model_dump() for fc in result.get("fact_checks", [])],
              "serper_news": result.get("serper_news", []),
              "serper_web": result.get("serper_web", []),
              "text_review": {**source, "status": "user_confirmed", "reviewed_text": body.text,
                              "changed": body.text != source["original_text"].strip(),
                              "reviewed_at": datetime.now(timezone.utc).isoformat()}}
    report["limitations"] = [*report.get("limitations", []),
        "Nova checagem apenas do texto conferido pelo usuário. A leitura automática original foi preservada; a edição não comprova correspondência ao arquivo nem autenticidade da mídia."]
    if user:
        verification = Verification(user_id=user.id, content_type=ContentType.TEXT,
            verdict_score=report["score"], verdict_label=report["verdict"], ai_summary=report["summary"], raw_result=report)
        db.add(verification)
        await db.flush()
        db.add(AnalysisMetrics(verification_id=verification.id,
                              text_ai_probability=result.get("metrics", {}).get("text_ai_probability")))
        await db.commit()
    return attach_pdf_snapshot(report, user)


async def _process_one(text: str, user: User | None, db: AsyncSession) -> dict:
    clean_text = sanitize(text)
    try:
        result = await run_pipeline(text=clean_text, use_detailed_report=True, use_gemini_report=True)
        ai = {**result["report"], "content_type": "text", "query_input": clean_text,
              "analyzed_at": datetime.now(timezone.utc).isoformat()}
        ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
        ai["serper_news"] = result.get("serper_news", [])
        ai["serper_web"] = result.get("serper_web", [])
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

    result = await run_pipeline(text=clean_text, use_detailed_report=True, use_gemini_report=True)
    ai = {**result["report"], "content_type": "text", "query_input": clean_text,
          "analyzed_at": datetime.now(timezone.utc).isoformat()}
    ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
    ai["serper_news"] = result.get("serper_news", [])
    ai["serper_web"] = result.get("serper_web", [])
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

    return attach_pdf_snapshot(ai, user)


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

    return {"results": [attach_pdf_snapshot(report, user) for report in clean_results]}
