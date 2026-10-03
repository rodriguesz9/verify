import re
from urllib.parse import urlsplit
from typing import Dict, Any, List

SCAM_PATTERNS = [
    {
        "category": "Golpe do Pix / Dinheiro Fácil",
        "regex": r"(pix.*aprovado|pague\s+(uma\s+)?taxa|taxa.*(liberar|receber|resgatar)|devolu[cç][aã]o\s+do\s+pix|resgate\s+(de\s+)?valores|valores\s+esquecidos?.*pix|saldo\s+esquecido|pix\s+em\s+dobro|multiplicador\s+de\s+pix|taxa\s+para\s+liberar\s+saldo|taxa\s+de\s+r\$\s*\d+.*liberar|chave\s+pix.*ganhe)",
        "risk_level": "ALTO",
        "description": "Pedido de taxa ou promessa de liberar um suposto saldo. O pagamento antecipado pode causar perda de dinheiro; confirme o procedimento no canal oficial antes de pagar."
    },
    {
        "category": "Falsa Taxa dos Correios / Alfândega",
        "regex": r"(correios.*encomenda.*retida|correios.*objeto|taxa\s+alfandeg[aá]ria|objeto\s+aguardando\s+pagamento|alfandega.*taxa|libera[cç][aã]o\s+de\s+pacote|sua\s+encomenda\s+est[aá]\s+presa)",
        "risk_level": "ALTO",
        "description": "Mensagem relacionando uma encomenda a uma cobrança. Taxas legítimas podem existir, portanto confira o rastreamento e o pagamento no site oficial; a mensagem isolada não comprova fraude."
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
        "description": "Troca de número ou pedido financeiro atribuído a um parente. O texto não comprova a identidade do remetente; confirme pelo número antigo antes de transferir dinheiro."
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
PATTERN_GUIDANCE = {
    "Golpe do Pix / Dinheiro Fácil": [
        {"title": "Banco Central · orientação sobre golpes e Valores a Receber",
         "url": "https://www.bcb.gov.br/meubc/faqs/p/golpes-envolvendo-o-meu-bc",
         "reviewed_at": "2026-10-02"},
    ],
    "Falsa Taxa dos Correios / Alfândega": [
        {"title": "Correios · segurança e mensagens falsas",
         "url": "https://www.correios.com.br/falecomoscorreios/seguranca",
         "reviewed_at": "2026-10-02"},
    ],
}

def is_negated_request(text: str, start: int) -> bool:
    # Narrow local safeguard, not semantic understanding of sarcasm/quotations.
    prefix = text[max(0, start - 65):start]
    return bool(re.search(r"(?:\bn[aã]o|\bnunca|\bjamais|\bevite)\s+(?:\w+\s+){0,3}$", prefix, re.IGNORECASE))


def analyze_scam_indicators(text: str, url: str | None = None) -> Dict[str, Any]:
    """
    Scans text and URLs for common Brazilian scams, phishing attempts,
    and elderly-targeted fraud patterns.
    """
    matches: List[Dict[str, str]] = []
    
    # Check text patterns
    for pattern in SCAM_PATTERNS:
        match = next((m for m in re.finditer(pattern["regex"], text, re.IGNORECASE)
                      if not is_negated_request(text, m.start())), None)
        if match:
            matches.append({
                "category": pattern["category"],
                "risk_level": pattern["risk_level"],
                "description": pattern["description"],
                "matched_excerpt": match.group(0)[:300],
                "guidance": PATTERN_GUIDANCE.get(pattern["category"], []),
            })
            
    # Check URL patterns if present
    has_suspicious_url = False
    suspicious_url_reason = ""
    target_url = url or ""
    if not target_url:
        found_urls = re.findall(r'https?://[^\s]+', text)
        if found_urls:
            target_url = found_urls[0]
            
    impersonates_institution = False
    if target_url:
        try:
            hostname = (urlsplit(target_url).hostname or "").lower().rstrip(".")
        except ValueError:
            hostname = ""
        for tld in SUSPICIOUS_DOMAINS_TLD:
            if hostname.endswith(tld):
                has_suspicious_url = True
                suspicious_url_reason = f"O domínio termina em '{tld}'. A extensão isolada é um sinal fraco e não comprova golpe ou falsidade."
                break
        official_domains = {
            "gov": ("gov.br",), "caixa": ("caixa.gov.br",),
            "correios": ("correios.com.br",), "bb": ("bb.com.br",),
        }
        for entity, domains in official_domains.items():
            if re.search(r"(?:^|[.-])" + entity + r"(?:[.-]|$)", hostname):
                if not any(hostname == domain or hostname.endswith("." + domain) for domain in domains):
                    has_suspicious_url = impersonates_institution = True
                    suspicious_url_reason = f"O domínio usa o nome '{entity}', mas não corresponde aos domínios oficiais configurados para essa instituição. Confirme pelo canal oficial."
                    break

    # An unfamiliar suffix alone must not turn a legitimate site into a scam.
    is_scam = len(matches) > 0 or impersonates_institution
    
    return {
        "is_scam": is_scam,
        "scam_count": len(matches) + (1 if impersonates_institution else 0),
        "detected_patterns": matches,
        "suspicious_url": has_suspicious_url,
        "suspicious_url_reason": suspicious_url_reason,
        "advice": "Nunca envie dinheiro, não faça Pix e não digite suas senhas ou CPF em links recebidos por mensagem." if is_scam else ""
    }
