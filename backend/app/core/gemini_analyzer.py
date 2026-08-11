import asyncio
import json
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-lite-8b"))


async def extract_claims_with_ai(content: str) -> list[str]:
    """
    Extract factual claims from text using Gemini.
    Returns a plain list of short, searchable claims.
    """
    prompt = f"""
Você é um extrator de claims para um sistema de fact-checking.

TAREFA:
Extraia apenas as alegações factuais verificáveis do texto.

REGRAS:
- Retorne somente um JSON array de strings.
- Não retorne markdown.
- Não explique.
- Separe alegações independentes em itens diferentes.
- Preserve entidades, locais e relações importantes.
- Ignore opiniões, xingamentos, perguntas, chamadas e trechos sem afirmação factual.
- Se não houver claims verificáveis, retorne [].

EXEMPLOS:
Texto: "Prefeitura de BH decretou lockdown hoje"
Resposta: ["A prefeitura de BH decretou lockdown"]

Texto: "vacina causa infertilidade e governo esconde dados"
Resposta: ["vacina causa infertilidade", "governo esconde dados"]

TEXTO:
"{content}"
"""

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        response_text = _extract_json_text(response.text)
        claims = json.loads(response_text)
    except Exception as e:
        print(f"Error extracting claims with Gemini: {e}")
        return []

    extracted_claims = _clean_claims(claims)
    if not extracted_claims:
        return []

    return await decontextualize_claims(content, extracted_claims)


async def decontextualize_claims(original_text: str, claims: list[str]) -> list[str]:
    """
    Rewrite extracted claims into standalone, searchable claims using the source text.
    """
    clean_input_claims = _clean_claims(claims)
    if not clean_input_claims:
        return []

    prompt = f"""
Você é um normalizador de claims para busca em sistemas de fact-checking.

TAREFA:
Reescreva cada claim para que ela fique independente do texto original e adequada para busca.

REGRAS:
- Retorne somente um JSON array de strings.
- Não retorne markdown.
- Não explique.
- Preserve o sentido factual original.
- Use o texto original para resolver pronomes, sujeitos implícitos, locais e entidades.
- Remova marcadores temporais vagos quando não forem essenciais, como "hoje", "agora" ou "nesta semana".
- Não invente dados que não estejam no texto original.
- Mantenha a mesma quantidade de claims, exceto para remover duplicatas ou claims inválidas.
- Se nenhuma claim for válida, retorne [].

TEXTO ORIGINAL:
{json.dumps(original_text, ensure_ascii=False)}

CLAIMS:
{json.dumps(clean_input_claims, ensure_ascii=False)}
"""

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        response_text = _extract_json_text(response.text)
        decontextualized_claims = json.loads(response_text)
    except Exception as e:
        print(f"Error decontextualizing claims with Gemini: {e}")
        return clean_input_claims

    clean_output_claims = _clean_claims(decontextualized_claims)
    return clean_output_claims or clean_input_claims


def _clean_claims(claims: object) -> list[str]:
    if not isinstance(claims, list):
        return []

    clean_claims: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        if not isinstance(claim, str):
            continue

        clean_claim = claim.strip()
        if not clean_claim:
            continue

        key = clean_claim.casefold()
        if key in seen:
            continue

        seen.add(key)
        clean_claims.append(clean_claim)

    return clean_claims


def _extract_json_text(text: str) -> str:
    text = text.strip()
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text


