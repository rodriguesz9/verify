# Verify — Plataforma Inteligente de Checagem de Fatos e Proteção contra Golpes

> Checagem acessível de mensagens, links, imagens e áudios para ajudar famílias e idosos a reconhecerem notícias falsas, fraudes digitais e clonagem de voz antes de repassar.

O **Verify** combina inteligência artificial multimodal (Google Gemini), cruzamento com agências oficiais de checagem, inspeção forense de imagens (metadados EXIF/C2PA), análise acústica de voz sintética e verificação de reputação de links. O objetivo central é fornecer apoio à decisão rápido, acolhedor e com linguagem clara para que qualquer pessoa leiga consiga se proteger.

---

## Sumário Executivo das Melhorias e Diagnósticos

### 1. Diagnóstico e Execução Completa dos Testes
- **Status dos testes:** **26 testes executados e 100% aprovados** (com 2 testes de banco real opcionalmente ignorados na ausência de `TEST_DATABASE_URL`).
- **Problemas resolvidos durante a auditoria:**
  1. *Dependência opcional de áudio quebrada:* O módulo `audio_checker.py` importava `numpy` e `librosa` no nível do arquivo, impedindo que o backend e os testes iniciassem em contêineres que não possuíam essas bibliotecas pesadas de compilação C++. O carregamento foi tornado estritamente preguiçoso (*lazy import*) com salvaguarda sem quebra de execução.
  2. *Incompatibilidade de teste de autenticação:* O teste de renovação de cookie JWT validava estaticamente `SameSite=lax`, enquanto o ambiente de produção configurado utilizava `COOKIE_SAME_SITE=none`. O teste foi flexibilizado para validar dinamicamente a configuração do ambiente.
  3. *Incompatibilidade na simulação do WhatsApp:* O frontend buscava `whatsapp_response`, enquanto o backend retornava `whatsapp_reply`. O endpoint agora fornece compatibilidade bidirecional com ambos os campos.
  4. *Criação de novos testes:* Adicionado arquivo `test_image_and_whatsapp.py` cobrindo a não detecção falsa do Photoshop como IA, detecção correta do Midjourney, formatação de respostas para WhatsApp e payloads vazios do webhook.

### 2. Solução Definitiva para Falsos-Positivos em Imagens Verdadeiras
- **Causa raiz diagnosticada:**
  - Softwares padrão de mercado como **Adobe Photoshop** e **GIMP** estavam cadastrados na lista `AI_SOFTWARE_SIGNATURES` do módulo de metadados. Qualquer fotógrafo, jornalista ou usuário que tratasse, cortasse ou redimensionasse uma foto genuína acionava o alerta `is_suspicious = True`.
  - No C2PA, uma busca simples por substring `b"generative"` em bytes binários causava falsos-positivos em perfis de cores ou licenças embutidas.
  - Detectores pontuais (como Sightengine com nota `> 0.6` ou o modelo `umm-maybe/AI-image-detector` do Hugging Face) são excessivamente sensíveis a ruídos de compressão JPEG (típicos de fotos enviadas pelo WhatsApp) e a fotos de celular com HDR/suavização de pele.
  - O backend não submetia os bytes da imagem à visão multimodal do Gemini, confiando apenas nas notas numéricas de detectores externos.
- **Implementações realizadas:**
  - Criação da lista `CONVENTIONAL_EDITING_SIGNATURES` separada da lista de geradores generativos (`AI_SOFTWARE_SIGNATURES`). Edição convencional agora gera apenas a etiqueta de imagem tratada, sem classificar como suspeita.
  - Adoção de **consenso multi-camadas**: para declarar uma imagem como gerada por IA na ausência de assinatura explícita no arquivo, é exigida concordância de múltiplos modelos ou nota extrema (> 0.85).
  - Atualização do prompt forense do Gemini para orientar explicitamente o modelo sobre artefatos de compressão de redes sociais e pós-processamento de smartphones.

