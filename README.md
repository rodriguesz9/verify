# Verify

Aplicação de apoio à checagem de mensagens, links, imagens, áudio e vídeos. Feita para ajudar pessoas a reconhecer sinais de risco e consultar evidências antes de compartilhar ou agir.

Não é uma perícia, um certificado de autenticidade ou uma garantia de detecção de deepfake.

**Revisão de 10/10:** [diagnóstico das análises inconclusivas e correções](docs/INCONCLUSIVOS-2026-10-10.md). Busca prioriza frases literais completas; fontes gerais com trechos recuperados não decidem verdade; sinais isolados, discordância e indisponibilidade de mídia agora têm explicações diferentes. **554 testes backend e 169 frontend passaram localmente; build concluído.** Ver registro para publicação/smoke e pendências; números e configurações de etapas anteriores abaixo são históricos, não validação de precisão universal.

Documentação consolidada em 07/10/2026: [manual completo do projeto](docs/DOCUMENTACAO-COMPLETA.md) · [plano original de 14 dias](docs/PLANO-ENTREGA-14-DIAS.md) · [índice de documentação e evidências](docs/README.md). Inclui arquitetura, API, banco, todas as variáveis suportadas, Docker, APIs, deploy, testes, privacidade, operação, tarefas, responsáveis e critérios de aceite. Em caso de divergência com guias anteriores, conferir o código e o manual atual.

