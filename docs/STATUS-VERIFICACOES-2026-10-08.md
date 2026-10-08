# Verify — o que funciona, o que falta e como configurar

Atualização: **8 de outubro de 2026**, horário de Brasília. Este documento descreve a revisão local e as evidências disponíveis; não certifica que ela esteja publicada no Vercel/Railway.

**Resposta curta: não, todas as verificações ainda não estão homologadas.** Há caminhos funcionais, serviços com resposta real e regressões automatizadas aprovadas. Ainda faltam disponibilidade multimodal do Gemini, avaliação independente de precisão, fala/vídeos humanos autorizados e validação integral do candidato em produção. Nenhuma chave ou combinação de APIs garante vereditos 100% certos.

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

As respostas externas abaixo são as últimas observações disponíveis, principalmente de **07/10**, não novos testes de todas as APIs em 08/10. Onde o registro anterior é apenas narrativo, isso está indicado em [fechamento de 07/10](FECHAMENTO-2026-10-07.md#4-outras-observações-de-apis-nesta-sessão).

| Verificação/camada | Última evidência | Por que ainda não está totalmente validada | Como avançar sem inventar resultados |
| --- | --- | --- | --- |
| Texto — Google Fact Check | Três consultas HTTP 200 em 07/10, sem checagens correspondentes | A API recupera checagens existentes; não pesquisa a verdade de qualquer frase. Sem correspondência suficiente, a política não conclui | Confirmar projeto/API/chave; ensaiar afirmações com checagens reais de duas famílias editoriais, mesmo conteúdo/contexto/data. Ausência de resultado continua inconclusiva |
| Texto — Gemini | `gemini-3.8-flash` respondeu HTTP 200/STOP ao controle mínimo de JSON em 07/10 | Um controle mínimo não homologa extração de textos longos nem veracidade | Conferir modelo/quota na conta; validar extração literal, negações, datas e valores. Gemini auxilia leitura/pesquisa, não vota “verdadeiro/falso” |
| Texto — OpenRouter gratuito | Controle respondeu com `liquid/lfm-2.5-2.6b:free` em 07/10 | Modelos gratuitos/capacidade mudam; saída estruturada pode não ser compatível. Sucesso não o torna detector factual | Manter `openrouter/free` ou modelo explicitamente `:free`, preço máximo zero e limites. Ensaiar preservação literal; indisponibilidade deve aparecer no relatório |
| Contexto — Serper | Duas consultas HTTP 200 em 07/10 | Notícias relacionadas não são checagens da mesma afirmação; franquia disponível precisa ser conferida | Usar `SERPERAPI_KEY` do próprio Serper, acompanhar saldo. Não confundir com SerpAPI nem promover contexto a prova |
| Links públicos | Extração/limites/segurança testados offline e em controles locais anteriores | Não certifica o site inteiro, páginas dependentes de JavaScript nem todas as condições HTTPS no deploy | Ensaiar URL pública autorizada no candidato; conferir texto extraído, fonte e truncamento. Depois aplicar a mesma política factual do texto |
| Imagem — OCR local | Tesseract leu controle impresso pela interface em 07/10, preservando negação, R$ 123,45 e data | Um impresso limpo não mede todos os prints, manuscritos ou imagens degradadas | Instalar binário + idiomas `por`/`eng` na imagem final; manter `LOCAL_OCR_ENABLED=true` e conferência humana antes de checar o texto |
| Imagem — Gemini OCR/inspeção | OCR e inspeção pela UI retornaram HTTP 503 em 07/10; 3.7 também falhou | Houve indisponibilidade do fornecedor. Chave/catalogação funcionais não asseguram geração multimodal. Não há prova de que trocar só a chave resolva | Confirmar acesso, modelo e quota; testar modelo multimodal disponível com teto novo de chamadas. Deadline já corrigido para 60 s, configurável até 90; esperar mais não resolve um 503 rápido |
| Imagem — OpenRouter OCR | Tentativas anteriores tiveram HTTP 404/resposta incompleta | Não havia resposta de visão/OCR utilizável; texto funcionando não valida imagem | Só configurar variante gratuita realmente compatível com imagem + formato exigido. Não ativar fallback pago; manter Tesseract/conferência como contingência |
| Imagem — Sightengine | Foto publicada: sinal de IA 0.001; imagem conhecida gerada: 0.99 em 07/10 | Dois controles não são benchmark. Face-swap/transformações não homologados; um único fornecedor não dá consenso | Conferir acesso aos modelos `genai,deepfake`, créditos gratuitos e exemplos independentes. Pontuação é sinal; cobertura insuficiente continua inconclusiva |
| Imagem — Hugging Face | Dois uploads HTTP 200; detector experimental já errou controles conhecidos | Token não provisiona modelo hospedado. Endpoint/classe positiva precisam corresponder ao modelo. **Sem elegibilidade de voto**, inclusive vídeo | Configurar somente endpoint oficial existente, compatível e autorizado; classe positiva exata. Avaliar corpus independente antes de qualquer promoção. Não inverter classes para “acertar” dois exemplos |
| Imagem/facial — Hive v3 | Um smoke de imagem respondeu anteriormente; nenhuma nova chamada nesta rodada | API tem custo. Autorização de até US$ 0,01 era apenas para o smoke já realizado; não autoriza tráfego contínuo. Não homologou face-swap/áudio | Manter modalidades v3 vazias/pausadas. Para novo teste, confirmar Secret Key v3, modalidade, saldo e novo teto explícito; depois avaliar controles independentes |
| Hive v2 por projeto | Cliente e parsing cobertos por testes; projetos específicos não homologados nesta etapa | Chave de projeto de imagem não é automaticamente projeto de áudio/facial/texto; chave v3 não é chave v2 | Conferir versão e projeto no painel. Usar nomes específicos. Não contratar novos projetos apenas para preencher o template |
| Áudio — AssemblyAI | Transcrição de voz sintética já respondeu, mas houve erro “Pix urgente” → “pic surgente”; fala humana ainda pendente | Reconhecimento pode perder palavra/negação/valor/data. Retomada de tarefa foi testada com transporte simulado, não nova voz reconhecida | Se houver créditos gratuitos autorizados, preferir `AUDIO_TRANSCRIPTION_PROVIDER=assemblyai`; subir gravações humanas sem dados pessoais e conferir a leitura na UI |
| Áudio — retomada AssemblyAI | Ensaio local 07/10: duas tentativas, um upload/uma criação/duas consultas simuladas | Cache por processo/sessão tem janela limitada; reinício, réplica, expiração ou perda de contexto não têm garantia durável | Evitar reenviar repetidamente. Resultado pendente não vira “sem fala”; concluir checkpoint compartilhado para escala. [Limites/testes](TRANSCRICAO-PENDENTE-2026-10-07.md) |
| Áudio — Gemini transcrição | Não há homologação atual em fala humana após as falhas multimodais | Texto mínimo bem-sucedido não valida fala; transcrição não autentica voz | Modelo multimodal separado, prazo/quota e teste humano autorizado. Não usar transcrição como detector de clonagem |
| Áudio — Sightengine `ai_speech` | Cliente testado offline; acesso real ao modelo não comprovado | Chaves de imagem não liberam esse modelo. Documentação atual informa acesso restrito a enterprise/parceiros | Sem acesso autorizado gratuito já existente, deixar `SIGHTENGINE_AUDIO_ENABLED=false`. Não pagar nem trocar sinal acústico por palpite do LLM |
| Áudio — Hive | Cliente/modalidade previstos; áudio real não homologado | Cabeça de áudio/projeto e autorização de custo distintos | Não ativar uso pago automático. Transcrição funcional não substitui este detector |
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
| HF | `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_IMAGE_API_URL`, `HUGGINGFACE_AI_LABEL` | Endpoint existente, HTTPS oficial, classe positiva real e saldo autorizado. Continua experimental sem voto |
| Hive | `HIVE_API_KEY`, `HIVE_API_VERSION`, `HIVE_V3_API_KEY`, `HIVE_V3_MEDIA_TYPES`, `HIVE_IMAGE_API_KEY`, `HIVE_AUDIO_API_KEY`, `HIVE_DEEPFAKE_API_KEY` | Distinguir v2/projeto e v3/Secret Key. `HIVE_V3_MEDIA_TYPES` vazio; não habilitar uso pago nesta orientação |
| ASR | `ASSEMBLYAI_API_KEY`, `AUDIO_TRANSCRIPTION_PROVIDER` | `assemblyai` só quando houver os créditos gratuitos já autorizados; modelo usado pelo cliente: `universal-2`, português |
| Ferramentas | `LOCAL_OCR_ENABLED`, `EXIFTOOL_ENABLED`, `C2PATOOL_ENABLED`, `VIDEO_MAX_FRAMES` | Confirmar instalação real; OCR `true`. C2PA sem confiança/voto homologados. Vídeo 9 quadros padrão |

Valores públicos seguros de referência para a revisão, **não um arquivo completo para substituir a produção**:

```dotenv
GEMINI_MODEL_NAME=gemini-3.8-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=60
GEMINI_MEDIA_MODEL_NAME=
GEMINI_FALLBACK_MODELS=
LOCAL_OCR_ENABLED=true
OPENROUTER_ENABLED=true
OPENROUTER_MODEL=openrouter/free
OPENROUTER_FALLBACK_MODELS=
OPENROUTER_DAILY_LIMIT=40
HIVE_V3_MEDIA_TYPES=
SIGHTENGINE_AUDIO_ENABLED=false
```

`GEMINI_MEDIA_MODEL_NAME` vazio herda o principal, ainda não homologado em OCR/fala. Aumentar timeout para 90 deve ser ensaio controlado, não solução presumida para indisponibilidade.

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
| Hive | [Hive Models](https://thehive.ai/explore), [Service API Keys v3](https://docs.thehive.ai/docs/chat-completions-openai-compatible-llms), [modelo imagem/vídeo/facial](https://docs.thehive.ai/docs/ai-image-and-video-detection) | Secret Key, não Access Key ID; painel/projeto/versão/uso. Orientação de autenticação não homologa o detector. V3 usa Bearer; v2 usa chave de projeto. Sem nova autorização de gasto, manter pausado |
| AssemblyAI | [Dashboard](https://www.assemblyai.com/dashboard/), [criar transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/submit), [consultar transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/get) | Chave, créditos de teste restantes, tarefa pendente e leitura final. Polling de tarefa existente não é nova tarefa; retenção local não apaga arquivo remoto |

Para HF, este cliente aceita HTTPS sem credenciais/query/fragmento em `router.huggingface.co`, `api-inference.huggingface.co` ou subdomínio de `endpoints.huggingface.cloud`. Isso é uma **guarda do código**, não garantia de que cada URL/modelo tenha serviço ativo. Requer retorno de lista `label`/`score` e a classe positiva exata. O exemplo anterior `Ateeqq/ai-vs-human-image-detector` usa `ai`, respondeu, mas errou controles; não é indicação de detector homologado. **Não criar Inference Endpoint dedicado para “resolver a falta de URL”.**

## 6. Evidência local versus produção em 08/10

- Backend: **424 testes offline** reexecutados em 08/10, zero falhas/skips, HTTP real bloqueado. Validam código/regras, não disponibilidade atual das APIs.
- Frontend: **142 testes aprovados + build** em 08/10, incluindo 18 controles novos de renovação/troca de sessão, sem rede. Registro anterior de 124 permanece histórico. [Entrega candidata](ENTREGA-BANCA-2026-10-08.md). Não usar essas contagens como percentual de acerto.
- PostgreSQL: execução anterior no modo PostgreSQL rodou a mesma suíte; **só três testes são integração real PostgreSQL**. Não afirmar homologação completa de todos os fluxos no banco de produção.
- Em 08/10, frontend público `https://verifybr.vercel.app` respondeu HTTP 200. O bundle publicado apontou para `https://verify-production-ead7.up.railway.app`.
- Consultas read-only `/health`, `/ready` e `/api/capabilities` do backend não puderam ser completadas deste ambiente. Controle de `/health`: timeout de resolução DNS após 5 s, HTTP `000`. **Não houve HTTP 5xx observado; isso não prova que o Railway esteja globalmente fora do ar.** A fronteira bloqueada foi resolução/rede.
- Referência remota `master` ainda era `5db970d…` na checagem desta rodada. Commit/push de candidato e implantação precisam ser confirmados separadamente; este documento não afirma que já aconteceram.
- Nenhuma chamada paga ou geração externa foi feita para produzir esta atualização; as observações remotas de conteúdo continuam históricas e identificadas.

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

- [Arquitetura e contratos](general.md).
- [Manual completo](DOCUMENTACAO-COMPLETA.md).
- [Diagnóstico/evidências de APIs de 07/10](FECHAMENTO-2026-10-07.md).
- [Retomada ASR, UI simulada e limites](TRANSCRICAO-PENDENTE-2026-10-07.md).
- [Template sem chaves](../backend/.env.example).
- Código consultado: `core/gemini_client.py`, `core/openrouter_service.py`, `core/fact_checker.py`, `core/huggingface_client.py`, `services/hive_service.py`, `services/audio_service.py`, `services/speech_detector.py`, `services/evidence_policy.py`, `services/claim_policy.py`, `services/capabilities.py` e `services/reverse_search_service.py`.

Guias antigos mantêm valor histórico, mas configuração/saldo/modelo descritos neles não confirmam disponibilidade atual. Para estado atual, priorizar este documento e os artefatos datados correspondentes.