### 3. Vozes e Áudios Reais na Demonstração (Sem Simulações)
- **Causa raiz diagnosticada:** A tela de demonstração gerava um sinal senoidal em memória (bip matemático de 2 segundos) e usava a síntese robótica do navegador (`SpeechSynthesis`), enquanto o backend usava um condicional de texto baseado no nome do arquivo.
- **Implementações realizadas:**
  - Disponibilizados arquivos de áudio gravados reais na pasta pública (`/audio/voz_humana_real.mp3` e `/audio/voz_golpe_clonado.mp3`).
  - O componente `AudioDeepfakeDemo.jsx` agora faz o streaming de áudio nativo via HTML5 `<audio>`, permitindo ao usuário escutar a gravação com clareza.
  - O botão de análise submete o arquivo de áudio real ao endpoint `/api/verificar/audio-rapido`, processando as características acústicas e o texto transcrito pelo pipeline de verdade.

---

## Como Tornar a UI Mais Didática para o Público Idoso

Pessoas idosas são os alvos mais frequentes de golpes de engenharia social (especialmente o "golpe do parente com celular novo" e o "falso resgate do Pix"). Para que a plataforma cumpra seu papel social, a experiência visual deve priorizar clareza, ausência de pânico e passos diretos.

### Diretrizes de Acessibilidade para Idosos Implementadas e Planejadas

```
┌─────────────────────────────────────────────────────────────┐
│                   METÁFORA DO FAROL                         │
├───────────────────┬───────────────────┬─────────────────────┤
│   🟢 VERDE        │    🟡 AMARELO     │     🔴 VERMELHO     │
│   CONFIÁVEL       │    ATENÇÃO        │     PERIGO / GOLPE  │
│   Pode ler e      │    Não temos      │     Não faça Pix!   │
│   compartilhar    │    certeza ainda  │     Não clique!     │
└───────────────────┴───────────────────┴─────────────────────┘
```

1. **Leitura em Voz Alta com 1 Clique (Botão "🔊 Ouvir explicação"):**
   - Idosos frequentemente relatam vista cansada ou dificuldade para ler textos longos na tela do celular.
   - Um botão visível lê a explicação em português com velocidade ajustada (0.92x), tom sereno e frases diretas.
2. **Checklist Prático de Ação Imediata ("O que você deve fazer agora"):**
   - Em vez de relatórios técnicos com jargões como "Perplexity 42.1" ou "HMAC SHA-256", exibe uma lista numerada:
     1. *Não transfira dinheiro nem faça Pix.*
     2. *Não clique em nenhum link nem passe códigos recebidos por SMS.*
     3. *Se disseram que é seu filho ou neto, ligue no número antigo dele para confirmar.*
     4. *Avise no grupo da família para proteger outras pessoas.*
3. **Botão Direto para o WhatsApp:**
   - Permite enviar com um toque uma mensagem carinhosa e clara no grupo da família explicando por que aquela mensagem é falsa, sem gerar atritos entre parentes.
4. **Modo Fácil / Letras Grandes (`A+`):**
   - Fontes com tamanho mínimo de 18px a 20px, alto contraste, espaçamento generoso e botões com área de toque ampla para evitar cliques acidentais.

---

## Como Criar o Bot de WhatsApp para Mensagens Encaminhadas

O WhatsApp é a principal porta de entrada de desinformação e golpes financeiros no Brasil. Criar um bot dedicado para receber mensagens encaminhadas é a maneira mais direta de alcançar os usuários.

### Arquitetura do Bot

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USUÁRIO NO WHATSAPP                             │
│       Recebeu mensagem com etiqueta "Encaminhada" ou áudio do golpe   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Encaminha para o contato do Verify
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        GATEWAY DO WHATSAPP                             │
│   Opção A: Evolution API (Self-Hosted, Open-Source, Baileys)           │
│   Opção B: WhatsApp Cloud API Oficial da Meta                          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Webhook POST /api/whatsapp/webhook
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         VERIFY BACKEND (FASTAPI)                       │
│  1. Envio de resposta imediata: "🔍 Checando fontes confiáveis..."     │
│  2. Roteamento por tipo de mídia:                                      │
│     ├─ Texto / Link   → Filtro SSRF + Busca Serper + Fact Checks       │
│     ├─ Áudio (Opus)   → Gemini Multimodal / AssemblyAI + Detector Golpe│
│     └─ Foto / Print   → Gemini Vision + OCR + EXIF / C2PA              │
│  3. Geração do veredito estruturado com dica para idosos               │
│  4. Síntese de áudio da resposta (áudio de voz para quem não lê)       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Resposta com badges + áudio TTS
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  MENSAGEM FORMATADA NO WHATSAPP                        │
│  📊 Veredito: 🔴 CUIDADO: ALERTA DE GOLPE                              │
│  📝 O QUE VOCÊ PRECISA SABER: [...]                                    │
│  💡 DICA DE SEGURANÇA: [...]                                           │
│  🔊 [Áudio com a explicação falada anexado]                            │
│  🛡️ Botão: Repassar alerta no grupo da família                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Especificação dos Tipos de Mensagem Tratados

