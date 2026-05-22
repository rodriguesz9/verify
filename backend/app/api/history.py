from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_user, DAILY_LIMITS
from app.models.user import User
from app.models.history import Verification

router = APIRouter(prefix="/history")


@router.get("")
async def get_history(
    page:  int  = Query(1, ge=1),
    limit: int  = Query(20, ge=1, le=50),
    user:  User = Depends(get_current_user),
    db:    AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit

    total_q = await db.execute(
        select(func.count(Verification.id)).where(Verification.user_id == user.id)
    )
    total = total_q.scalar_one()

    rows_q = await db.execute(
        select(Verification)
        .where(Verification.user_id == user.id)
        .order_by(Verification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = rows_q.scalars().all()

    return {
        "total": total,
        "page":  page,
        "limit": limit,
        "items": [
            {
                "id":            str(r.id),
                "content_type":  r.content_type.value,
                "query_input":   r.ai_summary[:100] if not r.source_url else r.source_url,
                "verdict_score": r.verdict_score,
                "verdict_label": r.verdict_label.value,
                "ai_summary":    r.ai_summary,
                "created_at":    r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    # Note: Simplified count for total used today across all types
    daily_q = await db.execute(
        select(func.count(Verification.id)).where(
            Verification.user_id == user.id,
            Verification.created_at >= today_start,
        )
    )
    daily_used = daily_q.scalar_one()

    total_q = await db.execute(
        select(func.count(Verification.id)).where(Verification.user_id == user.id)
    )
    total = total_q.scalar_one()

    avg_q = await db.execute(
        select(func.avg(Verification.verdict_score)).where(Verification.user_id == user.id)
    )
    avg_score = avg_q.scalar_one()

    # Get limit for display (based on TEXTUAL for simplicity in summary)
    limit = DAILY_LIMITS.get(user.tier, {}).get("TEXTUAL", 3)
    
    return {
        "daily_used":  daily_used,
        "daily_limit": limit,
        "total":       total,
        "avg_score":   round(float(avg_score), 1) if avg_score else 0,
        "plan":        user.tier.value,
    }


@router.get("/{v_id}")
async def get_verification(
    v_id: str,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    row_q = await db.execute(
        select(Verification).where(
            Verification.id == v_id,
            Verification.user_id == user.id,
        )
    )
    row = row_q.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
        
    return {
        "id":            str(row.id),
        "content_type":  row.content_type.value,
        "query_input":   row.source_url or "Conteúdo Direto",
        "verdict_score": row.verdict_score,
        "verdict_label": row.verdict_label.value,
        "ai_summary":    row.ai_summary,
        "raw_result":    row.raw_result,
        "created_at":    row.created_at.isoformat(),
    }
