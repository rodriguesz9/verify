from urllib.parse import urlparse
import httpx
import re

TRUSTED_DOMAINS = [
    "g1.globo", "globo.com", "bbc.", "cnn.", "folha.uol",
    "reuters.", "agenciabrasil", "estadao.", "uol.com",
    "correiobraziliense", "valor.globo", "exame.com",
    "scielo.", "gov.br", "wikipedia.org",
]

SUSPICIOUS_PATTERNS = [
    r"urgente", r"verdade[-_]?real", r"noticia[-_]?real",
    r"exclusivo[-_]?bombast", r"chocante", r"eles[-_]?nao[-_]?querem",
    r"midia[-_]?mentirosa", r"globalismo",
]


def check_domain_reputation(url: str) -> dict:
    """
    Fast, free heuristic check on a URL/domain.
    Returns a score (0-100) and a human-readable note.
    """
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        hostname = parsed.hostname or url.lower()
    except Exception:
        return {"score": 50, "note": "Não foi possível analisar o domínio.", "hostname": url}

    hostname_lower = hostname.lower()

    # Trusted
    for t in TRUSTED_DOMAINS:
        if t in hostname_lower:
            return {
                "score": 88,
                "note": f"Domínio reconhecido como fonte jornalística confiável ({hostname}).",
                "hostname": hostname,
            }

    # Suspicious keyword in hostname
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, hostname_lower):
            return {
                "score": 18,
                "note": f"Domínio contém padrão associado a desinformação ({hostname}).",
                "hostname": hostname,
            }

    # TLD check
    if hostname_lower.endswith(".gov.br") or hostname_lower.endswith(".edu.br"):
        return {"score": 92, "note": f"Domínio governamental/educacional ({hostname}).", "hostname": hostname}

    if hostname_lower.endswith((".xyz", ".click", ".buzz", ".info")):
        return {
            "score": 30,
            "note": f"TLD associado a sites de baixa confiabilidade ({hostname}).",
            "hostname": hostname,
        }

    return {"score": 55, "note": f"Domínio desconhecido – verificação manual recomendada ({hostname}).", "hostname": hostname}
