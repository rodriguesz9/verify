# Configurar o Verify em produção

Guia de 3 de outubro de 2026. Configuração completa não garante vereditos infalíveis. Os testes locais validam regras e funcionamento; precisão exige avaliação independente com amostras rotuladas.

## 1. Railway: configurações básicas

Abra `alert-peace` → `production` → serviço **verify** → **Variables**, não o serviço Postgres. Não cole chaves no chat nem no frontend.

Estes valores não são segredos e podem ser adicionados pelo RAW Editor. Confira antes de salvar: não substitua chaves existentes por campos vazios do `.env.example`.

```dotenv
APP_ENV=production
COOKIE_SECURE=true
COOKIE_SAME_SITE=none
CORS_ORIGINS=https://verifybr.vercel.app
CORS_ORIGIN_REGEX=
SIGHTENGINE_AUDIO_ENABLED=false
VIDEO_MAX_FRAMES=9
EXIFTOOL_ENABLED=true
C2PATOOL_ENABLED=false
WAYBACK_API_ENABLED=true
WHATSAPP_BOT_ENABLED=false
WHATSAPP_HISTORY_ENABLED=false
ANALYSIS_REQUESTS_PER_MINUTE=10
ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE=60
ANALYSIS_MAX_CONCURRENT=4
API_MAX_BODY_BYTES=36700160
```

Outros valores indispensáveis:

| Variável | O que colocar |
| --- | --- |
| `DATABASE_URL` | Referência `${{Postgres.DATABASE_URL}}`, se esse for o nome do serviço. Preserve a referência existente correta; não copie a URL SQLite local. |
| `JWT_SECRET` | Segredo aleatório próprio, pelo menos 32 caracteres. Produção não inicia com segredo fraco/ausente. Trocar invalida sessões existentes. |
| `HMAC_SECRET_KEY` | Outro segredo aleatório, independente do JWT, pelo menos 32 caracteres. Trocar pode invalidar registros de integridade anteriores. |

Você pode gerar dois segredos em um gerenciador de senhas. Não use senhas de exemplo. Não altere segredos válidos só para seguir este guia.

### Publicação e ferramentas locais