async def generate_final_report(content: str, context_data: dict) -> dict:
    """
    VerifAI Core - Dynamic Consolidation Engine.
    Implements the 'Antianachronism Mechanism' by injecting real-time system context.
    """
    now = datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Roadmap Strict Prompt Structure
    prompt = f"""
Você é o VerifAI Core, um sistema auxiliar de análise de confiabilidade de notícias.

Você NÃO deve afirmar certeza absoluta.
Você deve basear sua análise apenas no conteúdo fornecido e nos dados de contexto.
Quando as evidências forem insuficientes, use "Suspicious" ou indique baixa confiança.

CONTEXTO TEMPORAL CRÍTICO:
Data e Hora Atual do Sistema: {current_time_str} (Use este ponto no tempo como o presente absoluto para julgar o que é recente, histórico ou futuro).

CONTEÚDO PARA ANÁLISE:
"{content}"

DADOS DE CONTEXTO (Fact-checks e buscas):
{json.dumps(context_data, indent=2, ensure_ascii=False)}

INSTRUÇÕES DE EXECUÇÃO:
1. ORQUESTRAÇÃO: Cruze os dados de contexto com o conteúdo fornecido.
2. ANCHORING: Nunca julgue uma notícia de ontem como "antiga" se hoje é hoje. Use a data do sistema.
3. ETAPAS DE ANALISE:
- Extrair alegações principais
- Comparar com context_data
- Avaliar fonte/domínio
- Avaliar linguagem sensacionalista
- Avaliar problemas temporais
- Avaliar sinais de manipulação/IA, se houver imagem
4. FACT-CHECKING (OBRIGATÓRIO quando context_data.fact_checks não estiver vazio):
- Para cada alegação principal, compare com os itens de context_data.fact_checks (claim_text, rating, publisher, url).
- Alegação que contradiz um fact-check de fonte confiável: reduza o "score", reforce o "verdict" para Suspicious/Out_Of_Context e adicione alerta em "red_flags" citando o publisher e a avaliação.
- Alegação corroborada por fact-check: adicione o item em "fact_check_evidence" e registre sinal positivo em "positives".
- SEMPRE reflita os resultados dos fact-checks na "summary", citando publisher e avaliação (ex.: "Boatos.org avalia a alegação como Falso").
- Se nenhum fact-check corresponde, NÃO invente: apenas informe que não houve correspondência.
5. BUSCA DE NOTÍCIAS (OBRIGATÓRIO quando context_data.serper_news não estiver vazio):
- Compare cada alegação principal com context_data.serper_news (title, link, snippet, date de veículos de imprensa).
- Alegação confirmada por MÚLTIPLAS fontes de imprensa confiáveis: aumente o "score", registre sinal positivo em "positives" e cite os veículos na "summary".
- Fontes conflitantes ou apenas veículos de baixa credibilidade: reforce o "verdict" para Suspicious e adicione alerta em "red_flags".
- Nenhuma notícia relevante encontrada: NÃO invente cobertura; apenas informe na "summary" que não há cobertura de imprensa indexada.
- Adicione em "serper_news_evidence" os itens usados (title, link, snippet, date).
6. STRUCTURE: Retorne EXATAMENTE um JSON com:
   - "verdict": (Authentic | AI_Generated | Manipulated | Out_Of_Context | Suspicious)
   - "score": (0-100, onde 100 é totalmente autêntico)
   - "summary": (Resumo humanizado de 2 a 3 frases explicando o motivo do veredito, citando fact-checks e/ou veículos de imprensa relevantes quando existirem)
   - "red_flags": [Lista de alertas técnicos]
   - "fact_check_evidence": [Lista de fact-checks efetivamente usados na análise, cada um com claim_text, rating, publisher e url]
   - "serper_news_evidence": [Lista de notícias efetivamente usadas na análise, cada uma com title, link, snippet e date]
   - "semantic_score": (0-100)
   - "sensationalism": (0-100)
   - "domain_score": (0-100)
   - "temporal_issues": boolean (se houver conflito de data)
   - "positives": [Sinais de autenticidade]

FOCO: Seja extremamente técnico, cético e preciso. Se um fact-check ou a cobertura de imprensa contradisser o conteúdo, o score e o veredito DEVEM refletir isso. Corroboração de imprensa confiável não é garantia absoluta de verdade, mas eleva a confiança.
"""

    try:
        response = model.generate_content(prompt)
        return json.loads(_extract_json_text(response.text))
    except Exception as e:
        print(f"Error in Gemini Analyzer: {e}")
        return {
            "verdict": "Suspicious",
            "score": 50,
            "summary": "Erro no motor de análise. Veredito inconclusivo.",
            "red_flags": ["Falha na orquestração de IA"],
            "semantic_score": 50,
            "sensationalism": 50,
            "domain_score": 50,
            "temporal_issues": False,
            "positives": []
        }
