from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import AnalysisRequest, AnalysisResponse
from app.core.pipeline import run_pipeline
from app.core.security import sanitize
from app.core.auth import get_current_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import VerificationLog, QueryType

router = APIRouter()


@router.post("/check-text", response_model=AnalysisResponse)
async def check_text(
    body: AnalysisRequest,
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    await verify_limit(user, db, "TEXTUAL")
    
    clean_text = sanitize(body.text)
    result = await run_pipeline(text=clean_text)

    log = VerificationLog(
        user_id    =user.id,
        query_type =QueryType.TEXT,
        query_input=clean_text[:500],
        result     =result.model_dump(),
        score      =result.score,
        verdict    =result.verdict,
        summary    =result.summary,
    )
    db.add(log)
    await db.commit()
    return result