- Repositório: `rodriguesz9/verify`, branch `master`.
- Se a raiz do serviço for `/backend`, use o Dockerfile dessa pasta e o arquivo de configuração `/backend/railway.toml`; o comando inicial precisa respeitar `$PORT`.
- Se a raiz for o repositório inteiro, use o Dockerfile e `railway.toml` da raiz. Não combine contexto `/backend` com `COPY backend/` do Dockerfile da raiz.
- Os dois Dockerfiles instalam **FFmpeg/ffprobe e ExifTool**. Confira os logs do build: não basta cadastrar `EXIFTOOL_ENABLED=true` para instalar uma ferramenta.
- `C2PATOOL_ENABLED=false` é o estado seguro até instalar c2patool, configurar âncoras confiáveis e testar assinaturas. FFmpeg não depende de chave de API.
- Na consulta desta etapa havia quatro mudanças pendentes: `APP_ENV`, `CORS_ORIGINS`, `SIGHTENGINE_AUDIO_ENABLED` e uma atualização de configuração do serviço. Valores/configuração pendentes não foram revelados pelo conector. Abra **Details**, confira cada mudança e só depois aplique **Deploy**. [Funcionamento das variáveis](https://docs.railway.com/variables) · [Dockerfiles](https://docs.railway.com/builds/dockerfiles).

## 2. Chaves para cada análise

Nome cadastrado e asteriscos no painel não comprovam valor válido, acesso ao modelo ou saldo. Não precisa contratar tudo; camadas ausentes devem permanecer explícitas/inconclusivas.

| Análise | Variáveis / serviço | Onde obter |
| --- | --- | --- |
| Texto, link e afirmações extraídas de mídia | `GOOGLE_FACT_CHECK_KEY` | [Ativar Fact Check Tools API](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com) → [Credenciais Google Cloud](https://console.cloud.google.com/apis/credentials). Restrinja a chave a essa API. |
| OCR, transcrição, auxílio visual e voz educativa | `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `GEMINI_TTS_MODEL` | [Google AI Studio](https://aistudio.google.com/app/apikey). Escolha IDs de [modelos disponíveis](https://ai.google.dev/gemini-api/docs/models) na sua conta; TTS tem acesso/quota próprios. |
| Imagem e quadros de vídeo | `SIGHTENGINE_API_USER`, `SIGHTENGINE_API_SECRET` | [Sightengine](https://dashboard.sightengine.com/). Confirme acesso a `genai`/`deepfake` no plano. |
| Imagem / quadros, manipulação facial, áudio | `HIVE_IMAGE_API_KEY`, `HIVE_DEEPFAKE_API_KEY`, `HIVE_AUDIO_API_KEY` | [Portal Hive](https://portal.thehive.ai/). Projeto v2 e chave específicos para **cada** modelo; `HIVE_API_KEY` não habilita todos. Duas chamadas Hive não contam como dois provedores independentes. |
| Detector adicional de imagem | `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_IMAGE_API_URL`, `HUGGINGFACE_AI_LABEL` | [Tokens HF](https://huggingface.co/settings/tokens) e [Endpoints](https://endpoints.huggingface.co/). Token sozinho não hospeda um modelo. Endpoint oficial HTTPS e classe positiva exata do detector. |
| Segundo detector de fala sintética | Credenciais Sightengine + opt-in `SIGHTENGINE_AUDIO_ENABLED=true` | [Modelo ai_speech](https://sightengine.com/docs/ai-generated-speech-detection). Habilite somente depois de confirmar autorização enterprise/parceiro e preço; chave de imagem não basta. |
| Transcrição alternativa | `ASSEMBLYAI_API_KEY` | [AssemblyAI](https://www.assemblyai.com/dashboard/). Transcrição **não** é detecção de clonagem. |
| Notícias relacionadas | `SERPERAPI_KEY` | [Serper](https://serper.dev/). Notícias relacionadas não decidem verdade. |
| Login Google, opcional | `GOOGLE_CLIENT_ID` no backend e o mesmo `VITE_GOOGLE_CLIENT_ID` público na Vercel | [Google Cloud — credenciais](https://console.cloud.google.com/apis/credentials). Cliente OAuth web com origem autorizada `https://verifybr.vercel.app`. Não colocar client secret no frontend. |

Primeiro valide Google Fact Check + Gemini. Para concordância de imagem, valide Sightengine e Hive de imagem (ou HF realmente hospedado). Para áudio, a política requer dois detectores disponíveis: Hive áudio e Sightengine `ai_speech` autorizado. Sem segundo detector, o resultado pode continuar inconclusivo; cadastrar AssemblyAI não resolve isso.

Vídeo usa detectores de imagem nos quadros e de áudio na faixa sonora. Não é uma análise completa de identidade ou sincronização labial. Texto sem duas checagens editoriais correspondentes também pode ser inconclusivo, mesmo com todas as chaves válidas.

`OPENROUTER_API_KEY`, `SERPAPI_KEY`, `MIN_CONFIDENCE_THRESHOLD` e outras variáveis legadas não substituem estas configurações. `VIRUSTOTAL_API_KEY` está no roteiro futuro, não implementa hoje uma análise de malware. WhatsApp real exige gateway, transporte e autenticação adicionais; mantenha desligado até validar o fluxo.

## 3. Vercel

Projeto `verify`: Root Directory `frontend`, Build Command `npm run build`, Output Directory `dist`.

```dotenv
VITE_API_URL=https://verify-production-ead7.up.railway.app
```

Não acrescente `/api`. Só URL e, opcionalmente, client ID público do Google entram em `VITE_*`; nunca chaves Gemini/Hive/Sightengine ou segredos do banco. Variáveis Vite entram na compilação: alteração exige novo deploy.

## 4. Como conferir depois do deploy

1. Compare o commit do deploy ao commit publicado no GitHub. Push não prova que a aplicação já foi implantada.
2. Abra [saúde da API](https://verify-production-ead7.up.railway.app/health) e [configuração/cobertura](https://verify-production-ead7.up.railway.app/api/capabilities). A segunda rota só existe na revisão nova.
3. Em capabilities, confirme `policy_version=2026-10-03.1`, FFmpeg/ffprobe/ExifTool e os provedores configurados. `operational_status=not_tested` não é confirmação de funcionamento; a rota não faz chamadas pagas.
4. Teste login, histórico, texto, link público, imagem, áudio, vídeo e PDF. Use somente controles autorizados, não conteúdo privado. Veja fontes/cobertura, não apenas HTTP 200.
5. Verifique autorização (403), quota (429), classes/modelos e falhas; nunca interpretar indisponibilidade como falsidade. Confira cobrança e retenção nos painéis dos fornecedores.

O [guia de verificação](VERIFICACOES-2026-10-03.md) registra testes, limites e como medir precisão incluindo inconclusivos. Não divulgar “100% correto” sem avaliação independente — mesmo essa avaliação não garantiria acerto em qualquer conteúdo futuro.

Próxima etapa visual: melhorar a landing com texto simples, contraste, botões grandes, navegação clara e animações discretas que respeitem movimento reduzido, preservando idosos e pessoas leigas.
