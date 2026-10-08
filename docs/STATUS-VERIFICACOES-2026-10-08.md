# Verify — o que funciona, o que falta e como configurar

Atualização: **8 de outubro de 2026**, horário de Brasília. Código publicado e ensaiado em `cba8d3f77cb60ae1906ab1ccb292c77f6f3e7b40`; Vercel READY/Railway SUCCESS, candidato e master com CI aprovado. Filtro de contexto Serper rechecado na interface: 200/4,924 s, sem notícias irrelevantes. Commits posteriores exclusivos de documentação não alteram esse código. [Fechamento da publicação](PUBLICACAO-2026-10-08.md#7-publicação-da-revisão-posterior-e-rechecagem).

**Publicação da base anterior nesta data:** Railway deployment `a0e0d2b0-fbf9-4473-9350-eae24d9be5b7` SUCCESS, Vercel `dpl_J5zdpkUjexfSMs8xsWTMi7GN9sDm` READY, ambos em `ef9655ff9d3fa4d350d149cc5b48e44b3611b729`. Texto e duas imagens tiveram respostas reais pela interface pública; OCR/Gemini, origem visual e política factual são dimensões distintas. [Registro atualizado de publicação](PUBLICACAO-2026-10-08.md). Os 422/500 do SHA antigo e os controles isolados permanecem históricos no [diagnóstico anterior](CORRECOES-PRODUCAO-2026-10-08.md).

**Resposta curta: não, todas as verificações ainda não estão homologadas.** Texto/imagens e exportação HTTP têm novos controles públicos no SHA confirmado; isso não valida todo o produto. Ainda faltam homologação multimodal abrangente, avaliação independente de precisão, fala/vídeos humanos autorizados, salvamento/abertura do PDF e demais fronteiras de produção. Nenhuma chave ou combinação de APIs garante vereditos 100% certos.

## 1. Como interpretar os resultados

São quatro perguntas diferentes:

| Pergunta | O que comprova | O que não comprova |
| --- | --- | --- |
| Está configurado? | Nome e configuração necessários presentes no processo | Chave válida, acesso ao modelo, saldo, resposta ou precisão |
| Respondeu à API? | Transporte e contrato funcionaram naquele controle/data | Todos os formatos, fidelidade, disponibilidade futura ou classificação correta |
| Passou nos testes automatizados? | Regras e cenários controlados não regrediram | Acerto em mídia desconhecida; testes com mocks não chamam o fornecedor |
| Está homologado no deploy? | Fluxo da interface publicada até API/banco/relatório foi ensaiado no SHA candidato | Infalibilidade ou cobertura de qualquer conteúdo da internet |

`/api/capabilities` informa configuração/ferramentas; seus fornecedores permanecem com `operational_status=not_tested`. `/health` mede resposta do processo; `/ready` consulta o banco. **Nenhum deles faz uma análise real nem mede precisão.**

O relatório distingue:

- **Veracidade:** o conteúdo da afirmação, baseado em checagens correspondentes.
- **Origem/autenticidade:** sinais de geração ou manipulação da mídia.
- **Leitura:** OCR/transcrição; ler corretamente uma frase não prova que ela seja verdadeira.
- **Triagem de golpe:** padrões suspeitos e orientação preventiva; não comprova identidade do remetente.

“Inconclusivo” pode ser o resultado correto quando a cobertura é insuficiente. Uma foto gerada por IA pode ilustrar um fato verdadeiro; uma foto publicada por fonte conhecida pode receber legenda falsa.

## 2. Situação por verificação e API

As respostas externas abaixo identificam a data do controle: novas observações de **08/10** não substituem uma homologação de todas as APIs. Registros anteriores de 07/10 permanecem históricos; quando apenas narrativos, isso está indicado em [fechamento de 07/10](FECHAMENTO-2026-10-07.md#4-outras-observações-de-apis-nesta-sessão). Diagnóstico, correções e controles pendentes desta rodada estão no [registro complementar](CORRECOES-PRODUCAO-2026-10-08.md).

| Verificação/camada | Última evidência | Por que ainda não está totalmente validada | Como avançar sem inventar resultados |
| --- | --- | --- | --- |
| Texto — Google Fact Check | Controle público de 08/10 respondeu `/check-text` 200/5,704 s; cobertura factual sem checagens correspondentes, mensagem preventiva corretamente inconclusiva | A API recupera checagens existentes; não pesquisa a verdade de qualquer frase. Sem correspondência suficiente, a política não conclui | Ensaiar afirmações com checagens reais de duas famílias editoriais, mesmo conteúdo/contexto/data. Ausência de resultado continua inconclusiva |
| Texto — Gemini | Em 08/10, diagnóstico 3.8 atingiu timeout de 60 s; controle Lite pela interface isolada teve `/check-text` e Gemini HTTP 200 | Modelo 3.8 e Lite têm evidências diferentes; disponibilidade varia. O 200 local não explica automaticamente os três 422 públicos, cuja entrada foi rejeitada e corpo não foi observado | Conferir modelo/quota e mensagem de validação separadamente; ensaiar preservação literal no SHA publicado. Admissão local não mede quota global; Gemini não vota “verdadeiro/falso” |
| Texto — OpenRouter gratuito | Cobertura “respondeu” no controle público de 08/10; “Não pague” preservado. Modelo específico `liquid/lfm-2.5-2.6b:free` é registro histórico de 07/10, não atribuído ao controle novo | Modelos gratuitos/capacidade mudam; sucesso não o torna detector factual nem confirma todos os formatos | Manter `openrouter/free` ou modelo explicitamente `:free`, preço máximo zero e limites. Ensaiar preservação literal; indisponibilidade deve aparecer no relatório |
| Contexto — Serper | No primeiro controle público incluiu notícias irrelevantes de cassino/dívidas. Filtro posterior cba8d3f publicado/rechecado: essas notícias não apareceram, busca concluída sem correspondência lexical utilizável; texto 200/4,924 s | Notícias relacionadas não são checagens da mesma afirmação. Filtro lexical pode excluir sinônimos/refutações/resumos incompletos; não é equivalência semântica | Conferir contagens de retorno bruto/exclusão e preservar `no_results` diferente de indisponível. Não promover contexto a prova |
| Links públicos | Correção da persistência de datas integra SHA ef9655ff publicado; regressão PostgreSQL descartável passou. Log 500 do SHA antigo preservado como histórico | Novo fluxo completo link→banco/histórico público ainda não foi ensaiado nesta rodada; não certifica páginas JavaScript | Ensaiar URL pública autorizada, conferir texto/fonte/truncamento e histórico. Datas relativas de métricas permanecem desconhecidas, não são inventadas |
| Imagem — OCR local | Tesseract leu controle impresso pela interface em 07/10, preservando negação, R$ 123,45 e data | Um impresso limpo não mede todos os prints, manuscritos ou imagens degradadas | Instalar binário + idiomas `por`/`eng` na imagem final; manter `LOCAL_OCR_ENABLED=true` e conferência humana antes de checar o texto |
| Imagem — Gemini OCR/inspeção | Em 08/10, Lite visão respondeu nas duas imagens pela interface publicada; planta com leitura “Sem texto”, foto NASA com fragmento OCR “A” não usado para checagem. Controle isolado anterior Lite OCR 200/~2,376 s correspondeu à referência impressa de 88 caracteres; 3.8 retornou 503/~41,8 s | Visão/leitura funcionaram nesses controles, não homologam manipulação/voz ou acerto universal. Fragmento curto não permite afirmar fidelidade ou alucinação; a imagem só com LLM no ensaio isolado ficou inconclusiva, diferente da cobertura do ensaio público | Manter conferência humana e limites da conta; testar prints/formatos independentes. “Sem texto” em uma imagem de planta não significa falha de autorização nem informação falsa |
| Imagem — OpenRouter OCR | Tentativas anteriores tiveram HTTP 404/resposta incompleta | Não havia resposta de visão/OCR utilizável; texto funcionando não valida imagem | Só configurar variante gratuita realmente compatível com imagem + formato exigido. Não ativar fallback pago; manter Tesseract/conferência como contingência |
| Imagem — Sightengine | Pela interface pública em 08/10: planta IA, sinal 99,0%; foto NASA zinnia, sinal 0,1%. Percentuais arredondados, não calibrados | Dois controles não são benchmark. Face-swap/transformações não homologados; ausência de sinal não certifica câmera/origem | Manter exemplos independentes, acesso/créditos autorizados e tratar pontuação como sinal, não probabilidade de acerto |
| Imagem — Hugging Face | Respostas históricas experimentais erraram controles. Revisão 08/10 usa `HUGGINGFACE_ENABLED=false` padrão | Usuário recusou contratação paga. Chave presente não implica endpoint/saldo e não deve gerar envio após opt-out | Manter `false` no Railway/candidato; não criar endpoint nem comprar créditos. Sinal experimental continua sem voto, inclusive vídeo |
| Imagem/facial — Hive v3 | Dois novos controles pela interface pública em 08/10: planta IA, sinal 100,0% arredondado; foto NASA, 0,0% arredondado. Planta recebeu “Indícios de IA”, foto permaneceu inconclusiva. Teto nominal destes dois envios US$ 0,012, sem consulta de saldo/fatura | Dois exemplos não medem acurácia nem homologam face-swap/voz. `hive_deepfake` reutiliza a mesma chamada Hive; não é fornecedor independente. Zero não certifica autenticidade | Conferir Usage/Billing sem recarga automática. Guardas por processo não são teto financeiro global. [Passos e limites](ATIVACAO-HIVE-VOZ-2026-10-08.md) |
| Hive v2 por projeto | Cliente e parsing cobertos por testes; projetos específicos não homologados nesta etapa | Chave de projeto de imagem não é automaticamente projeto de áudio/facial/texto; chave v3 não é chave v2 | Conferir versão e projeto no painel. Usar nomes específicos. Não contratar novos projetos apenas para preencher o template |
| Áudio — AssemblyAI | Transcrição de voz sintética já respondeu, mas houve erro “Pix urgente” → “pic surgente”; fala humana ainda pendente | Reconhecimento pode perder palavra/negação/valor/data. Retomada de tarefa foi testada com transporte simulado, não nova voz reconhecida | Se houver créditos gratuitos autorizados, preferir `AUDIO_TRANSCRIPTION_PROVIDER=assemblyai`; subir gravações humanas sem dados pessoais e conferir a leitura na UI |
| Áudio — retomada AssemblyAI | Ensaio local 07/10: duas tentativas, um upload/uma criação/duas consultas simuladas | Cache por processo/sessão tem janela limitada; reinício, réplica, expiração ou perda de contexto não têm garantia durável | Evitar reenviar repetidamente. Resultado pendente não vira “sem fala”; concluir checkpoint compartilhado para escala. [Limites/testes](TRANSCRICAO-PENDENTE-2026-10-07.md) |
| Áudio — Gemini transcrição | Não há homologação atual em fala humana após as falhas multimodais | Texto mínimo bem-sucedido não valida fala; transcrição não autentica voz | Modelo multimodal separado, prazo/quota e teste humano autorizado. Não usar transcrição como detector de clonagem |
| Áudio — Sightengine `ai_speech` | Cliente testado offline; acesso real ao modelo não comprovado | Chaves de imagem não liberam esse modelo. Documentação atual informa acesso restrito a enterprise/parceiros | Sem acesso autorizado gratuito já existente, deixar `SIGHTENGINE_AUDIO_ENABLED=false`. Não pagar nem trocar sinal acústico por palpite do LLM |
| Áudio — Hive | Controle público de voz sintética eSpeak NG, 6,859456 s: upload 200/2,774 s em 08/10, Hive respondeu com sinal 97,4% arredondado. Origem da voz permaneceu não determinada, com um único detector disponível | Uma amostra sintética não homologa fala humana/clonagem nem mede precisão. Sightengine voz desabilitado; transcrição é tarefa distinta | Manter saldo/modalidade/reserva autorizados, sem recarga automática. Ensaiar voz humana autorizada e corpus independente; transcrição não substitui detector |
| Vídeo | Validação de bytes, extração de quadros e separação áudio/visual testadas offline | Amostras de quadros não cobrem o vídeo todo, lip-sync ou identidade; vídeos humanos autorizados ainda faltam | Ensaiar vídeo sem fala e vídeo com voz fora do quadro; distinguir resultados visuais/acústicos. `VIDEO_MAX_FRAMES=9` aumenta cobertura/custo, não certifica origem |
| Busca reversa — SerpAPI/Lens | Usuário confirmou chave rotacionada local/Railway; chave anterior autenticou em etapa histórica. Fluxo reverso atual não homologado | **Upload privado retorna `skipped` por projeto**, pois Lens precisa URL pública/ação explícita. Preencher chave não ativa essa busca | Validar desenho de busca pública com URL autorizada e contrato do provedor; nunca publicar upload privado automaticamente. Sem busca realizada, não declarar “zero correspondências” |
| TinEye / Wayback | Tratamento de falhas melhorado/testado offline; integrações reais ainda não homologadas nesta revisão | TinEye API não equivale ao site gratuito; registro Wayback não prova primeira publicação/descontextualização | Só ativar TinEye com contrato/crédito autorizados. Ensaiar URL pública Wayback; erro, consulta vazia e resultado encontrado devem permanecer diferentes |
| EXIF / SHA-256 / C2PA | Extração/comparação e regras testadas; confiança/voto C2PA desabilitados no runtime | EXIF pode mudar; hash comprova bytes relacionados, não verdade. C2PA exige binário/trust/corpus validados | Confirmar ferramentas na imagem final; explicar os limites. Não habilitar voto C2PA só porque há variável/âncoras presentes |
| TTS educativo Gemini | Formato WAV/PCM e ausência de beep falso corrigidos, 29 regressões de formato | Fidelidade/voz real do modelo TTS atual ainda não homologadas | Confirmar `GEMINI_TTS_MODEL` disponível e áudio audível; apresentar como voz gerada, não pessoa real nem resultado de detecção |
| WhatsApp | Simulador/webhook/parser/segurança testados localmente | Simulação não é envio real ao WhatsApp; gateway/entrega real pendentes | Separar demo de integração real. Habilitar webhook só com segredo/gateway e testar entrega autenticada sem dados pessoais |

Opcional: `GPTZERO_API_KEY` é autoria de texto, não verdade; contrato/idioma reais ainda precisam validação. `HIVE_TEXT_API_KEY` é camada legada, não checagem principal. `VIRUSTOTAL_API_KEY` está no roadmap, não no pipeline atual. Conseguir mais chaves não resolve automaticamente essas lacunas.

## 3. Por que há chave no `.env`, mas a camada não funciona?

1. **Arquivo local não é Railway.** O processo publicado só recebe as variáveis do serviço/ambiente aplicado. Alteração pendente no painel ainda não vale no deploy.
2. **Modelo/projeto errado.** Permissão de imagem não é áudio; Hive v2 não é v3; token Hugging Face não publica detector.
3. **Acesso negado ou saldo/quota.** 401/403/402/429 não significam conteúdo falso. Modelo listado no catálogo não garante geração naquela modalidade.
4. **Modalidade/formato incompatíveis.** Modelo textual pode não receber imagem, áudio ou JSON completo exigido pela aplicação.
5. **Serviço indisponível.** 503/timeout deve reduzir cobertura. Não inventar resultado, aumentar espera indefinidamente ou repetir até conseguir rótulo desejado.
6. **Camada deliberadamente desligada.** Hive v3/modalidades pagas, áudio Sightengine, HF experimental e busca reversa privada têm guardas intencionais.
7. **Binário faltando.** Variável `EXIFTOOL_ENABLED`/`LOCAL_OCR_ENABLED` não instala ExifTool/Tesseract/idiomas.
8. **Resultado correto sem conclusão.** A política factual exige fontes correspondentes; resposta de API vazia ou sinal isolado não basta.

`.env.example` é o **template atualizado e sem secrets**; `.env` é configuração privada que pode conservar nomes/opções antigos. Não precisam ser idênticos. Defaults novos do código também não substituem uma variável antiga explícita já definida no Railway.

### Nomes exatos e observações do arquivo privado local

Presença conferida pelo responsável pela auditoria em 07/10, sem imprimir valores; **não houve leitura de secrets por este documento nem confirmação de valores Railway**:

- Chaves de Gemini, OpenRouter, Google Fact Check, Serper, Sightengine, AssemblyAI, Hugging Face e Hive legado tinham valor não vazio.
- `HUGGINGFACE_IMAGE_API_URL` ausente → impede a chamada HF. `HUGGINGFACE_AI_LABEL` ausente → herda `artificial`; isso só serve se for a classe positiva real do modelo escolhido. **Não usar os nomes abreviados `HF_IMAGE_API_URL`/`HF_AI_LABEL`: o código não os lê.**
- `HIVE_API_VERSION` ausente → herda `v2`. `HIVE_V3_API_KEY`, `HIVE_V3_MEDIA_TYPES`, `HIVE_IMAGE_API_KEY`, `HIVE_AUDIO_API_KEY` e `HIVE_DEEPFAKE_API_KEY` ausentes. Se a chave existente veio de **Service API Keys v3**, usar o default v2 é incompatível; tipo da chave não foi revelado/assumido pela auditoria.
- `GEMINI_MEDIA_MODEL_NAME` ausente → herda modelo principal; **não é erro por si só**. `GEMINI_REQUEST_TIMEOUT_SECONDS` ausente → novo código usa 60; não explica sozinho HTTP 503.
- `AUDIO_TRANSCRIPTION_PROVIDER` ausente → preferência Gemini; AssemblyAI continua alternativa se configurado e se o fluxo permitir.
- `SIGHTENGINE_AUDIO_ENABLED` ausente → `false`, proteção intencional contra ativação de modalidade restrita.

Mudanças no template ou commit **não sincronizam secrets** automaticamente. Conferir manualmente os nomes no serviço backend Railway, sem postar prints de valores/chaves.

## 4. Configuração segura por serviço

### Railway: backend `verify`, ambiente `production`

Não importar o `.env` inteiro. Preservar referência privada PostgreSQL, secrets válidos e configuração específica de produção. O Railway exige revisar e aplicar/deployar as mudanças de variáveis. [Variáveis Railway](https://docs.railway.com/variables).

| Categoria | Variáveis usadas pelo código | Ação |
| --- | --- | --- |
| Base | `APP_ENV`, `DATABASE_URL`, `JWT_SECRET`, `HMAC_SECRET_KEY` | Produção, banco Railway e secrets fortes/independentes; não copiar SQLite/senhas QA. Não rotacionar valores válidos sem planejar invalidação |
| Navegador/origem | `COOKIE_SECURE`, `COOKIE_SAME_SITE`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` | HTTPS, `true`/`none` para domínios distintos; origem exata `https://verifybr.vercel.app`. Não liberar `*` |
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `GEMINI_MEDIA_MODEL_NAME`, `GEMINI_REQUEST_TIMEOUT_SECONDS`, `GEMINI_FALLBACK_MODELS`, `GEMINI_TTS_MODEL` | Chave AI Studio correta, modelo disponível, prazo 60 s. Modelo multimodal/TTS precisa ensaio próprio; fallback só explícito/autorizado |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_ENABLED`, `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODELS`, `OPENROUTER_DAILY_LIMIT` | `true`, `openrouter/free`, fallback vazio até validado; limite local 40/dia por processo. A cota real da conta pode ser menor |
| Fact Check/contexto | `GOOGLE_FACT_CHECK_KEY`, `SERPERAPI_KEY`, `SERPAPI_KEY` | Cada chave do seu provedor; Fact Check API habilitada/restrições compatíveis com backend. SerpAPI não ativa upload privado |
| Sightengine | `SIGHTENGINE_API_USER`, `SIGHTENGINE_API_SECRET`, `SIGHTENGINE_AUDIO_ENABLED` | Par de credenciais; áudio `false` sem acesso autorizado ao modelo |
| HF | `HUGGINGFACE_ENABLED`, `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_IMAGE_API_URL`, `HUGGINGFACE_AI_LABEL` | Manter `HUGGINGFACE_ENABLED=false` conforme escolha do usuário; não contratar endpoint nem comprar créditos |
| Hive | `HIVE_API_KEY`, `HIVE_API_VERSION`, `HIVE_V3_API_KEY`, `HIVE_V3_MEDIA_TYPES`, `HIVE_V3_IMAGE_REQUEST_LIMIT`, `HIVE_V3_AUDIO_SECONDS_LIMIT`, `HIVE_IMAGE_API_KEY`, `HIVE_AUDIO_API_KEY`, `HIVE_DEEPFAKE_API_KEY` | Distinguir v2/projeto e v3/Secret Key; saldo existente autorizado. Modalidades vazias ou limites zero impedem envio v3. Exemplos limitados e reinícios/réplicas explicados no guia de ativação |
| ASR | `ASSEMBLYAI_API_KEY`, `AUDIO_TRANSCRIPTION_PROVIDER` | `assemblyai` só quando houver os créditos gratuitos já autorizados; modelo usado pelo cliente: `universal-2`, português |
| Ferramentas | `LOCAL_OCR_ENABLED`, `EXIFTOOL_ENABLED`, `C2PATOOL_ENABLED`, `VIDEO_MAX_FRAMES` | Confirmar instalação real; OCR `true`. C2PA sem confiança/voto homologados. Exemplo de apresentação usa três quadros para limitar custo, com menor cobertura |

Valores públicos seguros de referência para a revisão, **não um arquivo completo para substituir a produção**:

```dotenv
GEMINI_MODEL_NAME=gemini-3.1-flash-lite
GEMINI_REQUEST_TIMEOUT_SECONDS=60
GEMINI_MEDIA_MODEL_NAME=gemini-3.1-flash-lite
GEMINI_FALLBACK_MODELS=
LOCAL_OCR_ENABLED=true
OPENROUTER_ENABLED=true
OPENROUTER_MODEL=openrouter/free
OPENROUTER_FALLBACK_MODELS=
OPENROUTER_DAILY_LIMIT=40
HUGGINGFACE_ENABLED=false
HIVE_API_VERSION=v3
HIVE_V3_MEDIA_TYPES=image,audio
HIVE_V3_IMAGE_REQUEST_LIMIT=20
HIVE_V3_AUDIO_SECONDS_LIMIT=60
VIDEO_MAX_FRAMES=3
SIGHTENGINE_AUDIO_ENABLED=false
```

O template candidato usa Lite principal/mídia porque controles de texto, leitura e inspeção auxiliar responderam. `GEMINI_MEDIA_MODEL_NAME` vazio continua herdando o principal no código; **não homologa fala nem precisão**. Variável antiga explícita do Railway prevalece até ser aplicada uma mudança. Aumentar timeout para 90 deve ser ensaio controlado, não solução presumida para indisponibilidade.

Para Hive, o exemplo positivo só vale com Secret Key v3/saldo existente e revisão aplicada. Padrões do código/template para reservas permanecem zero. São **vinte imagens/quadros e sessenta segundos acumulados por processo**, não teto global em dólares. Reinícios/réplicas podem renovar esses contadores. Nenhuma recarga ou cobrança automática foi autorizada. [Guia específico](ATIVACAO-HIVE-VOZ-2026-10-08.md).

### Vercel: somente frontend

No projeto Vite, `VITE_API_URL` é URL pública da API **sem `/api`**. `VITE_GOOGLE_CLIENT_ID`, quando usado, é identificador público OAuth. Chaves de Gemini, OpenRouter, Hive, HF, ASR, Serper/SerpAPI, banco/JWT/HMAC **não pertencem ao frontend nem a variáveis `VITE_*`**. Variáveis públicas entram no JavaScript entregue ao navegador; alterações de build exigem novo deployment. [Variáveis Vercel](https://vercel.com/docs/environment-variables).

## 5. Onde revisar acesso e obter configuração

Não cadastrar cartão, criar endpoint pago ou comprar créditos para seguir este guia. Conta gratuita não equivale a fornecimento sem limites.

| Serviço | Portal/documentação oficial | O que conferir |
| --- | --- | --- |
| Gemini | [API keys AI Studio](https://aistudio.google.com/apikey), [modelos](https://ai.google.dev/gemini-api/docs/models), [limites](https://ai.google.dev/gemini-api/docs/rate-limits), [erros](https://ai.google.dev/gemini-api/docs/troubleshooting) | Projeto da chave, modalidade, modelo, quota e falha específica. Limites são por projeto/modelo; nova chave no mesmo projeto não cria nova franquia |
| OpenRouter | [API keys](https://openrouter.ai/settings/keys), [catálogo gratuito](https://openrouter.ai/models?max_price=0), [variantes gratuitas](https://openrouter.ai/docs/guides/routing/model-variants/free), [limites](https://openrouter.ai/docs/api/reference/limits) | Variante realmente listada como gratuita, suporte à entrada/formato, quota da conta. Não basta adicionar `:free` a qualquer nome de modelo |
| Fact Check | [Habilitar Fact Check Tools API](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com), [credenciais Google Cloud](https://console.cloud.google.com/apis/credentials), [Claim Search](https://developers.google.com/fact-check/tools/api) | API/chave do projeto e restrições corretas. Busca usa chave; edição de ClaimReview/Search Console é outro produto, não requisito desta busca |
| Serper | [Conta/painel Serper](https://serper.dev/) | Chave existente e saldo; não presumir franquia renovável ilimitada |
| SerpAPI | [Manage API key](https://serpapi.com/manage-api-key), [Google Lens API](https://serpapi.com/google-lens-api) | Nova chave rotacionada, saldo, imagem pública autorizada e fluxo explicitamente implementado |
| Sightengine | [Dashboard](https://dashboard.sightengine.com/), [modelo de fala](https://www-cf.sightengine.com/docs/ai-generated-speech-detection) | Par API user/secret, modelos liberados e saldo. `ai_speech` atualmente é restrito a enterprise/parceiros; chave de imagem não libera essa camada |
| HF | [Access Tokens](https://huggingface.co/settings/tokens), [Inference Providers settings](https://huggingface.co/settings/inference-providers), [classificação de imagem](https://huggingface.co/docs/inference-providers/tasks/image-classification), [preços atuais](https://huggingface.co/docs/inference-providers/pricing) | Token com permissão de inferência, hospedagem do classificador, `label`/`score`, classe de IA e saldo. **Página atual aberta em 08/10 informa que contas gratuitas não recebem créditos mensais**; resultados/snippets antigos citando US$ 0,10 não são garantia atual |
| Hive | [Hive Models](https://thehive.ai/explore), [Service API Keys v3](https://docs.thehive.ai/docs/chat-completions-openai-compatible-llms), [modelo imagem/vídeo/facial](https://docs.thehive.ai/docs/ai-image-and-video-detection) | Secret Key, não Access Key ID; painel/projeto/versão/uso. V3 usa Bearer; v2 usa chave de projeto. Usuário autorizou saldo existente, não recarga automática; usar modalidades e reservas limitadas |
| AssemblyAI | [Dashboard](https://www.assemblyai.com/dashboard/), [criar transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/submit), [consultar transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/get) | Chave, créditos de teste restantes, tarefa pendente e leitura final. Polling de tarefa existente não é nova tarefa; retenção local não apaga arquivo remoto |

Para HF, este cliente aceita HTTPS sem credenciais/query/fragmento em `router.huggingface.co`, `api-inference.huggingface.co` ou subdomínio de `endpoints.huggingface.cloud`. Isso é uma **guarda do código**, não garantia de que cada URL/modelo tenha serviço ativo. Requer retorno de lista `label`/`score` e a classe positiva exata. O exemplo anterior `Ateeqq/ai-vs-human-image-detector` usa `ai`, respondeu, mas errou controles; não é indicação de detector homologado. **Não criar Inference Endpoint dedicado para “resolver a falta de URL”.**

## 6. Evidência local versus produção em 08/10

### Publicação e controles públicos posteriores

- SHA `ef9655ff9d3fa4d350d149cc5b48e44b3611b729` confirmado: Railway `a0e0d2b0-fbf9-4473-9350-eae24d9be5b7` SUCCESS em 16:24:40Z (13:24:40 Brasília); Vercel `dpl_J5zdpkUjexfSMs8xsWTMi7GN9sDm` READY, criação ~16:24:18Z (13:24:18 Brasília). Estados são observações do checkpoint, não disponibilidade permanente.
- Interface pública: texto 200/5,704 s inconclusivo; planta IA 200/40,745 s com indícios de IA; foto NASA zinnia 200/5,320 s inconclusiva. OpenRouter/Serper responderam ao texto; Fact Check sem resultados. Gemini visão respondeu nas imagens. OCR da foto produziu apenas “A”, sem uso para checagem factual.
- Voz sintética pública: `demo-conversa-sintetica.wav`, eSpeak NG/6,859456 s, upload 200/2,774 s às 16:41:58,789Z (13:41:58,789 Brasília). UI pediu conferência da leitura; “Ver só sinais da mídia” preservou a análise sem nova checagem. Texto transcrito disponível, Hive 97,4% arredondado, origem da voz não determinada. O rótulo observado não identifica AssemblyAI versus Gemini; não atribuir o controle a um deles.
- PDF da planta IA: POST 200/25 ms, sem nova análise/consumo dos detectores. Evento de download/arquivo aberto/salvo não confirmado. **HTTP 200 não comprova salvamento.**
- Estimativa nominal de consumo Hive desta rodada pública: duas imagens + voz curta **menos de US$ 0,032**. Não é fatura/saldo observado. Reinícios renovam os contadores por processo; nenhum cartão, recarga ou ativação de Sightengine voz foi efetuado.
- Revisão posterior cba8d3f publicada/rechecada: oito testes de contexto e dois de fragmentos extraídos; **492 backend offline, 156 frontend e build aprovados localmente, zero skips**; três jobs CI aprovados no candidato e em master. Contexto mantém contagens brutas/queries, diferencia ausência de notícia lexicalmente pertinente de indisponibilidade e não altera Fact Check/veredito. OCR curto ganha aviso sem apagar leitura, consultar fatos ou emitir token. Texto público 200/4,924 s sem notícias irrelevantes; demais controles públicos pertencem à base ef9655ff. [Registro completo](PUBLICACAO-2026-10-08.md#7-publicação-da-revisão-posterior-e-rechecagem).

### Checkpoint anterior à promoção — histórico preservado

- Backend final: **482 testes offline aprovados** em SQLite, 9,614 s, incluindo 13 controles de segurança do probe Hive e guarda de leitura excessiva. HTTP real bloqueado; validam código/regras, não disponibilidade/precisão atuais das APIs.
- Frontend final: **155 testes aprovados + build** em 08/10, 698,83 ms; build 1.977 módulos/3,92 s. Inclui proteção de renovação/troca de sessão, visão pública simples, entrada e conferência com limites Unicode sem corte silencioso. Contagens 124, 142, 150 e 154 permanecem históricas; não são percentual de acerto.
- PostgreSQL final: mesmo runner com `--postgres-test-url` explícito concluiu **482 aprovados**, 10,428 s; **quatro testes são integração real PostgreSQL**, incluindo persistência de métricas com datas. O restante usa controles/mocks/SQLite; não afirmar 482 integrações de banco, homologação completa da produção nem 964 casos distintos ao somar as duas execuções. Checkpoint anterior 468/9,247 s permanece histórico.
- Em 08/10, frontend público `https://verifybr.vercel.app` respondeu HTTP 200. O bundle publicado apontou para `https://verify-production-ead7.up.railway.app`.
- O timeout DNS anterior de `/health` é histórico, não evidência de indisponibilidade global. **O conector confirmou backend/PG Railway online** nesta rodada. Logs revelaram três 422 de texto, sem corpo/detalhe para concluir a causa, e um 500 de link causado por tipo de data na persistência. [Separação dos diagnósticos](CORRECOES-PRODUCAO-2026-10-08.md#2-por-que-aparece-não-foi-possível-concluir-a-checagem).
- **Antes da promoção**, `master`/Vercel/Railway publicados permaneciam `5db970d…`; último deployment Railway então confirmado `b34a1f5e`, de 04/10. Candidato `7c6b676` foi enviado na branch `entrega/banca-2026-10-08`, com três jobs CI aprovados. A autorização de promoção estava pendente naquele checkpoint; estado atual está na seção anterior.
- Foram feitas **seis chamadas Gemini reais** em 08/10: três diagnósticas (texto/OCR 3.8 e OCR Lite) e três pela interface Lite isolada (texto e leitura/inspeção da planta IA). O controle Hive de **duas imagens** concluiu com HTTP 200, teto nominal US$ 0,012, sem consulta de saldo/fatura nem homologação de precisão. **Zero envio HF** nesta rodada.
- Modo Fácil e mobile de 375 px foram conferidos na interface isolada sem overflow horizontal. Naquele checkpoint, publicação e limites aguardavam aprovação. Posteriormente o usuário confirmou aplicação das variáveis Railway e a revisão foi publicada; esta documentação não escreve variáveis nem faz deploy.

## 7. Aceite para apresentação e conclusão

Antes de declarar uma modalidade pronta:

1. Publicar/revisar candidato identificado por SHA e confirmar Vercel/Railway/banco/ferramentas corretos.
2. Executar exemplos próprios/autorizados pela **interface desse candidato**, anotando arquivo/hash, data, fornecedores, falhas, leitura original/conferida e relatório exportado.
3. Separar verdade factual, origem da mídia, fala e triagem de golpe. Registrar inconclusivos e erros; não selecionar apenas “acertos bonitos”.
4. Medir falsos positivos/negativos por modalidade com conjunto independente e procedência conhecida. Dois controles ou modelos concordando não estabelecem taxa de acerto.
5. Homologar fala humana (negação, dinheiro, data) e vídeos sem fala/voz fora do quadro. Pasta de entrada autorizada: `/mnt/externo/IMPORTANTES/mostra/arquivos-para-validacao/`; nenhum envio automático.
6. Fechar gates de segurança/publicação no [plano até 11/10](ENTREGA-ATE-11-OUTUBRO.md), incluindo sessão/privacidade, PostgreSQL, imagem Docker final, CI, retenção e recuperação.

Na banca, usar exemplos ensaiados **sem alterar o resultado para combinar com o rótulo esperado**. Se API falhar, mostrar cobertura/limitação e contingência; “não tenho evidência suficiente para concluir” é comportamento defensável, não resultado falso. Não prometer que o sistema certifica pessoas, clonagem de voz, lip-sync ou porcentagem calibrada de verdade.

## 8. Fontes internas usadas

- [Publicação e controles reais posteriores em 08/10](PUBLICACAO-2026-10-08.md).
- [Arquitetura e contratos](general.md).
- [Manual completo](DOCUMENTACAO-COMPLETA.md).
- [Diagnóstico/evidências de APIs de 07/10](FECHAMENTO-2026-10-07.md).
- [Retomada ASR, UI simulada e limites](TRANSCRICAO-PENDENTE-2026-10-07.md).
- [Diagnóstico/correções complementares de 08/10](CORRECOES-PRODUCAO-2026-10-08.md).
- [Ativação limitada Hive/voz e explicação de OCR](ATIVACAO-HIVE-VOZ-2026-10-08.md).
- [Template sem chaves](../backend/.env.example).
- Código consultado: `core/gemini_client.py`, `core/openrouter_service.py`, `core/fact_checker.py`, `core/huggingface_client.py`, `services/hive_service.py`, `services/audio_service.py`, `services/speech_detector.py`, `services/evidence_policy.py`, `services/claim_policy.py`, `services/capabilities.py` e `services/reverse_search_service.py`.

Guias antigos mantêm valor histórico, mas configuração/saldo/modelo descritos neles não confirmam disponibilidade atual. Para estado atual, priorizar este documento e os artefatos datados correspondentes.
