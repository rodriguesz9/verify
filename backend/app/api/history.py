from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from datetime import date, datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_user, DAILY_LIMITS
from app.models.user import User
from app.models.history import VerificationLog

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
        select(func.count(VerificationLog.id)).where(VerificationLog.user_id == user.id)
    )
    total = total_q.scalar_one()

    rows_q = await db.execute(
        select(VerificationLog)
        .where(VerificationLog.user_id == user.id)
        .order_by(VerificationLog.created_at.desc())
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
                "id":          str(r.id),
                "query_type":  r.query_type.value,
                "query_input": r.query_input[:200],
                "score":       r.score,
                "verdict":     r.verdict,
                "summary":     r.summary,
                "created_at":  r.created_at.isoformat(),
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

    daily_q = await db.execute(
        select(func.count(VerificationLog.id)).where(
            VerificationLog.user_id == user.id,
            VerificationLog.created_at >= today_start,
        )
    )
    daily_used = daily_q.scalar_one()

    total_q = await db.execute(
        select(func.count(VerificationLog.id)).where(VerificationLog.user_id == user.id)
    )
    total = total_q.scalar_one()

    avg_q = await db.execute(
        select(func.avg(VerificationLog.score)).where(VerificationLog.user_id == user.id)
    )
    avg_score = avg_q.scalar_one()

    limit = DAILY_LIMITS.get(user.plan.value, 3)
    return {
        "daily_used":  daily_used,
        "daily_limit": limit,
        "daily_left":  max(0, limit - daily_used),
        "total":       total,
        "avg_score":   round(float(avg_score), 1) if avg_score else None,
        "plan":        user.plan.value,
    }


@router.get("/{log_id}")
async def get_log(
    log_id: str,
    user:   User = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    row_q = await db.execute(
        select(VerificationLog).where(
            VerificationLog.id == log_id,
            VerificationLog.user_id == user.id,
        )
    )
    row = row_q.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    return {
        "id":          str(row.id),
        "query_type":  row.query_type.value,
        "query_input": row.query_input,
        "score":       row.score,
        "verdict":     row.verdict,
        "summary":     row.summary,
        "result":      row.result,
        "created_at":  row.created_at.isoformat(),
    }
