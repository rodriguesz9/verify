# 🚀 Verify — Roadmap e Especificação de Implementações Futuras

Este documento detalha o plano de evolução técnica, arquitetural e de produto do **Verify**, organizado por áreas de impacto: **Forense e Precisão de Mídia**, **Bot de WhatsApp para Mensagens Encaminhadas**, **Acessibilidade e Didática para Idosos** e **Infraestrutura e Segurança**.

---

## Índice
1. [Módulo 1: Forense Avançada de Mídia e Eliminação de Falsos-Positivos](#1-forense-avançada-de-mídia-e-eliminação-de-falsos-positivos)
2. [Módulo 2: Bot de WhatsApp para Mensagens e Mídias Encaminhadas](#2-bot-de-whatsapp-para-mensagens-e-mídias-encaminhadas)
3. [Módulo 3: Experiência do Usuário (UI/UX) para o Público Idoso](#3-experiência-do-usuário-uiux-para-o-público-idoso)
4. [Módulo 4: Detecção Especializada de Golpes Financeiros (Pix e Boletos)](#4-detecção-especializada-de-golpes-financeiros-pix-e-boletos)
5. [Módulo 5: Infraestrutura, Filas e Escalabilidade](#5-infraestrutura-filas-e-escalabilidade)
6. [Guia de Variáveis de Ambiente para Railway e Vercel](#6-guia-de-variáveis-de-ambiente-para-railway-e-vercel)

---

## 1. Forense Avançada de Mídia e Eliminação de Falsos-Positivos

### 1.1. Inspeção Multimodal Direta com Gemini Vision
- **Problema atual:** Em versões anteriores, apenas metadados ou pontuações de APIs de terceiros eram enviadas ao LLM como texto, sem que o modelo visual pudesse inspecionar os pixels diretamente.
- **O que implementar:**
  - Envio direto dos bytes da imagem (`image/jpeg`, `image/png`, `image/webp`) para o endpoint de visão multimodal do Gemini (`gemini-3.7-flash` ou `gemini-1.5-flash`).
  - *Prompt Forense Visual Especializado:* Instruir o modelo a analisar:
    - **Anatomia:** Mãos, dedos, reflexos nas pupilas, dentes, lóbulos de orelha e continuidade de fios de cabelo.
    - **Consistência Física:** Direção de sombras versus pontos de luz, reflexos em superfícies espelhadas/vidros/água e perspectiva geométrica.
    - **Diferenciação de Compressão vs. Difusão:** Discriminar artefatos normais de compressão JPEG de WhatsApp de ruído característico de difusão (*waxy skin*, suavização excessiva de pele).
    - **Detecção de Edição Tradicional:** Reconhecer que ajustes de curvas, saturação, corte e filtros de Instagram/Photoshop são edições convencionais e **não** geração de imagem sintética.

### 1.2. Prova de Existência Histórica (Análise Temporal Reversa)
- **Objetivo:** Se uma imagem já existia na internet em 2015, 2019 ou 2021, é matematicamente impossível que tenha sido criada por modelos generativos recentes (Midjourney v5/v6, DALL-E 3, Flux).
- **O que implementar:**
  - Integração contínua com **SerpApi (Google Lens Reversa)** e **Wayback Machine API**.
  - Regra de corte categórico: Se a primeira data de indexação for anterior a 2022, a probabilidade de IA generativa é travada em 0%, emitindo o veredito "Foto Histórica Autêntica" (ou "Fora de Contexto", caso esteja sendo usada com narrativa mentirosa recente).

### 1.3. Detecção de Deepfake em Vídeos
- **O que implementar:**
  - Extração de frames-chave usando `ffmpeg` (ex: 2 a 3 quadros por segundo).
  - Verificação de inconsistências temporais de piscar de olhos (*eye blinking rate*).
  - Análise de sincronia labial (*viseme-phoneme synchronization*) para identificar substituição de áudio em discursos públicos.

---

## 2. Bot de WhatsApp para Mensagens e Mídias Encaminhadas

O WhatsApp é o ecossistema primário onde o público leigo e idosos recebem desinformação. O bot funcionará como um "tira-dúvidas" direto.

### 2.1. Arquitetura de Conexão (Evolution API / Meta Cloud API)
- **Opção A (Recomendada para Início e Testes): Evolution API**
  - Servidor open-source self-hosted em Docker conectado via biblioteca Baileys com pareamento por QR Code.
  - Vantagens: Suporta números normais ou comerciais, captura áudios em formato nativo Opus e entrega webhooks instantâneos no backend do Verify.
- **Opção B (Recomendada para Escala Corporativa): Meta WhatsApp Cloud API**
  - Integração oficial via Graph API da Meta.
  - Vantagens: Confiabilidade de 99.9%, selo de verificação oficial da empresa e sem risco de banimento de número.

### 2.2. Fluxo de Tratamento das Mensagens Encaminhadas

```
1. RECEPÇÃO NO WHATSAPP
   ├── Usuário encaminha mensagem com tag "Encaminhada" ou "Encaminhada com frequência"
   └── Bot detecta o tipo: Texto, Link, Áudio (Voice Note) ou Imagem

2. FEEDBACK INSTANTÂNEO (< 2 segundos)
   └── "🔍 Recebi sua mensagem! Estou checando em jornais, bancos de dados oficiais e checadores... Aguarde um instante."

3. PIPELINE DE AUDITORIA
   ├── Se Áudio: Converte Opus -> Gemini Multimodal Audio -> Extrai fala -> Detecta padrão de extorsão/urgência
   ├── Se Foto/Print: OCR + Gemini Vision + Metadados -> Verifica adulteração de valores/chaves Pix
   └── Se Link/Texto: Antiphishing -> Fact Check Tools API -> Notícias em tempo real no Serper

4. RESPOSTA MULTIMODAL AMIGÁVEL
   ├── Texto com emojis e marcadores visuais nativos (*negrito*, badges de cores)
   ├── Áudio de voz sintetizado anexado (15 segundos) explicando o veredito para o idoso
   └── Botão de 1 toque: "Repassar aviso no grupo da família"
```

### 2.3. Modo "Guardião da Família" (Bot em Grupos)
- Possibilidade de adicionar o Verify em grupos familiares do WhatsApp.
- O bot permanece em silêncio e só atua quando alguém encaminha uma notícia e digita `@verify` ou quando detecta um link cadastrado em listas globais de golpes de Pix/phishing.

---

## 3. Experiência do Usuário (UI/UX) para o Público Idoso

### 3.1. Chave Seletora "Modo Fácil / Terceira Idade"
- Um botão de fácil visualização no topo de todas as páginas: `[ 👵 Modo Fácil (Letras Maiores) ]`.
- Ao ativar:
  - Tamanho de fonte base aumentado para 20px com alto contraste.
  - Ocultação de todas as métricas técnicas (eliminando termos como *SHA-256*, *Perplexity*, *C2PA JUMBF*).
  - Destaque exclusivo para a **Metáfora do Farol**:
    - 🟢 **VERDE:** *Seguro! Essa notícia é verdadeira e confirmada.*
    - 🔴 **VERMELHO:** *GOLPE / FALSO! Não pague, não faça Pix e não clique no link.*
    - 🟡 **AMARELO:** *SUSPEITO! Não encontramos provas em jornais confiáveis. Não passe adiante.*

### 3.2. Leitura Falada Universal (Assistente de Voz)
- Em qualquer tela de resultado, um botão grande em destaque: `[ 🔊 Ouvir Explicação em Voz Alta ]`.
- Voz serena em português do Brasil com velocidade ajustada (0.92x) e pausas claras, sintetizando a explicação de forma humana e acolhedora.

### 3.3. Gerador de Mensagem Pacificadora para a Família
- Quando uma notícia falsa é detectada, o idoso frequentemente tem vergonha de avisar a quem enviou.
- O Verify gera uma mensagem pronta com tom respeitoso e afetuoso para copiar com 1 toque:
  > *"Oi família! Passei essa mensagem no checador Verify e descobri que ela é falsa/golpe. O banco e o governo alertaram que não é verdade. Não cliquem e não façam Pix, tá bom? Amo vocês e quero ver todo mundo protegido! ❤️"*

---

## 4. Detecção Especializada de Golpes Financeiros (Pix e Boletos)

### 4.1. Verificador de Falsos Comprovantes de Pix
- Golpistas enviam comprovantes de Pix agendado ou falsificados com fontes adulteradas para comércios e idosos simulando pagamentos.
- **Implementação:**
  - Extração via OCR dos dados do comprovante: ID da transação, banco emissor, valor e data.
  - Verificação visual de alinhamento de texto (em comprovantes falsos, a fonte do valor costuma ser diferente do restante do documento).
  - Alerta imediato se o comprovante estiver na verdade com status **"AGENDADO"** (e não "LIQUIDADO/TRANSFERIDO").

### 4.2. Checador de Boletos Falsos (Linha Digitável)
- Análise da linha digitável de 47 ou 48 dígitos de boletos bancários.
- Validação do dígito verificador e conferência do código de compensação bancária (os 3 primeiros dígitos) contra o CNPJ da empresa real beneficiária.

---

## 5. Infraestrutura, Filas e Escalabilidade

| Componente | Situação Atual | Evolução Futura |
| --- | --- | --- |
| **Fila de Tarefas** | Tarefas assíncronas em memória (`asyncio`) | Fila persistente com **Redis + ARQ ou Celery** para processar áudios e vídeos em segundo plano sem perda de requisição |
| **Cache de Consultas** | Banco PostgreSQL com hash MD5 e TTL de 7 dias | Cache em memória ultrarrápido com **Redis**, respondendo a boatos virais idênticos em menos de 10ms |
| **Modelos Locais de Contingência** | APIs externas de terceiros | Container opcional com **Whisper Small** e **Florence-2** para transcrição e visão sem custo de tokens |
| **Métricas de Desinformação** | Histórico simples de usuário | Painel com mapa de calor dos golpes mais frequentes da semana no Brasil |

---

## 6. Guia de Variáveis de Ambiente para Railway e Vercel

Abaixo estão todas as variáveis de ambiente necessárias para o funcionamento correto nos ambientes de nuvem.

### 6.1. Variáveis para a API e Banco (Railway)

Configure estas variáveis nas configurações de **Variables** do serviço da API no Railway:

```dotenv
# ── Banco de Dados (Gerenciado pelo Railway) ──────────────────────────────────
DATABASE_URL=${{Postgres.DATABASE_URL}}

# ── Autenticação e Criptografia (Gere chaves longas de 32 bytes hex) ──────────
JWT_SECRET=sua_chave_jwt_secreta_longa_aqui
HMAC_SECRET_KEY=sua_chave_hmac_para_selos_aqui
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Cookies e Domínio (Atenção para comunicação Vercel <-> Railway) ────────────
COOKIE_SECURE=true
COOKIE_SAME_SITE=none
CORS_ORIGINS=https://seu-projeto-verify.vercel.app
CORS_ORIGIN_REGEX=https://.*\.vercel\.app

# ── Orquestração com Google Gemini (Google AI Studio) ─────────────────────────
GEMINI_API_KEY=sua_chave_do_google_ai_studio_aqui
GEMINI_MODEL_NAME=gemini-3.7-flash

# ── Checagem de Fatos e Notícias em Tempo Real ────────────────────────────────
GOOGLE_FACT_CHECK_KEY=sua_chave_da_google_fact_check_tools_aqui
SERPERAPI_KEY=sua_chave_do_serper_dev_aqui
SERPAPI_KEY=sua_chave_do_serpapi_aqui

# ── Análise Forense de Mídia (Opcionais para funcionalidades completas) ───────
SIGHTENGINE_API_USER=seu_usuario_sightengine
SIGHTENGINE_API_SECRET=seu_segredo_sightengine
HUGGINGFACE_API_TOKEN=seu_token_huggingface_aqui
HIVE_API_KEY=sua_chave_da_thehive_ai_aqui
ASSEMBLYAI_API_KEY=sua_chave_da_assemblyai_aqui

# ── Configurações do Bot de WhatsApp (Quando ativar a Evolution API) ──────────
WHATSAPP_BOT_ENABLED=true
EVOLUTION_API_URL=https://sua-evolution-api.railway.app
EVOLUTION_API_KEY=chave_da_instancia_evolution
```

### 6.2. Variáveis para o Frontend (Vercel)

Configure estas variáveis nas configurações de **Environment Variables** do projeto no Vercel (para ambientes de Production e Preview):

```dotenv
# URL pública da sua API no Railway (SEM barra no final)
VITE_API_URL=https://verify-production.up.railway.app

# Opcional: Login Google com botão One Tap
VITE_GOOGLE_CLIENT_ID=seu_client_id.apps.googleusercontent.com
```

> [!IMPORTANT]
> **Atenção sobre Cookies de Terceiros:**
> Enquanto estiver usando o domínio padrão `*.vercel.app` e `*.up.railway.app`, `COOKIE_SAME_SITE` deve ser `none` e `COOKIE_SECURE` deve ser `true`. Se você registrar um domínio próprio (ex: `app.verify.com.br` e `api.verify.com.br`), mude `COOKIE_SAME_SITE` para `lax` para máxima compatibilidade com Safari e navegadores modernos.