| Tipo de Mensagem | Como o Bot Processa | Resposta ao Usuário |
| --- | --- | --- |
| **Texto Encaminhado** | Extrai alegações com Gemini, consulta Google Fact Check Tools e notícias em tempo real no Serper. | Texto com veredito (Verdadeiro, Falso, Boato), resumo e link oficial. |
| **Links / URLs** | Faz checagem de domínio suspeito, phishing, idade do registro e scraping do conteúdo com proteção SSRF. | Alerta se o site se passa por banco, Correios ou governo oficial. |
| **Áudios de Voz (`.ogg`, Opus)** | Transcreve o áudio via Gemini Multimodal Audio e detecta padrões de extorsão emocional urgente. | Transcrição em texto, veredito se é golpe e resposta falada. |
| **Fotos e Prints de Tela** | Analisa comprovantes de Pix adulterados, anúncios falsos ou fotos geradas por IA. | Veredito sobre autenticidade da imagem e sinais visuais de fraude. |

---

## O Que Deve Ser Implementado (Roadmap de Tarefas)

Abaixo está o inventário de tudo o que deve ser desenvolvido e integrado para a versão definitiva de produção:

### Fase 1 — Inteligência Forense e Resolução de Falsos-Positivos
- [x] Separar ferramentas de edição gráfica (Photoshop, Lightroom, GIMP, Canva) de modelos generativos de IA nos metadados.
- [x] Implementar matriz de consenso e elevar o limiar de decisão contra falsos-positivos.
- [x] Corrigir testes unitários do backend (26 testes aprovados sem falhas).
- [ ] Implementar passagem direta dos bytes de imagem para a API multimodal de visão do Gemini no endpoint `/api/upload`.
- [ ] Adicionar checagem de data de publicação mais antiga via Google Imagens Reversa (SerpApi) para descartar categoricamente geração recente por IA de fotos antigas.
- [ ] Adicionar suporte a extração automática de OCR em capturas de tela (prints de conversas e comprovantes bancários).

### Fase 2 — UI/UX Acessível para Pessoas Idosas
- [x] Adicionar botão de leitura em voz alta do relatório com síntese em português brasileiro.
- [x] Adicionar botão de compartilhamento direto no aplicativo do WhatsApp.
- [x] Adicionar card de passos práticos imediatos ("O que fazer agora").
- [x] Corrigir espaçamento superior do Meu Painel (`Dashboard.jsx`) e implementar rolagem para o topo ao trocar de rota (`PageWrapper`).
- [ ] Criar chave seletora global "Modo Terceira Idade / Modo Fácil" no cabeçalho, ativando tipografia ampliada de 20px e contraste reforçado em todo o site.
- [ ] Criar tutorial ilustrado em 3 passos com animação: *"Como compartilhar do seu WhatsApp para o Verify"*.
- [ ] Implementar resumo em cartão visual simplificado com botão de impressão de recibo em PDF de 1 página.

### Fase 3 — Demonstração e Interatividade ao Vivo
- [x] Inserir gravações de áudio reais na pasta pública (`voz_humana_real.mp3` e `voz_golpe_clonado.mp3`).
- [x] Substituir a síntese senoidal artificial e o sintetizador do navegador pelo reprodutor de áudio real em `AudioDeepfakeDemo.jsx`.
- [x] Conectar o botão de análise ao endpoint real `/api/verificar/audio-rapido`.
- [ ] Adicionar seletor com 4 novos exemplos reais:
  1. Áudio real de idosa conversando sobre receita de bolo.
  2. Áudio de clonagem com pedido de resgate falso.
  3. Comprovante falso de Pix agendado.
  4. Foto histórica autêntica da década de 1980 com compressão de WhatsApp para provar a ausência de falso-positivo.

