"""
Reverse Search & Historical Provenance Service (Layer 3)
Integrates Wayback Machine (anachronism check), TinEye and SerpAPI.
"""

import os
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional


SERP_API_URL = "https://serpapi.com/search.json"


async def search_google_lens_reverse(image_bytes: bytes, filename: str = "image.jpg") -> Dict[str, Any]:
    """
    Uses SerpAPI to perform reverse image search (Google Lens equivalent).
    Checks if the image appears elsewhere on the web and can help determine
    if it's an old photo being reused with new context.
    """
    # Serper and SerpAPI are different providers; their keys are not interchangeable.
    # Google Lens requires a public image URL or an ID from the separate upload API.
    # Never publish private user uploads automatically just to enable this layer.
    return {"available": False, "status": "skipped", "matches_count": None,
            "reason": "Busca Lens exige URL pública ou upload explícito ao provedor; indisponível para este arquivo privado.",
            "summary": "Busca reversa não realizada. Isso não significa ausência de correspondências."}
async def check_wayback_machine(url_or_query: str) -> Dict[str, Any]:
    """
    Checks the Internet Archive (Wayback Machine) to see if a URL or resource
    was first seen in earlier years, exposing recycled old stories as 'breaking news'.
    """
    enabled = os.getenv("WAYBACK_API_ENABLED", "true").lower() == "true"
    if not enabled or not url_or_query:
        return {"checked": False, "found": False, "status": "disabled" if not enabled else "skipped"}

    wayback_api = f"https://archive.org/wayback/available?url={url_or_query}"
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(wayback_api)
            if resp.status_code != 200:
                return {"checked": False, "found": False, "status": "error",
                        "error": f"Consulta Wayback indisponível (HTTP {resp.status_code})."}
            if resp.status_code == 200:
                data = resp.json()
                snapshots = data.get("archived_snapshots", {})
                closest = snapshots.get("closest")
                if closest and closest.get("available"):
                    timestamp_str = closest.get("timestamp", "") # format: YYYYMMDDhhmmss
                    year = timestamp_str[:4] if len(timestamp_str) >= 4 else "desconhecido"
                    formatted_date = f"{timestamp_str[6:8]}/{timestamp_str[4:6]}/{timestamp_str[:4]}" if len(timestamp_str) >= 8 else year
                    
                    is_old = False
                    try:
                        archived_year = int(year)
                        if archived_year < datetime.now().year:
                            is_old = True
                    except Exception:
                        pass

                    return {
                        "checked": True,
                        "status": "success",
                        "found": True,
                        "snapshot_date": formatted_date,
                        "raw_timestamp": timestamp_str,
                        "archive_url": closest.get("url"),
                        "is_anachronistic_recycled": False,
                        "summary": (
                            f"Registro disponível da URL em {formatted_date}. Não comprova primeira publicação, identidade da imagem ou descontextualização."
                        )
                    }
        return {"checked": True, "found": False, "status": "no_results", "summary": "Nenhum registro foi retornado pela Wayback nesta consulta; não comprova ausência de arquivo histórico."}
    except Exception:
        # Transport/JSON exceptions can include the original private query URL.
        return {"checked": False, "found": False, "status": "error", "error": "Consulta Wayback indisponível ou resposta inválida."}


async def check_tineye_reverse_search(image_bytes: bytes, filename: str = "image.jpg") -> Dict[str, Any]:
    """
    Searches TinEye API for exact or near-duplicate matches across the web.
    """
    api_key = os.getenv("TINEYE_API_KEY", "").strip()
    if not api_key:
        return {
            "available": False,
            "status": "skipped",
            "matches_count": None,
            "reason": "TINEYE_API_KEY não configurada"
        }

    # TinEye Search Endpoint
    tineye_url = "https://api.tineye.com/rest/search/"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            files = {"image": (filename, image_bytes)}
            resp = await client.post(
                tineye_url,
                headers={"x-api-key": api_key},
                files=files
            )
            if resp.status_code == 200:
                data = resp.json()
                results_container = data.get("results") if isinstance(data, dict) else None
                results = results_container.get("matches") if isinstance(results_container, dict) else None
                if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
                    return {"available": False, "status": "invalid_response", "matches_count": None,
                            "error": "Busca TinEye não retornou correspondências em formato válido."}
                return {
                    "available": True,
                    "status": "success",
                    "matches_count": len(results),
                    "oldest_match": results[0] if results else None,
                    "top_matches": results[:3]
                }
            return {
                "available": False,
                "status": {401: "invalid_credentials", 403: "access_denied", 402: "quota_exhausted", 429: "rate_limited"}.get(resp.status_code, "error"),
                "matches_count": None,
                "error": f"HTTP {resp.status_code}"
            }
    except Exception:
        return {"available": False, "status": "error", "matches_count": None,
                "error": "Busca TinEye indisponível ou resposta inválida."}


async def search_context_and_provenance(
    text: str = "",
    url: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    filename: str = "upload.jpg"
) -> Dict[str, Any]:
    """
    Consolidates reverse search, fact-check tools and historical provenance.
    """
    tasks = []

    # 1. Wayback Machine (if URL provided)
    if url:
        tasks.append(check_wayback_machine(url))
    else:
        tasks.append(asyncio.sleep(0, result={"checked": False, "found": False}))

    # 2. TinEye (if image bytes provided)
    if image_bytes:
        tasks.append(check_tineye_reverse_search(image_bytes, filename))
    else:
        tasks.append(asyncio.sleep(0, result={"available": False, "matches_count": None}))

    # 3. SerpAPI Google Lens reverse (if image bytes provided)
    if image_bytes:
        tasks.append(search_google_lens_reverse(image_bytes, filename))
    else:
        tasks.append(asyncio.sleep(0, result={"available": False, "matches_count": None}))

    wayback_res, tineye_res, lens_res = await asyncio.gather(*tasks)

    return {
        "wayback": wayback_res,
        "tineye": tineye_res,
        "google_lens": lens_res,
    }
