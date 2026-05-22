import json
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-lite-8b"))

async def generate_final_report(content: str, context_data: dict) -> dict:
    """
    VerifAI Core - Dynamic Consolidation Engine.
    Implements the 'Antianachronism Mechanism' by injecting real-time system context.
    """
    now = datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Roadmap Strict Prompt Structure
    prompt = f"""
Você é o Perito-Chefe do VerifAI Core. Sua palavra é o veredito final.

CONTEXTO TEMPORAL CRÍTICO:
Data e Hora Atual do Sistema: {current_time_str} (Use este ponto no tempo como o presente absoluto para julgar o que é recente, histórico ou futuro).

CONTEÚDO PARA ANÁLISE:
"{content}"

DADOS DE CONTEXTO (Fact-checks e buscas):
{json.dumps(context_data, indent=2, ensure_ascii=False)}

INSTRUÇÕES DE EXECUÇÃO:
1. ORQUESTRAÇÃO: Cruze os dados de contexto com o conteúdo fornecido.
2. ANCHORING: Nunca julgue uma notícia de ontem como "antiga" se hoje é hoje. Use a data do sistema.
3. STRUCTURE: Retorne EXATAMENTE um JSON com:
   - "verdict": (Authentic | AI_Generated | Manipulated | Out_Of_Context | Suspicious)
   - "score": (0-100, onde 100 é totalmente autêntico)
   - "summary": (Resumo humanizado de 2 a 3 frases explicando o motivo do veredito)
   - "red_flags": [Lista de alertas técnicos]
   - "semantic_score": (0-100)
   - "sensationalism": (0-100)
   - "domain_score": (0-100)
   - "temporal_issues": boolean (se houver conflito de data)
   - "positives": [Sinais de autenticidade]

FOCO: Seja extremamente técnico, cético e preciso.
"""

    try:
        response = model.generate_content(prompt)
        # Extract json block
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        return json.loads(text)
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
