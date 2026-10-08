# Configurar as APIs sem novas contratações

**Nota de 08/10/2026:** este guia conserva observações de 03/10. Priorize o [status atual e os nomes de configuração](STATUS-VERIFICACOES-2026-10-08.md): Gemini multimodal não está homologado; OpenRouter local já tem chave; a [página atual de preços HF](https://huggingface.co/docs/inference-providers/pricing) informa que contas gratuitas não recebem créditos mensais. Não comprar créditos nem criar endpoint pago.

Revisão: 3 de outubro de 2026. Preferência do responsável: usar as contas existentes e opções gratuitas, **sem contratar planos, GPUs ou recargas automáticas**.

Atualização após testes reais: [resultados multimodais](MULTIMODAL-2026-10-03.md). OCR local passou sem internet; Gemini OCR passou com modelo multimodal separado; AssemblyAI transcreveu a fala portuguesa de controle. HF compartilhado respondeu, mas errou um controle: sinal experimental, sem voto. Nova chave SerpAPI autenticou após substituição pelo usuário.

## O que já existe e o que falta

Inspeção limitada aos nomes das variáveis do Railway e à presença de valores no `.env` local. Nenhum segredo foi publicado. Chave preenchida não comprova validade, saldo, quota ou autorização ao modelo.

| Serviço | Railway | Próximo passo sem contratar |
| --- | --- | --- |
| Google Fact Check | `GOOGLE_FACT_CHECK_KEY` presente | Confirmar API habilitada e restrição correta no projeto Google Cloud. É a prioridade para checagem factual. |
| Gemini | `GEMINI_API_KEY` presente | Confirmar Free Tier e modelo disponível. `GEMINI_MODEL_NAME` e `GEMINI_TTS_MODEL` podem ser definidos explicitamente; não são chaves. |
| Sightengine imagem | `SIGHTENGINE_API_USER` e `SIGHTENGINE_API_SECRET` presentes | Conferir Free plan, quota e acesso a `genai`/`deepfake`. |
| Serper | `SERPERAPI_KEY` presente | Conferir saldo gratuito restante; pesquisa auxilia contexto, não prova veracidade. |
| AssemblyAI | `ASSEMBLYAI_API_KEY` presente | Conferir créditos de teste restantes; serve para transcrever, não detectar clonagem. |
| Hugging Face | Endpoint compartilhado testado; configuração no guia multimodal | Resultado experimental sem voto, pois houve falso negativo. Créditos finitos; não criar endpoint dedicado pago. |
| Hive | `HIVE_API_KEY` presente; painel mostra v3 | Cliente v3 testado com uma imagem. Existe custo por uso; manter pausado fora do teste autorizado. Não comprar projetos v2. |

O `.env` local tem Gemini, Sightengine, Hugging Face, Hive, Serper, SerpAPI e AssemblyAI preenchidos; `OPENROUTER_API_KEY` está vazio. O Railway já tem variáveis adicionais. **Não substituir a configuração de produção pelo `.env` inteiro.**

## Ordem recomendada

### 1. Google Fact Check — fontes de checagens

1. Abra a [biblioteca da Fact Check Tools API](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com) no projeto correto e confira se está habilitada.
2. Em [APIs e serviços → Credenciais](https://console.cloud.google.com/apis/credentials), confira a chave existente ou crie uma para esse projeto.
3. Nas restrições de API, autorize a **Fact Check Tools API**. Uma chave de Gemini não comprova que essa API está habilitada.
4. Guarde a chave em `GOOGLE_FACT_CHECK_KEY`, apenas no backend Railway. Confira quotas e qualquer solicitação de faturamento antes de aceitar; não ativar outras APIs pagas.

A [documentação oficial de Claim Search](https://developers.google.com/fact-check/tools/api) exige chave. Essa busca recupera checagens publicadas: não verifica automaticamente qualquer afirmação, nem exige configurar escrita de ClaimReview/Search Console para este uso.

### 2. Gemini — auxílio multimodal e narração

Abra [Google AI Studio → API keys](https://aistudio.google.com/apikey). Use a conta existente, confira o projeto e o nível gratuito. Na [tabela oficial de preços](https://ai.google.dev/gemini-api/docs/pricing), confirme a coluna Free Tier do modelo escolhido; confira também [limites](https://ai.google.dev/gemini-api/docs/rate-limits).

O código tem `gemini-3.7-flash` como padrão de análise e `gemini-3.8-flash-tts` como padrão de voz. Não é necessário pagar ou trocar de chave só porque essas variáveis de modelo estão ausentes. Se o painel autorizar modelos diferentes, configure os identificadores exatos em `GEMINI_MODEL_NAME` e `GEMINI_TTS_MODEL`.

Sem cota, uma resposta 429 deve continuar como indisponibilidade, não “falso”. Voz/TTS tem disponibilidade própria. No nível gratuito, conteúdo pode ser usado para melhorar produtos: **não enviar dados sensíveis ou documentos pessoais sem avaliar essa condição**. Gemini não substitui evidências factuais ou um detector especializado.

### 3. Sightengine — usar somente a oferta gratuita disponível

Entre no [painel Sightengine](https://dashboard.sightengine.com/). Confira plano, operações restantes e modelos autorizados; as credenciais correspondem a `SIGHTENGINE_API_USER` e `SIGHTENGINE_API_SECRET`.

Há um [plano gratuito de testes, com limites](https://sightengine.com/pricing); isso não garante acesso gratuito a todos os modelos. `genai` e `deepfake` consomem várias operações por imagem; quadros de vídeo multiplicam consumo ([como as operações são contadas](https://sightengine.com/faq/what-is-an-operation)).

**Deixe `SIGHTENGINE_AUDIO_ENABLED=false` enquanto não houver acesso autorizado.** A [detecção `ai_speech` está disponível em planos pagos](https://sightengine.com/faq/detect-ai-generated-speech-voice-clones). Não contratar para esta etapa. Ter uma chave de imagem não habilita áudio automaticamente.

### 4. Serper e AssemblyAI — aproveitar saldo existente

- [Serper](https://serper.dev/): oferece consultas iniciais gratuitas; confira saldo da conta existente e mantenha a chave em `SERPERAPI_KEY`. Não presumir renovação mensal nem comprar pacote.
- [AssemblyAI Dashboard](https://www.assemblyai.com/dashboard/signup): use **Log in** se já tiver conta e confira API keys/Billing. Guarde em `ASSEMBLYAI_API_KEY`. A [oferta para novas contas é crédito limitado de teste](https://support.assemblyai.com/articles/5370767329-can-i-sign-up-for-free), não transcrição ilimitada. Não adicionar cartão nem ativar autopay.

Serper localiza páginas. AssemblyAI converte voz em texto. Nenhum dos dois, isoladamente, prova falsidade ou clonagem.

### 5. Hugging Face — token não é hospedagem gratuita

Seu token já tem campo no Railway. Se precisar revisar permissões, abra [Settings → Access Tokens](https://huggingface.co/settings/tokens); não dar acesso de escrita desnecessário.

A [regra atual de créditos](https://huggingface.co/docs/inference-providers/pricing) não inclui franquia mensal para contas gratuitas. A integração exige um classificador imagem real/gerada por IA efetivamente hospedado, autorizado e com resposta `label`/`score`; não criar endpoint pago:

Nesta revisão, confirmou-se inferência compartilhada para `Ateeqq/ai-vs-human-image-detector`, classe positiva `ai`. Não é necessário contratar GPU para esse endpoint; acesso e crédito podem expirar. O erro observado no controle sintético impede usá-lo como voto decisivo. Configuração exata e resultado em [MULTIMODAL-2026-10-03.md](MULTIMODAL-2026-10-03.md).

- `HUGGINGFACE_IMAGE_API_URL`: URL HTTPS de inferência oficial, não a página do modelo ou uma demo Space qualquer.
- `HUGGINGFACE_AI_LABEL`: classe positiva exata retornada pelo modelo; `artificial` é apenas o padrão do código.

Não cadastrar endpoint inventado para tirar o aviso de configuração. **Não criar Inference Endpoint dedicado:** há [cobrança durante inicialização e execução](https://huggingface.co/docs/inference-endpoints/en/pricing), inclusive sem consultas. Se nenhum detector compatível estiver disponível gratuitamente, mantenha essa camada indisponível. Rodar modelo aberto localmente seria outro projeto, exigindo recursos e validação — não é equivalente a habilitar esta API com um token.

### 6. Hive imagem / Deepfake / áudio — chave v3 e orçamento explícito

No [Hive Models](https://thehive.ai/explore), abra **Service API Keys**. Guarde o Secret Key, não o Access Key ID, em `HIVE_V3_API_KEY`; uma chave existente em `HIVE_API_KEY` também é aceita com `HIVE_API_VERSION=v3`. O cliente agora distingue explicitamente v3 de v2, sem presumir compatibilidade.

O v3 combina geração por IA e deepfake na mesma chamada. O [Playground oficial](https://thehive.ai/models/hive/ai-generated-and-deepfake-content-detection) exibia US$ 6/1.000 imagens/quadros e US$ 10/h de áudio. Foi feito apenas um teste de imagem, estimado em US$ 0,006, com teto autorizado de US$ 0,01. **Não é grátis e não houve autorização de gasto contínuo.** `HIVE_V3_MEDIA_TYPES` vazio impede chamadas; não ativar imagem/áudio públicos nem recarga automaticamente.

Se tiver projetos v2 autorizados, preserve suas chaves específicas e selecione v2. Não contratar três planos para preencher campos. Contratos e classes estão em [ATIVAR-DETECTORES.md](ATIVAR-DETECTORES.md).

## Campos opcionais que não precisamos comprar

| Campo | Situação no código |
| --- | --- |
| `OPENROUTER_API_KEY` | Agora integrado à busca e ao OCR auxiliar. `OPENROUTER_MODEL=openrouter/free`, preços máximos zero, limite local e pausa após quota. Não precisa comprar créditos. [Portal](https://openrouter.ai/settings/keys). |
| `GPTZERO_API_KEY` | Camada opcional de autoria de texto, não veracidade. Cliente legado exige validar contrato e idioma antes de ativação. [Docs](https://gptzero.me/docs). |
| `TINEYE_API_KEY` | Busca reversa opcional; contrato do cliente legado não homologado nesta etapa. Site gratuito não equivale a API gratuita. [Docs](https://services.tineye.com/developers/). |
| `SERPAPI_KEY` | Já presente; Google Lens não envia uploads privados automaticamente. Preencher a chave não ativa essa busca. [Portal](https://serpapi.com/manage-api-key). |
| `HIVE_TEXT_API_KEY` | Integração legada, não usada na checagem principal. |
| `VIRUSTOTAL_API_KEY` | Roadmap, não integrado ao pipeline atual. Não obter chave só para preencher o exemplo. |
| `GOOGLE_CLIENT_ID` | Somente login Google; já existe no Railway. Não é detector. [Credenciais OAuth](https://console.cloud.google.com/apis/credentials). |

FFmpeg, ExifTool e C2PA são ferramentas locais, não APIs que precisam de chave. `C2PATOOL_TRUST_ANCHORS` é configuração de confiança; habilitar uma variável não instala binário nem valida assinatura. JWT/HMAC são segredos da aplicação: **não trocar os existentes durante configuração de fornecedores**.

## Como salvar no Railway

1. Abra o [Railway](https://railway.com/) → projeto **alert-peace** → **production** → serviço **verify** → **Variables**.
2. Adicione/edite somente a variável necessária. Cole o valor privado diretamente ali, sem postar no chat, GitHub, print ou `VITE_*`. Não copiar placeholders deste guia.
3. Preserve `DATABASE_URL`, segredos de autenticação e configuração de cookies/CORS de produção. Variáveis locais de desenvolvimento não são valores de produção.
4. Revise as alterações, aplique e publique. Aguarde deploy bem-sucedido.
5. Confira `/api/capabilities`: informa presença de configuração, **não testa saldo nem precisão**. Depois teste controles de origem conhecida apenas nos serviços cujo plano gratuito esteja confirmado, com poucas solicitações.

O teste real Hive foi limitado a uma imagem dentro dos US$ 0,01 autorizados. Não foram contratados planos, criadas chaves fictícias ou ativadas recargas. Chave SerpAPI exposta no print precisa ser revogada/regenerada no [painel](https://serpapi.com/manage-api-key), depois substituída privadamente no Railway e `.env`.

## O que esperar sem pagar

Checagem factual pode usar fontes recuperadas; metadata e credenciais assinadas válidas ajudam na origem. Modelos e transcrição ficam sujeitos às cotas. **Sem detectores autorizados, clonagem de voz/manipulação facial devem continuar como indisponíveis ou inconclusivas** — transcrição, estética e ausência de metadata não substituem esses detectores.

Não reduzir a política de concordância ou usar opinião de Gemini/OpenRouter como prova para eliminar inconclusivos. Mesmo com todas as APIs ativas, nenhum detector garante 100% de acerto.
