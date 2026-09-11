# Verify 🛡️

> Sistema Inteligente e Acessível de Checagem de Fatos, Proteção contra Golpes no WhatsApp e Auditoria Digital.
> **Focado em Idosos, Famílias e Usuários Leigos.**

---

## 🌟 O que há de novo no Verify?

1. **Interface Ultra-Simples e Acessível:**
   - Textos claros, botões grandes e linguagem acolhedora sem termos difíceis.
   - Botão **"Ouvir Explicação" (Voz em Português)** para idosos ouvirem o veredito sem precisar ler telas longas.
   - Botão **"Avisar a Família no WhatsApp"** que já prepara a mensagem explicativa com emojis com 1 clique.
   - Controle de tamanho de texto (**A- / A+ / Padrão / Grande / Muito Grande**).
   - Abas dedicadas para: **Texto da Mensagem**, **Link de Site**, **Foto/Imagem** e **Áudio do WhatsApp**.

2. **Detector de Golpes e Fraudes Brasileiras:**
   - Detecção especializada de falsos resgates de Pix, falsas taxas dos Correios, golpes do parente com número novo, falsas promoções e páginas falsas de auxílios e INSS.

3. **Suporte a Áudios de WhatsApp (.ogg / .mp3 / .m4a):**
   - Transcrição e checagem de fatos automática de áudios encaminhados usando IA Multimodal.

4. **Bot do WhatsApp:**
   - Webhook pronto para integrar com serviços de WhatsApp (Evolution API, Baileys, Z-API, Meta Cloud API) e responder diretamente no aplicativo com laudos formatados.

---

## 🚀 Como Rodar o Projeto Localmente

### Pré-requisitos
- Python 3.10+
- Node.js 18+ (ou Docker)

### 1. Backend (FastAPI)

```bash
cd backend

# Crie o ambiente virtual (opcional mas recomendado)
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis no arquivo .env
cp .env.example .env
# Adicione sua chave GEMINI_API_KEY no .env

# Inicie o backend
uvicorn app.main:app --reload --port 8000
```
O backend rodará em `http://localhost:8000` (com documentação interativa em `http://localhost:8000/docs`).

---

### 2. Frontend (React + Vite + Tailwind)

```bash
cd frontend

# Instale as dependências
npm install

# Inicie o frontend
npm run dev
```
O frontend abrirá em `http://localhost:5173`.

---

## 🤖 Como Funciona o Bot do WhatsApp

O Verify possui endpoints dedicados para integração com WhatsApp:
- `POST /api/whatsapp/webhook`: Recebe mensagens de instâncias do WhatsApp e devolve a resposta formatada.
- `POST /api/whatsapp/simulate`: Permite simular o envio e receber a resposta do WhatsApp formatada.

### Formato de Resposta do Bot:
```text
━━━━━━━━━━━━━━━━━━
🔍 *VERIFY - Checagem de Fatos*
━━━━━━━━━━━━━━━━━━

📊 *Veredito:* ❌ *CONTEÚDO FALSO / GOLPE*
📈 *Risco: ALTO*

📝 *O QUE VOCÊ PRECISA SABER:*
Essa mensagem sobre resgate de dinheiro do Pix é falsa. O Banco Central não cobra taxas para devolver valores.

💡 *DICA DE SEGURANÇA:*
Nunca clique em links nem envie Pix para promessas de dinheiro fácil.

━━━━━━━━━━━━━━━━━━
🛡️ *Dica:* Antes de repassar qualquer notícia, verifique sempre no *Verify*.
🌐 *Acesse:* https://verify.vercel.app
```

---

## ☁️ Como Fazer o Deploy Online

### 1. Frontend na Vercel (1-Click Deploy)
1. Conecte seu repositório no [Vercel](https://vercel.com).
2. Defina o diretório raiz como `frontend`.
3. Adicione a variável de ambiente:
   - `VITE_API_URL`: URL do seu backend hospedado (ex: `https://verify-api.onrender.com`).
4. O arquivo `frontend/vercel.json` já está configurado para gerenciar as rotas SPA!

### 2. Backend no Render / Railway / Fly.io / Koyeb
1. Conecte o repositório e aponte para a pasta `backend`.
2. O arquivo `backend/render.yaml` e `backend/Procfile` já contêm os comandos de build e start.
3. Configure as variáveis de ambiente:
   - `GEMINI_API_KEY`: Sua chave gratuita do Google AI Studio.
   - `GEMINI_MODEL_NAME`: `gemini-1.5-flash`
   - `DATABASE_URL`: URL do seu banco PostgreSQL (ou deixe vazio para SQLite local).
   - `CORS_ORIGINS`: `*` ou a URL do seu domínio na Vercel.

---

## 📄 Licença e Créditos
Desenvolvido com o compromisso de combater a desinformação e proteger cidadãos na era digital.
