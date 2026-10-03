import os
import httpx

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

async def reverse_image_search(image_url: str) -> dict:
    """
    Search for image origin and context using SerpApi (Google Reverse Image Search).
    """
    if not SERPAPI_KEY:
        return {"available": False, "reason": "SerpApi key not configured."}

    params = {
        "engine": "google_reverse_image",
        "image_url": image_url,
        "api_key": SERPAPI_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
            response = await client.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract historical find info
            image_results = data.get("image_results", [])
            visual_matches = data.get("visual_matches", [])
            
            # Simple heuristic: if we find matches from long ago
            # SerpApi doesn't always give date directly in the list, but we can look for snippets
            
            return {
                "available": True,
                "matches_count": len(image_results) + len(visual_matches),
                "image_results": image_results[:5],
                "raw": data
            }
    except Exception:
        # HTTP errors may include api_key in the request URL. Never echo them.
        return {"available": False, "status": "error", "reason": "Busca SerpAPI indisponível ou resposta inválida."}
