from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user, DAILY_LIMITS
from app.models.user import User
from app.models.history import ContentType, Verification, VerdictLabel
from app.services.pdf_snapshot import attach_pdf_snapshot

router = APIRouter(prefix="/history")


def _report_data(row: Verification) -> dict:
    # Older imports may contain a JSON scalar/list rather than a report object.
    return row.raw_result if isinstance(row.raw_result, dict) else {}


def _display_score(row: Verification):
    report = _report_data(row)
    return None if (report.get("analysis_status") == "inconclusive"
                    or report.get("score_semantics") == "not_calibrated_source_corroboration") else row.verdict_score


def _query_input(row: Verification) -> str:
    """Return the user's original input where it is available.

    Historical rows created before `query_input` was added only have a summary,
    so they remain readable without a database migration.
    """
    if row.source_url:
        return row.source_url
    if isinstance(row.raw_result, dict):
        query = row.raw_result.get("query_input") or row.raw_result.get("filename")
        if isinstance(query, str) and query.strip():
            return query
    return row.ai_summary or "Conteúdo enviado"


@router.get("")
async def get_history(
    page:  int  = Query(1, ge=1, le=10000),
    limit: int  = Query(20, ge=1, le=50),
    search: str = Query("", max_length=200),
    content_type: Literal["all", "Text", "Url", "Image", "Audio", "Video"] = Query("all"),
    verdict: Literal["all", "Authentic", "False", "Suspicious", "Scam", "AI_Generated", "Manipulated", "Out_Of_Context"] = Query("all"),
    user:  User = Depends(get_current_user),
    db:    AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    # Apply ownership to BOTH count and result queries before every filter.
    # The legacy schema stores links as Text with a source URL.
    filters = [Verification.user_id == user.id]
    if content_type == "Url":
        filters.extend([Verification.content_type == ContentType.TEXT,
                        Verification.source_url.is_not(None), Verification.source_url != ""])
    elif content_type == "Text":
        filters.extend([Verification.content_type == ContentType.TEXT,
                        or_(Verification.source_url.is_(None), Verification.source_url == "")])
    elif content_type != "all":
        filters.append(Verification.content_type == ContentType(content_type))
    if verdict != "all":
        filters.append(Verification.verdict_label == VerdictLabel(verdict))
    term = search.strip()
    if term:
        # LIKE wildcards are user text, never a command to match every row.
        # JSON text access compiles for both PostgreSQL and SQLite.
        pattern = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        fields = (Verification.source_url, Verification.ai_summary,
                  Verification.raw_result["query_input"].as_string(),
                  Verification.raw_result["filename"].as_string())
        filters.append(or_(*(field.ilike(pattern, escape="\\") for field in fields)))

    total_q = await db.execute(
        select(func.count(Verification.id)).where(*filters)
    )
    total = total_q.scalar_one()

    rows_q = await db.execute(
        select(Verification)
        .where(*filters)
        .order_by(Verification.created_at.desc(), Verification.id.desc())
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
                "content_type":  "Url" if r.content_type == ContentType.TEXT and r.source_url else r.content_type.value,
                "query_input":   _query_input(r)[:100],
                "verdict_score": _display_score(r),
                "analysis_status": _report_data(r).get("analysis_status"),
                "veracity_status": _report_data(r).get("veracity_status"),
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
        select(func.avg(Verification.verdict_score), func.count(Verification.id)).where(
            Verification.user_id == user.id,
            Verification.raw_result["analysis_status"].as_string() == "partial",
            Verification.raw_result["score_semantics"].as_string() == "legacy_decision_index_not_probability",
            Verification.verdict_score.between(0, 100),
        )
    )
    # Inconclusive and unversioned legacy placeholders (often 50) are not an
    # available index. No eligible rows is NULL, not a fabricated zero/50.
    avg_score, indexed_count = avg_q.one()

    # Get limit for display (based on TEXTUAL for simplicity in summary)
    limit = DAILY_LIMITS.get(user.tier, {}).get("TEXTUAL", 3)
    
    return {
        "daily_used":  daily_used,
        "daily_limit": limit,
        "total":       total,
        "avg_score":   round(float(avg_score), 1) if avg_score is not None else None,
        "avg_score_count": indexed_count,
        "avg_score_semantics": "legacy_decision_index_not_probability",
        "plan":        user.tier.value,
    }


@router.get("/{v_id}")
async def get_verification(
    v_id: UUID,
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
        "query_input":   _query_input(row),
        "verdict_score": _display_score(row),
        "verdict_label": row.verdict_label.value,
        "ai_summary":    row.ai_summary,
        "raw_result":    attach_pdf_snapshot(row.raw_result, user),
        "created_at":    row.created_at.isoformat(),
    }
