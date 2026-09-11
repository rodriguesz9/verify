from fastapi import APIRouter, Depends, HTTPException
import httpx
from bs4 import BeautifulSoup
import re
import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import UrlRequest
from app.core.pipeline import run_pipeline
from app.core.security import sanitize
from app.core.auth import get_optional_user, get_current_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType

router = APIRouter()
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AntigravityBot/1.0)"}
MAX_REDIRECTS = 5


def _is_public_ip(address: str) -> bool:
    """Allow only globally routable IP addresses for user-supplied URLs."""
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def _resolve_public_host(hostname: str) -> None:
    normalized = hostname.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"}:
        raise HTTPException(status_code=400, detail="Endereço local não pode ser verificado.")

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Não foi possível localizar o domínio informado.") from exc

    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise HTTPException(status_code=400, detail="Endereço privado ou reservado não pode ser verificado.")


async def _validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise HTTPException(status_code=400, detail="Informe uma URL pública válida com http ou https.")
    await asyncio.to_thread(_resolve_public_host, parsed.hostname)


async def fetch_page_text(url: str) -> dict:
    """Robust scraper for Antigravity Core."""
    current_url = url
    async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await _validate_public_url(current_url)
            resp = await client.get(current_url)
            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    raise HTTPException(status_code=400, detail="Redirecionamento sem destino válido.")
                current_url = urljoin(current_url, location)
                continue
            resp.raise_for_status()
            break
        else:
            raise HTTPException(status_code=400, detail="A URL excedeu o limite de redirecionamentos.")
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Metadata
    meta = {
        "title": soup.title.string if soup.title else "",
        "description": "",
    }
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_tag:
        meta["description"] = desc_tag.get("content", "")

    # Cleanup
    for tag in soup(["script", "style", "nav", "footer", "aside", "header", "form"]):
        tag.decompose()
        
    # Main content
    main = soup.find("main") or soup.find("article") or soup.body
    text = re.sub(r"\s+", " ", main.get_text(separator=" ", strip=True)).strip()
    
    return {
        "text": text[:5000],
        "meta": meta
    }


@router.post("/check-url")
async def check_url(
    body: UrlRequest,
    user: User | None  = Depends(get_optional_user),
    db:   AsyncSession = Depends(get_db),
):
    await verify_limit(user, db, "TEXTUAL")
    
    url = sanitize(body.url.strip())
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        scraped = await fetch_page_text(url)
        page_text = scraped["text"]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Acesso negado ou erro na URL: {str(exc)[:100]}")

    if len(page_text) < 50:
        raise HTTPException(status_code=422, detail="Conteúdo insuficiente para auditoria.")

    result = await run_pipeline(text=page_text, url=url)
    ai = result["report"]
    ai["query_input"] = url
    ai["fact_checks"] = [fc.model_dump() for fc in result.get("fact_checks", [])]
    ai["serper_news"] = result.get("serper_news", [])
    metrics = result["metrics"]

    if user:
        v = Verification(
            user_id=user.id,
            content_type=ContentType.TEXT,
            source_url=url,
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
