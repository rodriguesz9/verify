from fastapi import APIRouter, Depends, HTTPException
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import MAX_ANALYSIS_URL_LENGTH, UrlRequest
from app.core.pipeline import run_pipeline
from app.core.auth import get_optional_user, verify_limit
from app.core.database import get_db
from app.models.user import User
from app.models.history import Verification, AnalysisMetrics, ContentType
from app.services.public_fetch import fetch_public_resource
from app.services.pdf_snapshot import attach_pdf_snapshot
from app.services.metric_dates import absolute_metric_date

router = APIRouter()
MAX_REDIRECTS = 5
HIDDEN_STYLE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))"
    r"\s*(?:!\s*important\s*)?(?:;|$)", re.IGNORECASE,
)


def normalize_analysis_url(value: str) -> str:
    url = value.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    if len(url) > MAX_ANALYSIS_URL_LENGTH:
        raise HTTPException(422, "O link pode ter até 512 caracteres, incluindo https://. O endereço informado não foi cortado. Cole um endereço direto mais curto para a mesma página.")
    return url


def validate_final_analysis_url(value: str) -> str:
    # public_fetch returns a canonical URL after redirects/percent-encoding.
    # It can be longer than the submitted value, even without a redirect.
    if not isinstance(value, str) or not value:
        raise HTTPException(422, "A consulta não retornou um endereço final válido.")
    if len(value) > MAX_ANALYSIS_URL_LENGTH:
        raise HTTPException(422, "O endereço final da página tem mais de 512 caracteres. A análise não foi realizada e nenhum endereço foi cortado.")
    return value


async def fetch_page_text(url: str) -> dict:
    resource = await fetch_public_resource(
        url, max_bytes=2 * 1024 * 1024, max_redirects=MAX_REDIRECTS,
        allowed_types={"text/html", "application/xhtml+xml", "text/plain"},
    )
    try:
        document = resource.data.decode(resource.encoding, errors="replace")
    except LookupError:
        document = resource.data.decode("utf-8", errors="replace")
    meta = {"title": "", "description": ""}
    if resource.content_type == "text/plain":
        # Literal angle brackets are not markup in a text/plain response.
        text = re.sub(r"\s+", " ", document).strip()
    else:
        soup = BeautifulSoup(document, "html.parser")
        meta["title"] = soup.title.get_text(strip=True)[:500] if soup.title else ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if desc_tag:
            meta["description"] = desc_tag.get("content", "")[:1000]

        # Remove hidden parents before choosing the main region. Do not delete
        # <header>: an article's headline may contain a decisive negation.
        for tag in list(soup.find_all(True)):
            if tag.attrs is None:  # already removed with its ancestor
                continue
            if (tag.name in {"script", "style", "nav", "footer", "aside", "form", "template", "noscript", "head"}
                    or tag.has_attr("hidden") or str(tag.get("aria-hidden", "")).lower() == "true"
                    or HIDDEN_STYLE.search(str(tag.get("style", "")))):
                tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        text = re.sub(r"\s+", " ", main.get_text(separator=" ", strip=True)).strip()
    
    return {
        "text": text[:5000],
        "meta": meta,
        "final_url": resource.final_url,
        "extraction_details": {"method": "plain_text" if resource.content_type == "text/plain" else "static_html",
                               "truncated": len(text) > 5000, "rendered_browser": False},
    }


@router.post("/check-url")
async def check_url(
    body: UrlRequest,
    user: User | None  = Depends(get_optional_user),
    db:   AsyncSession = Depends(get_db),
):
    url = normalize_analysis_url(body.url)
    await verify_limit(user, db, "TEXTUAL")

    try:
        scraped = await fetch_page_text(url)
        page_text = scraped["text"]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Não foi possível extrair o texto desta URL.") from exc

    if len(page_text) < 50:
        raise HTTPException(status_code=422, detail="Conteúdo insuficiente para auditoria.")

    source_url = validate_final_analysis_url(scraped.get("final_url", url))
    result = await run_pipeline(text=page_text, url=source_url, use_detailed_report=True)
    ai = {**result["report"], "content_type": "url", "source_text": page_text,
          "analyzed_at": datetime.now(timezone.utc).isoformat()}
    ai["query_input"] = url
    ai["source_url"] = source_url
    ai["source_extraction"] = scraped.get("extraction_details", {})
    ai["limitations"] = [*ai.get("limitations", []),
                          "Leitura estática do texto principal: não executa JavaScript nem resolve toda a visibilidade por CSS; não certifica o site inteiro."]
    if ai["source_extraction"].get("truncated"):
        ai["limitations"].append("Apenas os primeiros 5.000 caracteres extraídos foram analisados; o restante da página não foi checado.")
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
            earliest_known_date=absolute_metric_date(metrics.get("earliest_known_date"))
        )
        db.add(m)
        await db.commit()

    return attach_pdf_snapshot(ai, user)
