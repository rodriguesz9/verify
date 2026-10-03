from fastapi import APIRouter, Depends, HTTPException
from bs4 import BeautifulSoup
import re

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import UrlRequest
from app.core.pipeline import run_pipeline
from app.core.auth import get_optional_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType
from app.services.public_fetch import fetch_public_resource

router = APIRouter()
MAX_REDIRECTS = 5


async def fetch_page_text(url: str) -> dict:
    resource = await fetch_public_resource(
        url, max_bytes=2 * 1024 * 1024, max_redirects=MAX_REDIRECTS,
        allowed_types={"text/html", "application/xhtml+xml", "text/plain"},
    )
    try:
        document = resource.data.decode(resource.encoding, errors="replace")
    except LookupError:
        document = resource.data.decode("utf-8", errors="replace")
    soup = BeautifulSoup(document, "html.parser")
    
    # Metadata
    meta = {
        "title": soup.title.get_text(strip=True)[:500] if soup.title else "",
        "description": "",
    }
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_tag:
        meta["description"] = desc_tag.get("content", "")[:1000]

    # Cleanup
    for tag in soup(["script", "style", "nav", "footer", "aside", "header", "form"]):
        tag.decompose()
        
    # Main content
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = re.sub(r"\s+", " ", main.get_text(separator=" ", strip=True)).strip()
    
    return {
        "text": text[:5000],
        "meta": meta,
        "final_url": resource.final_url,
    }


@router.post("/check-url")
async def check_url(
    body: UrlRequest,
    user: User | None  = Depends(get_optional_user),
    db:   AsyncSession = Depends(get_db),
):
    await verify_limit(user, db, "TEXTUAL")
    
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        scraped = await fetch_page_text(url)
        page_text = scraped["text"]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Não foi possível extrair o texto desta URL.") from exc

    if len(page_text) < 50:
        raise HTTPException(status_code=422, detail="Conteúdo insuficiente para auditoria.")

    source_url = scraped.get("final_url", url)
    result = await run_pipeline(text=page_text, url=source_url)
    ai = result["report"]
    ai["query_input"] = url
    ai["source_url"] = source_url
    ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
    ai["serper_news"] = result.get("serper_news", [])
    metrics = result["metrics"]

    if user:
        v = Verification(
            user_id=user.id,
            content_type=ContentType.TEXT,
            source_url=source_url,
            verdict_score=ai["score"],
            verdict_label=ai["verdict"],
            ai_summary=ai["summary"],
            raw_result=ai
        )
        db.add(v)
        await db.flush()

        m = AnalysisMetrics(
            verification_id=v.id,
            text_ai_probability=metrics["text_ai_probability"],
            earliest_known_date=metrics["earliest_known_date"]
        )
        db.add(m)
        await db.commit()

    return ai
