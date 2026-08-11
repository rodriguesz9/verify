import os
import httpx

SERPER_API_KEY = os.getenv("SERPERAPI_KEY", "")
NEWS_ENDPOINT = "https://google.serper.dev/news"


async def search_news(query: str) -> list[dict]:
    """
    Search Google News via Serper.dev.
    Returns a list of {title, link, snippet, date}.
    """
    if not SERPER_API_KEY:
        return []

    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {
        "q": query[:200],
        "gl": "br",
        "hl": "pt-br",
        "num": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(NEWS_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    results = []
    for item in data.get("news", [])[:5]:
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link"),
                "snippet": item.get("snippet", ""),
                "date": item.get("date"),
            }
        )
    return results
