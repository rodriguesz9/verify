# VerifAI – Antigravity Core

> Sistema Avançado de Auditoria Digital e Combate à Desinformação.
> Stack: **FastAPI + Gemini 3.1 Flash-Lite + Sightengine + SerpApi + GPTZero + React**

---

## 🚀 Antigravity Core Architecture
O VerifAI evoluiu para o **Antigravity Core**, uma arquitetura modular que orquestra múltiplas camadas de inteligência forense para um veredito inquestionável.

### 🔬 Pipeline de Verificação 3.0
1. **Sightengine + Hive**: Detecção profunda de Deepfakes e fotos geradas por IA.
2. **Hugging Face (Open Source)**: Dupla checagem com modelos da comunidade para validação visual.
3. **SerpApi (Google Reverse Image)**: Rastreamento de origem para detectar imagens fora de contexto.
4. **GPTZero / Sapling**: Análise de perplexidade para identificar textos escritos por máquinas.
5. **Gemini 3.1 Flash-Lite (Orquestrador)**: O "Perito-Chefe" que consolida todos os dados em um laudo humanizado.

---

## 🔑 APIs Necessárias (.env)
Para rodar o sistema completo, configure as seguintes variáveis no seu `backend/.env`:

```env
# Google AI Studio
GEMINI_API_KEY="sua_chave"
GEMINI_MODEL_NAME="gemini-3.1-flash-lite-preview"

# Forense de Mídia
SIGHTENGINE_API_USER="seu_usuario"
SIGHTENGINE_API_SECRET="sua_chave"
HUGGINGFACE_API_TOKEN="seu_token"

# Contexto e Texto
SERPAPI_KEY="sua_chave"
GPTZERO_API_KEY="sua_chave"
```

---

## ⚙️ Instalação Rápida (Docker)

1. **Clone o repositório**
2. **Configure o `.env` no backend**
3. **Suba os containers:**
```bash
docker-compose up --build
```

---

## 🏗️ Estrutura do Projeto (v0.3)
- `backend/app/core/pipeline.py`: O sistema nervoso central.
- `backend/app/core/gemini_analyzer.py`: Orquestrador Gemini 3.1.
- `frontend/src/pages/Missao.jsx`: Nossa filosofia.
- `frontend/src/pages/Sugestoes.jsx`: Canal aberto para melhorias.

---

## 💡 Missão
Democratizar a análise forense digital e fornecer ferramentas de elite para que qualquer cidadão possa distinguir fatos de manipulações sintéticas.

---

## 📊 Endpoints Atualizados
- `/api/check-text`: Agora com detecção de escrita por IA via GPTZero.
- `/api/check-url`: Scraping otimizado e orquestração Gemini 3.1.
- `/api/upload`: Análise paralela (Deepfakes, IA Visibility, Vision).