### Fase 4 — Integração e Publicação do Bot de WhatsApp
- [x] Endpoint base de webhook do WhatsApp (`POST /api/whatsapp/webhook`).
- [x] Endpoint de simulação interativa (`POST /api/whatsapp/simulate`).
- [ ] Implementar contêiner Docker da **Evolution API** no `docker-compose.yml` para pareamento com QR Code de número real.
- [ ] Adicionar suporte a download automático de mídias recebidas (áudios `.ogg` e imagens `.jpeg`) pelo webhook.
- [ ] Integrar envio de resposta em formato de nota de voz (gerada via Gemini TTS ou Google Cloud TTS) para o usuário que enviou um áudio.
- [ ] Salvar histórico das conversas anônimas do WhatsApp associadas a números com hash para métricas de desinformação recorrente.

---

## Tecnologias

| Camada | Tecnologia | Finalidade |
| --- | --- | --- |
| **Interface** | React 18, Vite, Tailwind CSS, Lucide | Painel responsivo e acessível para web e celular |
| **API** | FastAPI (Python 3.11/3.12), Pydantic v2 | Orquestração assíncrona do pipeline forense |
| **Banco de Dados** | PostgreSQL 16 com asyncpg / SQLAlchemy | Armazenamento de auditorias, métricas e usuários |
| **Inteligência Artificial** | Google Gemini (3.7 Flash, 1.5 Flash), AssemblyAI | Transcrição, visão multimodal e geração de vereditos |
| **Forense de Mídia** | Sightengine, Hive, ExifTool, C2PA Tool | Detecção de manipulação, selos de proveniência e metadados |
| **Busca de Fatos** | Google Fact Check Tools API, Serper (Google News) | Cruzamento com checagens de agências oficiais |
| **Bot WhatsApp** | Webhook nativo (FastAPI) preparado para Evolution API / Meta Cloud API | Atendimento de mensagens encaminhadas |
| **Infraestrutura** | Docker Compose, Railway (Backend + DB), Vercel (Frontend) | Execução local e publicação em nuvem |

---

## Executar Localmente com Docker

### 1. Clonar e configurar variáveis de ambiente
```bash
cp backend/.env.example backend/.env
```
Preencha pelo menos a `GEMINI_API_KEY` gerada no [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Subir todos os serviços
```bash
docker-compose up --build
```

Portas mapeadas no ambiente:
- **Interface Web:** `http://localhost:5174`
- **API FastAPI:** `http://localhost:8001`
- **Documentação Swagger:** `http://localhost:8001/docs`
- **Health Check da API:** `http://localhost:8001/health`
- **PostgreSQL:** `localhost:5433`

### 3. Rodar todos os testes de verificação
Para executar a suíte completa de testes unitários e de integração dentro do contêiner do backend:

```bash
docker exec -t verify-backend python -m unittest discover -s tests -v
```

Resultado esperado:
```text
Ran 26 tests in ~4s
OK (skipped=2)
```

Para validar a compilação do frontend:
```bash
docker exec -t verify-frontend npm run build
```

---

## Variáveis de Ambiente Canônicas

| Variável | Obrigatória | Finalidade |
| --- | --- | --- |
| `DATABASE_URL` | Sim | Conexão PostgreSQL assíncrona (`postgresql+asyncpg://...`) |
| `GEMINI_API_KEY` | Sim | Orquestração da IA, visão multimodal e transcrição de áudios |
| `GEMINI_MODEL_NAME` | Não | Modelo padrão (ex: `gemini-3.7-flash` ou `gemini-1.5-flash`) |
| `JWT_SECRET` | Sim | Assinatura dos cookies HTTP-only de sessão |
| `HMAC_SECRET_KEY` | Sim | Assinatura digital criptográfica dos selos de autenticidade |
| `GOOGLE_FACT_CHECK_KEY` | Não | Chave da API Google Fact Check Tools |
| `SERPERAPI_KEY` | Não | Busca de notícias em tempo real no Google via Serper |
| `SIGHTENGINE_API_USER` / `SECRET` | Não | Detecção de deepfakes e IA em imagens |
| `HUGGINGFACE_API_TOKEN` | Não | Modelo complementar de detecção de imagem |
| `HIVE_API_KEY` | Não | Análise multimídia do TheHive.ai |
| `ASSEMBLYAI_API_KEY` | Não | Transcrição fonética e medição de confiança acústica |
| `COOKIE_SECURE` | Produção | Deve ser `true` sob HTTPS |
| `COOKIE_SAME_SITE` | Produção | `none` em domínios separados (Vercel/Railway) ou `lax` em subdomínio próprio |
