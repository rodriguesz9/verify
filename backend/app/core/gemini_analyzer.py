import asyncio
import json
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

MODEL_ROTATION = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-lite",
]

class GeminiModelRotator:
    _index = 0
    _lock = asyncio.Lock()

    @classmethod
    async def get_model(cls) -> genai.GenerativeModel:
        async with cls._lock:
            model_name = MODEL_ROTATION[cls._index % len(MODEL_ROTATION)]
            cls._index = (cls._index + 1) % len(MODEL_ROTATION)
            return genai.GenerativeModel(model_name)

    @classmethod
    def get_current_model_name(cls) -> str:
        return MODEL_ROTATION[cls._index % len(MODEL_ROTATION)]


async def _generate_with_rotation(prompt: str, system_instruction: str = None, temperature: float = 0.1) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return '{"error": "GEMINI_API_KEY não configurada"}'

    genai.configure(api_key=api_key)
    
    try:
        model = await GeminiModelRotator.get_model()
        if system_instruction:
            model = genai.GenerativeModel(
                model_name=model._model_name,
                system_instruction=system_instruction
            )
        
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json"
            )
        )
        return response.text
    except Exception as e:
        print(f"Error generating with rotation: {e}")
        raise


async def extract_claims_with_ai(content: str) -> list[str]:
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
        response_text = await _generate_with_rotation(prompt)
        claims = json.loads(_extract_json_text(response_text))
    except Exception as e:
        print(f"Error extracting claims with Gemini: {e}")
        return []

    extracted_claims = _clean_claims(claims)
    if not extracted_claims:
        return []

    return await decontextualize_claims(content, extracted_claims)


async def decontextualize_claims(original_text: str, claims: list[str]) -> list[str]:
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
        response_text = await _generate_with_rotation(prompt)
        decontextualized_claims = json.loads(_extract_json_text(response_text))
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
    now = datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    prompt = f"""
Você é o Verify, um assistente inteligente e atencioso de checagem de fatos e proteção contra notícias falsas e golpes no WhatsApp e na internet.
O seu público principal inclui pessoas idosas, famílias e pessoas leigas em tecnologia, por isso sua linguagem deve ser muito clara, educada, acolhedora, sem jargões complicados.

CONTEXTO TEMPORAL:
Data e Hora Atual do Sistema: {current_time_str}

CONTEÚDO PARA ANÁLISE:
"{content}"

DADOS DE CONTEXTO (Fact-checks, buscas e detecção de golpes):
{json.dumps(context_data, indent=2, ensure_ascii=False)}

INSTRUÇÕES:
1. Avalie cuidadosamente se o conteúdo é:
   - "Authentic" (Verdadeiro / Notícia real confirmada)
   - "AI_Generated" (Criado por Inteligência Artificial / Foto ou texto sintético)
   - "Manipulated" (Manipulado / Editado com intenção de enganar)
   - "Out_Of_Context" (Fora de Contexto / Notícia antiga ou vídeo real usado com história falsa)
   - "Suspicious" (Boato Falso / Suspeito / Sem confirmação em fontes sérias)
   - "Scam" (Golpe / Fraude / Tentativa de roubo de dados, dinheiro ou Pix)

2. Responda EXATAMENTE um JSON com as seguintes chaves:
{{
  "verdict": "Authentic" | "AI_Generated" | "Manipulated" | "Out_Of_Context" | "Suspicious" | "Scam",
  "score": 0 a 100 (onde 100 é autêntico e 0 é falso/golpe),
  "summary": "Resumo simples e direto de 2 a 3 frases explicando de forma clara e amigável o que é essa mensagem e qual o veredito.",
  "plain_explanation": "Explicação detalhada em linguagem fácil para qualquer pessoa entender o motivo do veredito sem palavras difíceis.",
  "elderly_tip": "Uma dica curta de segurança prática para idosos (Ex: 'Nunca clique em links para receber presentes ou cadastros de auxílio no WhatsApp').",
  "whatsapp_share_text": "Texto amigável formatado com emojis (usando *negrito* do WhatsApp) pronto para o usuário copiar e mandar no grupo da família explicando por que essa mensagem é falsa ou verdadeira com carinho e educação.",
  "red_flags": ["Alertas em linguagem simples"],
  "positives": ["Sinais positivos encontrados"],
  "fact_check_evidence": [lista de fact-checks usados],
  "serper_news_evidence": [lista de notícias usadas],
  "semantic_score": 0 a 100,
  "sensationalism": 0 a 100,
  "domain_score": 0 a 100,
  "temporal_issues": false
}}
Retorne APENAS o JSON, sem markdown e sem textos adicionais.
"""

    try:
        response_text = await _generate_with_rotation(prompt, temperature=0.2)
        result = json.loads(_extract_json_text(response_text))
        result["model_used"] = GeminiModelRotator.get_current_model_name()
        return result
    except Exception as e:
        print(f"Error in Gemini Analyzer: {e}")
        return {
            "verdict": "Suspicious",
            "score": 50,
            "summary": "Não foi possível confirmar as informações com certeza no momento. Desconfie e não repasse sem antes verificar.",
            "plain_explanation": "Analisamos a mensagem, mas não encontramos provas confiáveis de que ela seja verdadeira. Recomendamos cautela.",
            "elderly_tip": "Quando receber uma notícia alarmante ou com promessas de dinheiro fácil, não repasse para seus contatos.",
            "whatsapp_share_text": "⚠️ *Atenção, família e amigos!* Pesquisei essa mensagem no *Verify* e ela não tem confirmação em fontes oficiais. Vamos ter cuidado antes de compartilhar!",
            "red_flags": ["Informação sem confirmação em veículos oficiais"],
            "semantic_score": 50,
            "sensationalism": 50,
            "domain_score": 50,
            "temporal_issues": False,
            "positives": [],
            "model_used": "fallback"
        }