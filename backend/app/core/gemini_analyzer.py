import os
import json
import re
from datetime import datetime
import google.generativeai as genai

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-flash-lite-preview")
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

_TODAY = datetime.now().strftime("%d de %B de %Y")

SYSTEM_INSTRUCTION = f"""Você é o Perito-Chefe do Sistema VerifAI (Antigravity Core).
Sua missão é consolidar dados de múltiplas ferramentas forenses e gerar um veredito final humanizado.

DATA DE HOJE: {_TODAY}

Você receberá dados técnicos de:
1. Sightengine/Hive (Detecção de Deepfakes/IA em mídia)
2. Hugging Face (Double check open-source)
3. SerpApi (Busca reversa e histórico de imagem)
4. GPTZero (Detecção de IA em texto)
5. Google Fact Check (Verificações prévias de agências)

Seu Relatório Final deve ser:
- Objetivo e direto.
- Humanizado (como um jornalista investigativo).
- Formato JSON estrito conforme o esquema fornecido.
"""

_ANALYSIS_SCHEMA = """
{
  "score": <inteiro 0-100>,
  "semantic_score": <inteiro 0-100>,
  "sensationalism": <inteiro 0-100>,
  "verdict": "<CONFIÁVEL | SUSPEITO | FALSO>",
  "summary": "<relatório final humanizado em 2-3 frases>",
  "red_flags": ["<item>"],
  "positive_signals": ["<item>"],
  "logical_fallacies": ["<item>"],
  "emotional_triggers": <true | false>,
  "temporal_issues": <true | false>,
  "recommended_sources": ["<fonte>"]
}
"""

def _get_model() -> genai.GenerativeModel:
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION,
    )

def _safe_parse(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise

async def generate_final_report(content: str, context_data: dict) -> dict:
    """
    Orchestrate the final report using Gemini 3.1 Flash-Lite.
    consolidates all forensic data.
    """
    prompt = f"""
Analise o conteúdo principal e considere os dados forenses coletados pelas outras ferramentas:

CONTEÚDO ANALISADO:
"{content[:4000]}"

DADOS FORENSES (CONTEXTO):
{json.dumps(context_data, indent=2)}

Sua tarefa: Como perito chefe, analise as inconsistências. Se a busca reversa indica que a foto é antiga mas o post diz ser nova, aponte "Contexto Distorcido". Se o Sightengine indica Deepfake, aponte fraudes visuais.

Retorne APENAS o JSON no formato:
{_ANALYSIS_SCHEMA}
"""
    try:
        model = _get_model()
        response = await model.generate_content_async(prompt)
        return _safe_parse(response.text)
    except Exception as e:
        return {
            "score": 50, "verdict": "SUSPEITO",
            "summary": f"Erro na orquestração final: {str(e)[:100]}",
            "red_flags": ["Erro do Orquestrador Gemini"],
            "positive_signals": [], "logical_fallacies": [],
            "emotional_triggers": False, "temporal_issues": False,
            "recommended_sources": []
        }

async def analyze_with_gemini(text: str) -> dict:
    """Legacy support - redirected to orchestrator with empty context."""
    return await generate_final_report(text, {"source": "direct_text"})

async def analyze_media_with_gemini(media_bytes: bytes, mime_type: str) -> dict:
    """Consolidate media analysis."""
    # This will be called from upload.py pipeline
    # For now, keep it simple as a fallback
    model = _get_model()
    prompt = f"Analise esta mídia e retorne o JSON base:\n{_ANALYSIS_SCHEMA}"
    response = await model.generate_content_async([{"mime_type": mime_type, "data": media_bytes}, prompt])
    return _safe_parse(response.text)
