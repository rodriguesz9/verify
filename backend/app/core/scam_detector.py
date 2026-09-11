import re
from typing import Dict, Any, List

SCAM_PATTERNS = [
    {
        "category": "Golpe do Pix / Dinheiro Fácil",
        "regex": r"(pix.*aprovado|pague\s+(uma\s+)?taxa|taxa.*(liberar|receber|resgatar)|devolu[cç][aã]o\s+do\s+pix|resgate\s+(de\s+)?valores|valores\s+esquecidos?.*pix|saldo\s+esquecido|pix\s+em\s+dobro|multiplicador\s+de\s+pix|taxa\s+para\s+liberar\s+saldo|taxa\s+de\s+r\$\s*\d+.*liberar|chave\s+pix.*ganhe)",
        "risk_level": "ALTO",
        "description": "Promessa de resgate de valores ou multiplicação via Pix. Bancos e governo nunca cobram taxa para devolver dinheiro."
    },
    {
        "category": "Falsa Taxa dos Correios / Alfândega",
        "regex": r"(correios.*encomenda.*retida|correios.*objeto|taxa\s+alfandeg[aá]ria|objeto\s+aguardando\s+pagamento|alfandega.*taxa|libera[cç][aã]o\s+de\s+pacote|sua\s+encomenda\s+est[aá]\s+presa)",
        "risk_level": "ALTO",
        "description": "Golpe comum usando o nome dos Correios para cobrar falsas taxas de liberação de compras."
    },
    {
        "category": "Falso Benefício / INSS / Bolsa Família",
        "regex": r"(cad[uú]nico.*atualiz|prova\s+de\s+vida.*whatsapp|revis[aã]o\s+do\s+inss.*clique|aux[ií]lio.*liberado.*link|novo\s+vale\s+g[aá]s.*cadastro|benef[ií]cio.*bloqueado.*regularize)",
        "risk_level": "ALTO",
        "description": "Tentativa de roubo de dados pessoais ou conta Gov.br se passando por programas sociais."
    },
    {
        "category": "Golpe do Falso Parente / Novo Número",
        "regex": r"(troquei\s+de\s+n[uú]mero|salva\s+meu\s+n[uú]mero\s+novo|meu\s+celular\s+quebrou.*pix|m[aã]e.*preciso\s+pagar\s+uma\s+conta|pai.*preciso\s+de\s+uma\s+ajuda.*pix)",
        "risk_level": "CRÍTICO",
        "description": "Criminoso finge ser filho(a) ou parente com número novo pedindo dinheiro ou pagamento urgente."
    },
    {
        "category": "Falsa Promoção / Brinde Grátis",
        "regex": r"(ganhe\s+brinde\s+gr[aá]tis|anivers[aá]rio.*distribuindo|resgate\s+seu\s+vale|promo[cç][aã]o.*compartilhe\s+com\s+\d+\s+amigos|comemore\s+o\s+anivers[aá]rio.*ganhe)",
        "risk_level": "ALTO",
        "description": "Página falsa que pede para compartilhar com contatos do WhatsApp para supostamente receber prêmio."
    },
    {
        "category": "Falso Emprego / Tarefa Online",
        "regex": r"(trabalhe\s+avaliando\s+v[ií]deos|ganhe\s+de\s+r\$\s*\d+.*dia|renda\s+extra.*telegram|curta\s+v[ií]deos.*ganhe\s+dinheiro|avalia[cç][aã]o\s+remunerada)",
        "risk_level": "ALTO",
        "description": "Golpe das tarefas diárias que exige depósitos prévios para liberar supostos ganhos."
    }
]

SUSPICIOUS_DOMAINS_TLD = [".xyz", ".top", ".club", ".online", ".site", ".cc", ".buzz", ".work", ".click", ".vip"]

def analyze_scam_indicators(text: str, url: str | None = None) -> Dict[str, Any]:
    """
    Scans text and URLs for common Brazilian scams, phishing attempts,
    and elderly-targeted fraud patterns.
    """
    matches: List[Dict[str, str]] = []
    text_lower = text.lower()
    
    # Check text patterns
    for pattern in SCAM_PATTERNS:
        if re.search(pattern["regex"], text_lower, re.IGNORECASE):
            matches.append({
                "category": pattern["category"],
                "risk_level": pattern["risk_level"],
                "description": pattern["description"]
            })
            
    # Check URL patterns if present
    has_suspicious_url = False
    suspicious_url_reason = ""
    target_url = url or ""
    if not target_url:
        found_urls = re.findall(r'https?://[^\s]+', text)
        if found_urls:
            target_url = found_urls[0]
            
    if target_url:
        target_lower = target_url.lower()
        for tld in SUSPICIOUS_DOMAINS_TLD:
            if tld in target_lower:
                has_suspicious_url = True
                suspicious_url_reason = f"O link termina em '{tld}', extensão muito utilizada em páginas de golpes."
                break
        if ("gov" in target_lower or "caixa" in target_lower or "correios" in target_lower or "bb" in target_lower) and not (target_lower.endswith(".gov.br") or ".gov.br/" in target_lower or ".com.br" in target_lower):
            has_suspicious_url = True
            suspicious_url_reason = "O link tenta imitar um órgão oficial ou banco mas não possui o domínio oficial (.gov.br ou .com.br)."

    is_scam = len(matches) > 0 or has_suspicious_url
    
    return {
        "is_scam": is_scam,
        "scam_count": len(matches) + (1 if has_suspicious_url else 0),
        "detected_patterns": matches,
        "suspicious_url": has_suspicious_url,
        "suspicious_url_reason": suspicious_url_reason,
        "advice": "Nunca envie dinheiro, não faça Pix e não digite suas senhas ou CPF em links recebidos por mensagem." if is_scam else ""
    }
