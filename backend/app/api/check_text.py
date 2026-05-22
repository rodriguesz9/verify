from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import AnalysisRequest
from app.core.pipeline import run_pipeline
from app.core.security import sanitize
from app.core.auth import get_current_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType

router = APIRouter()

@router.post("/check-text")
async def check_text(
    body: AnalysisRequest,
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    await verify_limit(user, db, "TEXTUAL")
    clean_text = sanitize(body.text)
    
    result = await run_pipeline(text=clean_text)
    ai = result["report"]
    metrics = result["metrics"]

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
