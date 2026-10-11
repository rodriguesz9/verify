"""Retrieved news are context, not factual confirmation; failures stay visible."""
import os
import httpx
from urllib.parse import urlparse

NEWS_ENDPOINT = "https://google.serper.dev/news"
WEB_ENDPOINT = "https://google.serper.dev/search"
MAX_NEWS_QUERY_CHARS = 500


class NewsSearch(list):
    def __init__(self, items=(), status="success", reason=None):
        super().__init__(items)
        self.status = status
        self.reason = reason


async def search_web(query: str) -> list[dict]:
    """One bounded search for candidate pages, never evidence from snippets.

    Long queries are refused, not silently cut (which could remove a negation
    or date). Only links/title are passed to the safe document retriever.
    """
    key = os.getenv("SERPERAPI_KEY", "").strip()
    if not key:
        return NewsSearch(status="not_configured", reason="Busca de referências não configurada.")
    if not isinstance(query, str) or not 20 <= len(query.strip()) <= 500:
        return NewsSearch(status="no_results", reason="Nenhuma frase completa cabe no limite da busca de referências; nenhum texto foi cortado.")
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
            response = await client.post(
                WEB_ENDPOINT, headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query.strip(), "gl": "br", "hl": "pt-br", "num": 5},
            )
        if response.status_code != 200:
            return NewsSearch(status="rate_limited" if response.status_code in {402, 429} else "error",
                              reason=f"Busca de referências indisponível (HTTP {response.status_code}).")
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("organic", []), list):
            raise ValueError("Resposta inválida")
        results = []
        for item in data.get("organic", [])[:5]:
            if not isinstance(item, dict) or not isinstance(item.get("link"), str):
                continue
            try:
                url = urlparse(item["link"])
                safe = (url.scheme in {"https", "http"} and url.hostname and not url.username
                        and not url.password and url.port in {None, 80, 443}
                        and len(item["link"]) <= 4096)
            except ValueError:
                safe = False
            if safe:
                results.append({"title": item.get("title", "")[:500] if isinstance(item.get("title"), str) else "",
                                "link": item["link"]})
        return NewsSearch(results, status="success" if results else "no_results")
    except httpx.TimeoutException:
        return NewsSearch(status="timeout", reason="A busca de referências excedeu o tempo permitido.")
    except Exception:
        return NewsSearch(status="error", reason="Resposta da busca de referências indisponível ou inválida.")


async def search_news(query: str) -> list[dict]:
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= MAX_NEWS_QUERY_CHARS:
        return NewsSearch(status="not_requested", reason="Busca omitida: nenhuma consulta literal cabe no limite de 500 caracteres; nenhum texto foi cortado.")
    key = os.getenv("SERPERAPI_KEY", "").strip()
    if not key:
        return NewsSearch(status="not_configured", reason="Serper não configurado.")
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
            response = await client.post(NEWS_ENDPOINT, headers={"X-API-KEY": key, "Content-Type": "application/json"},
                                         json={"q": query.strip(), "gl": "br", "hl": "pt-br", "num": 5})
        if response.status_code != 200:
            return NewsSearch(status="rate_limited" if response.status_code in {402, 429} else "error",
                              reason=f"Serper indisponível (HTTP {response.status_code}).")
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("news", []), list):
            raise ValueError("Resposta inválida")
        results = []
        for item in data.get("news", [])[:5]:
            if not isinstance(item, dict) or not isinstance(item.get("link"), str):
                continue
            url = urlparse(item["link"])
            if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password:
                continue
            results.append({"title": item.get("title", ""), "link": item["link"],
                            "snippet": item.get("snippet", ""), "date": item.get("date"), "source": item.get("source", "")})
        return NewsSearch(results, status="success" if results else "no_results")
    except Exception:
        return NewsSearch(status="error", reason="Resposta Serper indisponível ou inválida.")