**Código publicado e ensaiado em 08/10 (histórico):** `cba8d3f77cb60ae1906ab1ccb292c77f6f3e7b40`, Vercel READY/Railway SUCCESS. Os commits exclusivos de documentação daquela rodada preservaram esse código; as correções de 10/10 alteraram a implementação e estão no registro atual. [Registro da publicação e limites](docs/PUBLICACAO-2026-10-08.md#7-publicação-da-revisão-posterior-e-rechecagem) · [status por verificação](docs/STATUS-VERIFICACOES-2026-10-08.md). O texto voltou a responder 200/4,924 s, preservou “Não pague” e ficou inconclusivo sem notícias irrelevantes. Na revisão base anterior, imagem conhecida gerada teve indícios de IA com respostas Sightengine/Hive/Gemini; foto NASA permaneceu inconclusiva, não recebeu certificado de autenticidade. PDF respondeu 200 sem refazer detectores, mas salvamento/abertura continuam não validados. Hugging Face desativado; saldo Hive existente autorizado com reservas por processo, não teto financeiro global. **492 backend, 156 frontend e build passaram localmente; os três jobs CI passaram no candidato e em master.**

**Melhorias da revisão publicada:** filtro de contexto Serper exclui notícias sem âncoras literais suficientes ou com negação/valores explícitos divergentes; checagens factuais e votos permanecem intactos. Fragmentos OCR menores que dez caracteres ganham aviso específico, preservando a leitura original, sem busca factual/token de conferência. Correspondência lexical não prova verdade; pode excluir sinônimos/resumos incompletos. Áudio sintético de 6,86 s respondeu 200/2,774 s na revisão base, transcrição disponível e sinal Hive de 97,4% arredondado; origem da voz permaneceu não determinada, Sightengine voz desabilitado. Fala/vídeos humanos e benchmark independente não foram certificados.

**Checkpoint anterior de 08/10, preservado como histórico:** [incidentes de produção e correções verificadas](docs/CORRECOES-PRODUCAO-2026-10-08.md) · [ativação do Hive e situação da detecção de voz](docs/ATIVACAO-HIVE-VOZ-2026-10-08.md). Antes da promoção, produção ainda usava `5db970d` de 04/10. Os controles isolados confirmaram leitura/inspeção Lite e duas respostas Hive de imagem; não homologaram todas as modalidades nem mediram precisão.

Prazo antecipado em 07/10: [fechamento até 11/10/2026](docs/ENTREGA-ATE-11-OUTUBRO.md), com prioridades, critérios de publicação e limitações do perfil gratuito. [Evidências desta rodada](docs/FECHAMENTO-2026-10-07.md). Não confundir a revisão local com a versão publicada.

Revisão de entrega em `entrega/banca-2026-10-08`: [registro do candidato](docs/ENTREGA-BANCA-2026-10-08.md), [status e configuração das verificações](docs/STATUS-VERIFICACOES-2026-10-08.md), [roteiro da banca](docs/ROTEIRO-BANCA.md). **424 testes backend e 142 frontend passaram em 08/10; build concluído.** A execução PostgreSQL anterior repetiu os mesmos 424, não 848 testes distintos; somente três são integração real PostgreSQL, os demais usam SQLite/mocks. A renovação de sessão não reenvia POST/FormData automaticamente; troca de contexto impede retry/logout antigos. Pedidos já enviados e cookies tardios exigem homologação adicional. [Retomada privada de transcrição](docs/TRANSCRICAO-PENDENTE-2026-10-07.md): mesma conta/aba e arquivo não criam outro job durante a janela local; UI simulada observou 1 upload, 1 criação, 2 consultas. Não garante retomada após reinício/réplicas/perda de contexto e não homologa fala. Gemini 3.8 respondeu ao controle de texto, mas OCR/inspeção retornaram 503; OCR local e conferência passaram pela interface. OpenRouter auxilia texto, OCR remoto segue não homologado. Matriz anterior: 22 casos parcialmente executados e 8 pendentes, não 22 vereditos corretos. Push de candidato não comprova deploy; testes funcionais não garantem precisão universal.

Guias novos: [configurar APIs sem novas contratações](docs/APIS-SEM-CUSTO.md) · [ativar Hugging Face, Hive e Gemini; situação do OpenRouter](docs/ATIVAR-DETECTORES.md) · [landing, Modo Fácil e testes visuais](docs/INTERFACE-MODO-FACIL.md).

Nova integração: OpenRouter com **modelos gratuitos e preço máximo zero**, extração literal e OCR alternativo; Hive **v3** com detecção combinada em uma chamada; transcrição AssemblyAI com modelo explícito e polling corrigido. Resultados e pendências em [INTEGRACOES-GRATUITAS.md](docs/INTEGRACOES-GRATUITAS.md). Teste real Hive de imagem passou; não equivale a validar todas as modalidades ou precisão universal.

Última revisão multimodal: **OCR local gratuito, AssemblyAI preferido para fala, bloqueio de silêncio e amostras portuguesas declaradamente sintéticas**. HF compartilhado respondeu, mas errou um controle: fica experimental, sem decidir o veredito. Testes reais, configuração e limites em [MULTIMODAL-2026-10-03.md](docs/MULTIMODAL-2026-10-03.md).

Primeira etapa do [plano de entrega em 14 dias](docs/PLANO-ENTREGA-14-DIAS.md): histórico paginado com busca completa, remoção do cache persistente de consultas e PDF da análise original. Mudanças **locais, ainda não implantadas**; funcionamento, reprodução dos testes e pendências em [PRIMEIRA-ETAPA-2026-10-03.md](docs/PRIMEIRA-ETAPA-2026-10-03.md).

Primeira bateria de 04/10: testes pela interface de texto/link/imagem/áudio/vídeo, correções de OCR/transcrição, falso alerta de domínio e upload WebM. [Resultados, falhas reais e limites por API](docs/VALIDACAO-INTERFACE-2026-10-04.md). Naquela bateria, 223 testes backend e 71 frontend passaram; isso não certifica precisão dos detectores nem implantação. A matriz tinha 20 controles executados parcialmente e 10 pendentes.

Continuação: [conferência do texto antes da checagem](docs/CONFERENCIA-TEXTO-2026-10-04.md). Na revisão local, `/app` permite corrigir OCR/transcrição e gera uma nova análise textual com a leitura original preservada; não altera nem repete os detectores da mídia. Exige `HMAC_SECRET_KEY` forte/estável em produção para vincular a origem. Ainda sem commit/push/deploy.

Etapa seguinte: [PDF, saúde do banco e CI](docs/PDF-READINESS-CI-2026-10-04.md). PDF distingue pontuação ausente de zero; `/ready` verifica conectividade do banco; runner offline e workflow de testes/build preparados sem credenciais de provedores. 256 testes backend passaram no Docker/Python 3.11 com SQLite e no Python 3.12 com PostgreSQL descartável; 79 frontend e build passaram. Execução remota do workflow e deploy ainda pendentes.

Continuação de extração: [HTML, OCR degradado e vídeo com áudio](docs/CONTROLES-EXTRACAO-2026-10-04.md). Corrigidos título de artigo apagado/texto oculto incluído e perda dos motivos de indisponibilidade em vídeos. **265 testes backend, 82 frontend e build passaram**. Controles locais: 18/19 cumpriram a comparação estrita; OCR05 alterou apenas “Valor” para “valor”, diferença mantida no registro. A matriz agora tem **22 casos executados parcialmente e 8 pendentes**, não 22 acertos de classificação. UI/histórico validados em ambiente descartável sem APIs; nenhuma homologação nova de provedor ou deploy.

Continuação de relatórios: [PDF para texto, links e texto conferido](docs/PDF-TEXTO-LINK-2026-10-04.md). Exporta a análise original, incluindo entrada, texto da página efetivamente analisado, avaliações/fontes/limitações e procedência da conferência humana quando houver. **274 testes backend, 84 frontend e build passaram**. Interface → API de exportação respondeu PDF/200 em texto, link e link reaberto do histórico; registros originais permaneceram idênticos. O navegador integrado não confirmou o arquivo salvo: essa última fronteira permanece pendente. Sem novas chamadas a APIs, commit/push ou deploy.

## Registro histórico — revisão de 3 de outubro de 2026

A versão publicada foi testada em [verifybr.vercel.app](https://verifybr.vercel.app). Foram encontradas falhas de validação de mídia, erros em texto/WhatsApp e resultados de voz dependentes do nome do arquivo.

A revisão corrige esses comportamentos e separa veracidade da informação da origem da mídia. A publicação foi autorizada via Git; **deploy e provedores devem ser confirmados separadamente**. Consulte o [passo a passo de configuração em produção](docs/CONFIGURACAO-PRODUCAO.md), o [guia de verificações e chaves](docs/VERIFICACOES-2026-10-03.md), o [relatório histórico da auditoria](docs/AUDITORIA-2026-10-02.md) e os resultados reproduzíveis:

- [Produção, antes das correções](docs/audit-production-2026-10-02.json).
- [Fluxos locais corrigidos](docs/audit-local-2026-10-02.json).
- [25 controles HTTP finais desta etapa](docs/audit-verifications-local-2026-10-03.json).
- [Teste limitado com provedores reais](docs/audit-providers-2026-10-02.json).
- [Origem e limites das mídias de teste](backend/tests/fixtures/README.md).

Última execução local da primeira etapa: **212 testes backend + 141 subtestes, 67 testes frontend e 24 controles HTTP aprovados; build da interface concluído**. O registro dos controles está em [release-controls-local-2026-10-03.json](docs/release-controls-local-2026-10-03.json). As verificações visuais estão registradas no documento da etapa. Na execução final houve um aviso de descontinuação do python-jose, não erro; uma execução anterior também avisou sobre AnyIO/Starlette. São testes funcionais, não medição da precisão dos detectores. Um HTTP 200 não significa análise conclusiva. As suítes usam respostas controladas e chaves externas desligadas; testes reais e pendências estão em [MULTIMODAL-2026-10-03.md](docs/MULTIMODAL-2026-10-03.md).

Primeira etapa: a suíte atual também passou com **PostgreSQL 16.13 descartável: 212 testes + 141 subtestes**, sem tocar serviços existentes; contêineres temporários removidos. **Docker da raiz compilou offline** e confirmou API/PDF, FFmpeg/ffprobe, Tesseract português/inglês, ExifTool e ausência de `.env`. O Dockerfile isolado de `backend` não pôde ser concluído sem rede por falta de cache de dependências; **seu build e o deploy novo continuam pendentes**. Na revisão anterior (`5db970d`), a atualização de enum foi repetida e `FALSE` gravado/lido corretamente. Ambos os contextos de build excluem `.env`, bancos locais e caches e respeitam `PORT`. Não houve acesso ao banco de produção, teste pago novo de provedores ou comprovação de precisão.

## O que a aplicação faz

| Entrada | Verificações disponíveis | Limite importante |
| --- | --- | --- |
| Texto | Padrões de risco e checagens atribuídas: duas famílias editoriais distintas com correspondência literal conservadora | LLM não decide verdade; paráfrase, contexto relativo, discordância ou cobertura incompleta ficam inconclusivos |
| Link | Consulta pública limitada com validação DNS/IP/TLS; conteúdo segue a política factual de texto | Não certifica legitimidade nem consulta idade do domínio; bloqueios e limites podem impedir leitura |
| Imagem | Decodificação real, Sightengine/Hive/Hugging Face, metadados, C2PA, OCR e inspeção visual auxiliar | Metadados podem ser forjados; visão de um LLM não é prova de geração por IA |
| Áudio | Transcrição Gemini/AssemblyAI, triagem do discurso, Hive específico e Sightengine `ai_speech` opt-in | Transcrição não prova clonagem; segundo detector exige autorização ao modelo, não só chave |
| Vídeo | Amostragem adaptativa limitada por `VIDEO_MAX_FRAMES` (exemplo econômico: três) e análise separada da faixa de áudio | Não verifica todos os quadros, sincronização labial ou identidade; média temporal não vira consenso |

Outros recursos: login com cookies HTTP-only, histórico autenticado, lotes de texto, PDF do resultado, demonstração educativa e simulador de WhatsApp.

O relatório na interface explica os sinais encontrados, destaca os trechos que acionaram regras e mostra fontes de checagem quando retornadas. Orientações oficiais cadastradas ficam separadas das consultas externas. Vídeos mostram o número de quadros e os tempos amostrados. O indicador animado é **heurístico, não porcentagem de veracidade**: sem evidência, aparece “Não determinado”. A interface usa rolagem nativa personalizada e respeita movimento reduzido.

O registro SHA-256 compara bytes com um registro anterior. Não comprova autoria, captura por câmera, veracidade da cena nem assinatura C2PA.

## Política de resultado

- Falta de evidência, erro de API ou discordância relevante: **inconclusivo**.
- Indícios concordantes de detectores: **resultado parcial**, sujeito a revisão.
- C2PA permanece inspeção sem confiança/voto até homologar CLI, configuração e corpus real; presença de âncoras não certifica validação.
- Ausência de sinais de IA nunca transforma uma mídia em “autêntica”.
- Corroborada/refutada é classificação atribuída às checagens correspondentes; `False` não é sinônimo de `AI_Generated`. OCR/transcrição têm relatório factual separado.
- Pontuações são sinais não calibrados. Não são porcentagens de acerto do Verify.

As políticas experimentais estão em `backend/app/services/evidence_policy.py` e `claim_policy.py`. Limiares precisam de validação com um conjunto rotulado representativo; concordância entre dois serviços ou famílias editoriais não garante independência estatística.

`GET /api/capabilities` informa configuração/ferramentas sem expor chaves nem fazer chamadas pagas. Presença de configuração não comprova acesso ou quota: disponibilidade operacional fica `not_tested`. Para métricas offline com resultados inconclusivos incluídos, use `backend/scripts/evaluate_predictions.py`, seguindo o [formato e plano de avaliação](docs/VERIFICACOES-2026-10-03.md#como-medir-precisão-de-verdade-sem-esconder-inconclusivos).

`GET /health` indica vida do processo. `GET /ready` faz `SELECT 1` com prazo de 2 s e cache/coalescência por 2 s/processo: 200 se o banco responder, 503 se indisponível/timeout, sem detalhes de conexão ou chamadas a provedores. Isso não certifica migrações, gravação, quotas ou precisão. Os `railway.toml` locais apontam para `/ready` no próximo deploy; a configuração remota não foi alterada.

## Arquitetura

- Interface: React, Vite, Tailwind CSS e Lucide.
- API: FastAPI e Pydantic.
- Persistência: SQLAlchemy assíncrono e PostgreSQL; SQLite em testes isolados.
- Mídia: Pillow, FFmpeg/ffprobe; ExifTool e c2patool opcionais.
- Hospedagem: frontend na Vercel, API e banco na Railway.

Uploads e relatórios completos usam o mesmo fluxo de análise de mídia. **PDF reutiliza o relatório original assinado: não reenvia o arquivo nem consulta detectores novamente.** Arquivos aceitos: imagens decodificáveis JPEG/PNG/WebP/GIF, áudio e vídeo suportados pelo servidor. Limites: 25 MiB, 20 megapixels e dois minutos. Imagens animadas têm cobertura limitada ao primeiro quadro.

O histórico usa páginas de 20 itens, busca e filtros em todos os registros da conta, incluindo vídeo. Consultas e resumos não ficam em cache persistente do navegador. O relatório atual fica apenas na sessão da aba, isolado por conta e limpo ao sair/trocar de conta; preferências de acessibilidade permanecem. Isso não substitui a política de retenção/exclusão do banco, ainda pendente.

Exportação de mídia/texto/link: `POST /api/verificar/relatorio-pdf` recebe JSON `{"snapshot_token":"<cópia assinada emitida pelo servidor>"}`. Validade: uma hora; relatórios autenticados exigem a conta original. Abrir um relatório compatível no histórico renova a exportação sem nova análise. Texto/link preservam tipo, entrada original, data/versão e avaliações; link também preserva texto extraído e método. Relatórios antigos sem esses dados continuam indisponíveis: não há reconstrução por consulta nova. Em produção, configure `HMAC_SECRET_KEY` forte e estável; sem isso a exportação fica indisponível. A cópia assinada **não é criptografada**; não compartilhe nem registre seu token. Para anônimos, quem possuir essa cópia pode exportá-la até expirar. A interface informa que o PDF foi preparado, não que o navegador necessariamente salvou o arquivo.

## Executar com Docker

Copie `backend/.env.example` para `backend/.env` e configure o necessário. Não comite esse arquivo.

```bash
docker compose up --build
```

- Interface: http://localhost:5174
- API: http://localhost:8001
- Documentação: http://localhost:8001/docs
- Vida do processo: http://localhost:8001/health
- Conectividade do banco: http://localhost:8001/ready
- PostgreSQL de desenvolvimento: porta 5433

O Compose é para desenvolvimento: possui senhas de exemplo, volumes locais e recarga automática. Não exponha o banco nem use essas senhas em produção. O Dockerfile do backend instala FFmpeg e ExifTool; c2patool exige instalação adicional.

O perfil opcional `whatsapp` não foi certificado de ponta a ponta com um número real. O webhook não envia automaticamente uma mensagem só porque retornou um JSON; integração de transporte, autenticação e provisionamento do gateway ainda precisam de validação.

## Testes reproduzíveis

Dentro de `backend`, com dependências de `requirements.txt`, FFmpeg/ffprobe e Poppler (`pdftotext`/`pdftoppm`) instalados:

```bash
python -B scripts/run_offline_tests.py
```

O runner ignora `.env` e URLs de banco herdadas, gera seus próprios SQLite temporários/segredos e bloqueia HTTP real; falha se houver tentativa inesperada ou teste pulado. A opção `--postgres-test-url` aceita somente PostgreSQL local explicitamente fornecido, sem parâmetros extras, com `test` no nome do banco. Use **somente um banco descartável**: a suíte recria suas tabelas. Não use banco real nem túnel para produção. As credenciais fictícias e os bancos de CI não precisam ser adicionados no Railway/Vercel.

O workflow `.github/workflows/tests.yml` prepara SQLite/PostgreSQL, testes backend, `npm ci`, `npm test` e `npm run build`. Não busca segredos, testa APIs reais ou faz deploy. Antes de tratá-lo como bloqueio de publicação, executar no GitHub e exigir os checks nas regras da branch/integrações de deploy. [Reprodução e limites](docs/PDF-READINESS-CI-2026-10-04.md).

Compilação da interface:

```bash
cd frontend
npm run build
```

Os testes de explicações, fontes e limites da animação ficam em `frontend/tests`: execute `npm test`. O controle visual `/tests/score-preview.html` é servido apenas pelo Vite de desenvolvimento; não é rota de análise da aplicação publicada.

Controles locais adicionais do webhook: `backend/scripts/security_probe.py`. Ele aceita apenas localhost e lê o segredo de teste de `VERIFY_AUDIT_WEBHOOK_SECRET`; mantenha-o fora de logs. Esses controles podem consumir provedores se você não os desabilitar no servidor de teste.

Com uma API local iniciada e banco descartável:

O probe envia controles em sequência. Somente nesse servidor descartável, aumente `ANALYSIS_REQUESTS_PER_MINUTE` para 200 e `ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE` para 400 antes de iniciá-lo, para não confundir limites 429 com falhas de fluxo. Não use esses valores para liberar produção; os limitadores têm testes independentes na suíte. Desabilite as chaves externas se não quiser consumir créditos.

```bash
PYTHONPATH=backend backend/venv/bin/python backend/scripts/audit_probe.py \
  --base-url http://127.0.0.1:8012 --local-auth --output docs/audit-local.json
```

`--local-auth` cria dados de teste e só aceita localhost. Sem essa opção, o script não cria contas. Os controles de mídia ainda podem consumir operações dos provedores configurados.

Teste real opcional e limitado de provedores:

```bash
PYTHONPATH=backend backend/venv/bin/python backend/scripts/provider_probe.py \
  --env-file backend/.env --output docs/audit-providers.json
```

Acrescente `--tts` para uma chamada de geração de fala. Isso pode consumir quota/créditos; os arquivos enviados são os controles fictícios do repositório.

## Chaves e configuração

As chaves de fornecedores ficam **no backend/Railway**, nunca em variáveis `VITE_*` públicas.

| Serviço | Onde obter | Variáveis |
| --- | --- | --- |
| Gemini | [Google AI Studio](https://aistudio.google.com/app/apikey) · [documentação](https://ai.google.dev/gemini-api/docs/api-key) | `GEMINI_API_KEY`, modelo explícito em `GEMINI_MODEL_NAME` |
| Sightengine | [Painel](https://dashboard.sightengine.com/) · [imagem](https://sightengine.com/docs/ai-generated-image-detection) · [fala sintética](https://sightengine.com/docs/ai-generated-speech-detection) | `SIGHTENGINE_API_USER`, `SIGHTENGINE_API_SECRET`; áudio só com acesso ao modelo e `SIGHTENGINE_AUDIO_ENABLED=true` |
| Hive | [Portal](https://portal.thehive.ai/) · [autenticação](https://docs.thehive.ai/reference/authentication) | `HIVE_IMAGE_API_KEY`, `HIVE_DEEPFAKE_API_KEY`, `HIVE_AUDIO_API_KEY`, `HIVE_TEXT_API_KEY`; `HIVE_API_KEY` é compatibilidade |
| Hugging Face experimental | [Tokens](https://huggingface.co/settings/tokens) · [inferência compartilhada](https://huggingface.co/docs/inference-providers/main/pricing) | `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_IMAGE_API_URL`, `HUGGINGFACE_AI_LABEL`; sem voto, sem contratar GPU |
| AssemblyAI | [Painel](https://www.assemblyai.com/dashboard/) · [transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/getting-started/transcribe-an-audio-file) | `ASSEMBLYAI_API_KEY` — alternativa de transcrição, não detector de clonagem |
| Google Fact Check | [Console Google Cloud](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com) · [documentação](https://developers.google.com/fact-check/tools/api/reference/rest/) | `GOOGLE_FACT_CHECK_KEY` |
| Serper | [Serper](https://serper.dev/) | `SERPERAPI_KEY` |
| SerpApi | [Chave](https://serpapi.com/manage-api-key) · [Lens](https://serpapi.com/google-lens-api) | `SERPAPI_KEY` |
| OpenRouter gratuito | [Chaves](https://openrouter.ai/settings/keys) · [free router](https://openrouter.ai/openrouter/free) | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL=openrouter/free`; auxilia busca/OCR, não decide veracidade |

Hive v2 exige chave do projeto/modelo apropriado: chave de imagem não habilita automaticamente manipulação facial, áudio ou texto; chaves v3 não são intercambiáveis com v2. Duas chamadas Hive não contam como dois detectores independentes. HF exige endpoint hospedado oficial explicitamente configurado e classe positiva documentada, não apenas um token. Sightengine `ai_speech` tem acesso enterprise/parceiro; mantenha desligado sem autorização e confirme preço/acesso antes de contratar.

Hive v3 usa `HIVE_API_VERSION=v3`, `HIVE_V3_API_KEY` (ou `HIVE_API_KEY` existente) e `HIVE_V3_MEDIA_TYPES` para autorizar explicitamente chamadas pagas. Vazio = pausado. Imagem/deepfake compartilham uma chamada; áudio usa `ai_generated_audio`, não o score visual. O teto de US$ 0,01 foi autorização de um teste, não gasto contínuo em produção.

AssemblyAI e GPTZero são integrações opcionais/alternativas; VirusTotal permanece roadmap. ExifTool, FFmpeg, SHA-256 e Wayback não exigem chave comercial. Não é necessário contratar todos os serviços para iniciar — porém, sem detectores disponíveis, mídia deve continuar inconclusiva.

`JWT_SECRET` e `HMAC_SECRET_KEY` são segredos aleatórios próprios, não chaves compradas. Gere valores fortes e independentes. `GOOGLE_CLIENT_ID` é um cliente OAuth, não uma chave de detecção.

## Proteções e limites desta revisão

- URLs: validação de endereços públicos e conexão ao IP validado, mantendo a verificação TLS do domínio original. Cada redirecionamento é revalidado; somente portas 80/443, sem credenciais ou proxy do ambiente. Páginas: até 2 MiB, cinco redirecionamentos e 20 segundos totais. Respostas comprimidas são recusadas; alguns sites exigirão outro meio de envio.
- Downloads de mídia: até 25 MiB, 20 segundos totais e sem redirecionamento. Bytes são validados antes da análise.
- Análises públicas: 10 solicitações/minuto por IP, 60/minuto globais e quatro simultâneas por processo; no máximo duas simultâneas por IP. Login conserva o limite próprio de cinco tentativas a cada 15 minutos; cadastro/Google também entram no controle de admissão.
- Envio: até 35 MiB por requisição completa, 64 KiB em autenticação e 15 segundos para receber o corpo. Lotes contam como uma solicitação, mas podem chamar vários provedores: estes limites **não garantem um orçamento financeiro máximo**.
- Origens: configure `CORS_ORIGINS` com domínios exatos. `*` não autoriza automaticamente todos os sites Vercel. Escritas de navegador vindas de origem não autorizada são recusadas antes do processamento.
- JWT: em `APP_ENV=production`, segredo ausente/curto/padrão impede iniciar. Em desenvolvimento sem segredo, a chave é efêmera e sessões expiram ao reiniciar.

Os limites e a deduplicação do webhook são em memória, **por processo**. Antes de várias réplicas/workers, use Redis ou outro mecanismo compartilhado e ajuste os IPs de proxies confiáveis no servidor. Não habilite confiança em cabeçalhos encaminhados por qualquer cliente. Retenção/exclusão de dados, fila de tarefas e auditoria de dependências continuam pendentes.

### WhatsApp: configuração obrigatória

`WHATSAPP_BOT_ENABLED=true` exige `WHATSAPP_WEBHOOK_SECRET` com pelo menos 32 caracteres. O gateway deve enviar esse mesmo segredo no header `X-Verify-Webhook-Secret`, por HTTPS. Não coloque segredo na URL, frontend ou logs.

São ignoradas mensagens `fromMe=true` e eventos diferentes de `messages.upsert`. IDs repetidos são suprimidos por dez minutos em um único processo; isso não garante entrega exatamente uma vez. Mídia em base64 é decodificada e validada; áudio/imagem/vídeo usam o mesmo fluxo. URLs nativas do WhatsApp podem conter conteúdo criptografado: forneça bytes já descriptografados pelo gateway.

Histórico de WhatsApp fica desligado por padrão. Ativar exige `WHATSAPP_HISTORY_ENABLED=true` e `WHATSAPP_HASH_SECRET` independente. O telefone recebe HMAC, mas mensagens ainda podem identificar pessoas: é **pseudonimização, não anonimização**. Simulações não são salvas como conversas reais.

O webhook apenas retorna JSON. Configure e teste o encaminhamento de `reply` e `audio_reply` ao gateway. O Compose opcional não faz esse transporte nem configura headers automaticamente: a configuração global sem autenticação será recusada.

## Antes de publicar esta revisão

1. Revisar o diff, preservar as mudanças locais existentes e executar a suíte novamente.
2. Railway: usar a pasta raiz `backend` e conferir o builder Dockerfile. O deploy auditado usava Railpack; o arquivo local não prova que o serviço adotou a configuração.
3. Confirmar FFmpeg/ffprobe no ambiente implantado, banco/migrações, segredos, limites de custo e disponibilidade dos provedores.
4. Vercel: raiz `frontend`, build `npm run build`, saída `dist`; configurar `VITE_API_URL` com a URL pública da API, sem o sufixo `/api`, conforme `frontend/src/services/api.js`.
5. Configurar origens CORS **exatas**, cookies HTTPS e testar login no navegador real. Cookies entre domínios podem sofrer bloqueios de terceiros.
6. Publicar e repetir os controles no serviço público. Não usar relatórios antigos do cache como se fossem resultados da política nova.
7. Conferir as configurações novas acima, limites compartilhados/custo e integração autenticada do gateway; implementar retenção/exclusão de dados.

Os relatórios de auditoria registram o estado anterior ao push. Publicação no Git não certifica implantação, validade das chaves ou precisão em produção. Confira commit/status do deploy e as pendências no [guia de produção](docs/CONFIGURACAO-PRODUCAO.md).
