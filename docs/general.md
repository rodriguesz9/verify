# Verify — estrutura e arquitetura

Continuação de 16/10: [busca neutra/bilíngue, comparação de datas e variações, leitura de contexto e cobertura parcial](CORRECAO-CHECAGEM-2026-10-16.md). Testes offline passaram; os controles reais ainda não homologam a checagem factual. Esta etapa não foi implantada.

Atualização de 13/10: [novo cruzamento de fontes](CRUZAMENTO-FONTES-2026-10-13.md) e [retomada do Railway](REATIVAR-RAILWAY-2026-10-13.md). Fluxo/serviços abaixo incorporam a nova camada; checkpoints de publicação anteriores continuam históricos.

Guia da revisão local, atualizado em 7 de outubro de 2026. Não é prova de implantação. Documentação canônica: [manual completo](DOCUMENTACAO-COMPLETA.md), [fechamento até 11/10](ENTREGA-ATE-11-OUTUBRO.md), [plano original de 14 dias](PLANO-ENTREGA-14-DIAS.md) e [índice de evidências](README.md). Para achados históricos, veja [auditoria](AUDITORIA-2026-10-02.md) e [continuação](CONTINUACAO-2026-10-02.md). Novas regras, configuração e avaliação estão em [verificações](VERIFICACOES-2026-10-03.md).

## Componentes

- `frontend/`: React 18, Vite, Tailwind, Lucide e React Router.
- `backend/app/`: FastAPI, serviços de análise, autenticação e persistência.
- PostgreSQL em produção; SQLite somente para desenvolvimento/testes isolados.
- FFmpeg/ffprobe para validar áudio/vídeo e extrair quadros, Pillow para imagem. ExifTool/c2patool são opcionais e devem informar indisponibilidade quando ausentes.

## Fluxos

Texto/link: entrada limitada → admissão/quota → consulta pública segura (link) → afirmações literais + checagens recuperadas → `claim_policy.py` → quando faltar evidência, corpos recuperados + `source_corroboration.py` → `source_decision.py` → relatório → histórico se autenticado. Modelo auxilia extração/comparação de citações, não decide por conhecimento próprio ou concordância com outra IA.

Integração de 16/10: texto/link/lote e texto conferido ativam `use_detailed_report`. Após a decisão, `report_explanation.py` acrescenta explicação por trecho e referências já aceitas, sem nova chamada de IA ou alteração de veredito. Interface valida o envelope contra as avaliações originais; PDF preserva o contrato. Crédito, testes e bloqueio Railway em [integração do Juan](INTEGRACAO-JUAN-2026-10-16.md).

Links preservam cabeçalhos de artigos, removem scripts/menu/template e atributos explícitos de ocultação antes de selecionar o texto principal. `text/plain` não é interpretado como HTML. `source_extraction` informa método/truncamento; interface explica leitura estática e limite de 5.000 caracteres. Não resolve toda a visibilidade CSS/JavaScript nem certifica o site inteiro. Testes e limites em [controles de extração](CONTROLES-EXTRACAO-2026-10-04.md).

Extração Gemini usa uma chamada estruturada com trechos literais, sem reformulação automática; falha/timeout aparece em `provider_coverage.gemini`, preservando a consulta literal. `/app` pede `review_text=true` no upload: checagem factual aguarda conferência/edição explícita e gera nova análise de texto, sem reescrever a mídia original. Outros clientes mantêm checagem automática anterior. `no_text`/`no_speech` são resultados de leitura, não prova de falsidade. Detalhes e testes em [conferência de texto](CONFERENCIA-TEXTO-2026-10-04.md).

Mídia: limite de bytes → decodificação real/limites de dimensão e duração → `media_analysis.py` → camadas disponíveis → `evidence_policy.py` → relatório original com SHA-256/nome/data → histórico se autenticado → cópia assinada para exportação.

PDF: JSON com `snapshot_token` → assinatura/finalidade/validade/conta → relatório original → renderização textual ou forense. Não recebe mídia nem resultado arbitrário; não chama `analyze_media`, não consome quota diária de análise. Limites de admissão/concorrência, corpo e origem continuam aplicados. Texto/link/lote/texto conferido compatíveis têm exportação; relatórios legados incompatíveis e erros ficam explicitamente sem exportação.

WhatsApp: segredo do webhook → parser de evento → ignorar eventos próprios/duplicados → bytes base64 ou download público limitado → fluxo de texto/mídia → JSON de resposta. Envio efetivo ao número exige gateway/integração adicional.

## API

Todos os routers ficam sob `/api`.

| Router | Rotas principais | Uso |
| --- | --- | --- |
| `auth.py` | `/auth/register`, `/auth/login`, `/auth/google`, `/auth/refresh`, `/auth/logout`, `/auth/me` | Cookies HTTP-only; JWT não é retornado ao JavaScript |
| `check_text.py` | `/check-text`, `/check-text-batch` | Texto e até dez mensagens por lote |
| `check_text.py` | `/check-extracted-text` | Nova checagem do texto conferido; origem assinada, mesma conta, quota textual normal |
| `check_url.py` | `/check-url` | Extrai até 5.000 caracteres de documento público limitado |
| `upload.py` | `/upload` | Imagem, áudio ou vídeo pelo fluxo centralizado |
| `verificacao.py` | `/verificar/completo`, `/verificar/audio-rapido`, `/verificar/relatorio-pdf` | Análise de mídia, conteúdo da fala, exportação |
| `verificacao.py` | `/capturar/selo`, `/verificar/selo` | Registro/comparação de bytes SHA-256; não comprova autenticidade |
| `history.py` | `/history`, `/history/stats`, `/history/{id}` | Consulta restrita ao usuário autenticado |
| `whatsapp.py` | `/whatsapp/webhook`, `/whatsapp/simulate` | Webhook autenticado e demonstração pública limitada |

`/health` é liveness. `/ready` consulta `SELECT 1` com deadline de 2 s, cache curto/coalescência por processo: 200 para conexão utilizável, 503 para falha/timeout, sem mensagens do driver. Não valida schema, escrita ou fornecedores. `/api/capabilities` informa presença de configurações/ferramentas, sem valores de segredos ou chamadas pagas; disponibilidade operacional continua `not_tested`. Lifespan inicializa tabelas e encerra o pool no desligamento. Alterações aditivas de enum (`SCAM`, `FALSE`) existem; precisam de staging PostgreSQL e não substituem migrações completas. Os `railway.toml` locais usam `/ready`, ainda sem implantação desta revisão.

## Serviços importantes

- `core/pipeline.py`: recupera checagens/notícias, registra falhas e passa afirmações literais à política de veracidade. Padrões de golpe não são prova de identidade nem investigação concluída.
- `services/claim_policy.py`: duas famílias editoriais distintas com avaliação explícita, data válida e correspondência exata conservadora; negação/valores/datas preservados. Discordância, contexto relativo e cobertura incompleta impedem aprovação global. Classificação é atribuída às fontes, não garantia de verdade.
- `services/source_corroboration.py`: comparação assistida dos corpos reutilizados, até três documentos/cinco segmentos, citações literais com IDs do servidor, guardas de identidade/negação/datas/valores e dependência editorial. JSON inválido/falha/ambiguidade não vira conclusão. Gemini primário e OpenRouter gratuito alternativo compartilham prazo único de 60 segundos; `SOURCE_CROSSCHECK_PRIMARY_PROVIDER` permite escolher o perfil. Recuperação: primeira leitura de três páginas, no máximo seis tentativas cumulativas em 45 segundos, incluindo falhas; uma busca neutra de identidade/evento pode localizar fontes sem alterar a alegação que recebe o veredito. [Validação atual](VALIDACAO-APIS-2026-10-14.md).
- `services/source_decision.py`: combina evidência documental validada e avaliações editoriais por afirmação; preserva golpe/decisão editorial e não aprova conteúdo sem cobertura. Novo score de compatibilidade não é exibido/calibrado.
- `core/scam_detector.py`: regras de triagem com trechos encontrados. Extensão de domínio isolada não produz veredito de golpe. Referências de orientação são cadastradas, não consultas automáticas.
- `core/gemini_client.py`: cliente assíncrono com modelo explícito e erros; deadline total 60 s, configurável 10–90 via `GEMINI_REQUEST_TIMEOUT_SECONDS`, compartilhado com fallback explícito. Default 3.8 respondeu ao controle de texto, não homologa OCR/fala. Camadas de leitura e interface têm margens coerentes; falha não vira sucesso.
- `core/openrouter_service.py`: somente `openrouter/free`/variantes específicas `:free`, preço máximo zero, limite por processo e pausa após quota. Extrai trechos para pesquisa, faz fallback de OCR e comparação assistida de trechos no novo caminho; não vota por conhecimento próprio sobre verdade/origem.
- `services/local_ocr.py`: Tesseract português/inglês primeiro, com limites de bytes/qualidade/prazo; Gemini/OpenRouter somente quando faltar leitura utilizável. Não certifica origem ou verdade.
- `services/speech_input.py`: normaliza mono 16 kHz e bloqueia quase silêncio antes de transcrição remota; não autentica voz nem identifica toda gravação sem fala.
- `services/audio_service.py`: ordem configurável via `AUDIO_TRANSCRIPTION_PROVIDER`, AssemblyAI `universal-2` preferido nos controles recentes; worker/pedido limitados a 25 s. Gemini usa modelo multimodal separado. Pendência AssemblyAI não dispara fallback naquela passagem; não é detector de clonagem.
- `services/assemblyai_jobs.py` e `transcription_scope.py`: checkpoint privado de ASR por conta/aba/arquivo/projeto/opções; consultas posteriores retomam GET, sem nova criação dentro da janela. 64 registros/8 workers, timers de limpeza e bloqueio de POST ambíguo. Não cobre reinício/réplicas/perda de contexto/expiração, nem outros detectores ou retenção remota. [Limites e evidências](TRANSCRICAO-PENDENTE-2026-10-07.md).
- `core/request_budget.py`: admissão por IP/processo, concorrência e corpo limitado; proteção de origens de escrita.
- `services/public_fetch.py`: valida DNS e conecta ao IP validado com TLS/SNI correto. Revalida redirecionamentos, limita bytes/tempo; não usa proxy do ambiente.
- `services/media_validation.py`: valida bytes reais; 25 MiB, 20 megapixels e 120 segundos. Não confia em nome/extensão/MIME declarado.
- `services/media_analysis.py`: fluxo comum de imagem/áudio/vídeo. Vídeo amostra até nove quadros por padrão, exige concordância no mesmo quadro e analisa áudio em paralelo. OCR/transcrição têm checagem factual separada; não faz perícia temporal completa.
- `services/speech_detector.py`: Sightengine `ai_speech` opt-in com acesso ao modelo; Hive de áudio é outro projeto. Transcrição não comprova clonagem e pontuação máxima de um trecho não se aplica automaticamente ao arquivo inteiro.
- `services/benchmark_metrics.py`: métricas offline por dimensão/modalidade/split, com inconclusivos nos denominadores. Não gera ground truth nem valida precisão sem corpus real independente.
- `services/evidence_policy.py`: cobertura, discordância, limitações e política versionada. Ausência de sinal de IA nunca vira mídia autêntica; resultados sem cobertura são inconclusivos. HF é experimental/sem voto, inclusive no agregado de vídeo; não confundir score retornado com evidência decisiva.
- Vídeos preservam status/motivos de indisponibilidade por fornecedor, contagem de estados por quadro e cobertura parcial. Sucesso apenas do modelo facial conta como cobertura do fornecedor, mas não fabrica sinal de geração por IA. Faixa de áudio presente, transcrição e origem da voz permanecem dimensões distintas na interface.
- `services/c2pa_service.py`: marcador não é assinatura validada; runtime mantém confiança/voto desabilitados até homologar CLI/configuração/corpus, mesmo com âncoras presentes.
- `services/whatsapp_security.py`: autenticação, parser, base64 e deduplicação limitada por processo.
- `services/gemini_service.py`: fala real quando disponível, PCM em WAV. Falha não vira beep apresentado como voz.
- `services/pdf_report_service.py`: PDF do resultado real e suas limitações; ausências são explícitas, zero permanece zero, sinais têm escala 0–1 não calibrada e conteúdo aguardando revisão é identificado. Renderização não altera relatório assinado.
- `services/readiness.py`: conectividade read-only do banco, sem acesso a APIs/segredos na resposta; cache e lock amortizam consultas simultâneas.
- `services/pdf_snapshot.py`: cópia de relatório HMAC, finalidade exclusiva, validade de uma hora e vínculo ao usuário quando autenticado. Em produção exige `HMAC_SECRET_KEY` forte/estável; sem segredo a análise continua, mas exportação fica indisponível. Tokens anônimos são capacidades bearer, assinadas mas não criptografadas, nunca gravadas no banco/logs/JSON técnico copiável. Sem dados originais não fabrica uma cópia legada.
- Texto/link/lote e texto conferido recebem snapshot somente após persistência, quando compatíveis. Preservam `content_type`, `query_input`, `analyzed_at`; link inclui `source_text`, `source_url` e `source_extraction`. PDF textual usa renderer próprio, sem camadas de mídia, SHA de texto apresentado como prova ou percentual de verdade. Conferência humana mantém leitura original e texto confirmado separados. Snapshot remove também `text_review_token`; legado incompleto e erros de lote não recebem exportação. [Registro](PDF-TEXTO-LINK-2026-10-04.md).
- `services/extracted_text_review.py`: procedência assinada da leitura original para nova checagem textual após revisão. Finalidade/chave derivada distintas de PDF/JWT, prazo de 15 minutos, limites de texto/corpo e controle de conta; token só em memória na UI, não no histórico. Confirmação do usuário não comprova fidelidade nem veracidade.

Os clientes Hive, Sightengine e Hugging Face não são intercambiáveis. Hive v2 exige projetos apropriados; Hive v3 usa Secret Key Bearer e `classes[].value`, com cabeça de áudio distinta. Imagem/facial v3 compartilham uma chamada e um fornecedor; ativação de chamadas pagas exige `HIVE_V3_MEDIA_TYPES`. Token HF exige endpoint hospedado oficial explícito e classe positiva documentada. Erros diminuem cobertura, não viram evidência de falsidade.

## Persistência e privacidade

Modelos de usuário, verificação, métricas, registro de integridade e conversas WhatsApp ficam em `models/`.

- Histórico pertence ao usuário autenticado.
- `/history` aplica busca, tipo e veredito na contagem e na consulta paginada, sempre dentro da conta; páginas estáveis por data/ID e até 50 itens. `Text` e `Url` são separados, inclusive registros legados de link. ID inválido retorna 422; registro de outra conta, 404.
- `/history/stats` agrega índice somente de registros `partial` com semântica declarada e índice válido; inconclusivos/legados não versionados são excluídos. Sem base, média é `null`/“Não determinado”, não placeholder 50; zero real é preservado. Não mede precisão ou probabilidade de verdade.
- `privacyStorage.js` remove os caches legados persistentes. Relatório atual usa envelope versionado em `sessionStorage`, até 1 MiB, com dono confirmado e proteção contra respostas de uma sessão anterior; armazenamento bloqueado usa memória temporária. Não apaga preferências nem chaves de outros aplicativos.
- Saída/troca de conta limpa relatório e consultas. Sinal entre abas não contém identidade, conteúdo nem credenciais. Respostas API usam `Cache-Control: no-store`; isso não protege contra extensões, scripts maliciosos ou cópias já exportadas.
- Cache MD5 legado não é reutilizado globalmente no upload. Se reintroduzido, precisa de versão, isolamento/contexto e validade explícitos.
- Registro SHA-256 apenas relaciona bytes a registro anterior. Não é C2PA nem certificado de câmera.
- WhatsApp guarda histórico somente se habilitado e com chave HMAC independente. Hash é pseudônimo; texto pode conter dados pessoais. Simulações não entram no histórico real.
- Não registrar mensagens, parâmetros SQL, credenciais ou URLs sensíveis em logs.
- Exclusão de conta/retenção completa ainda são pendências, não funcionalidades garantidas.

## Interface

Rotas públicas: `/`, `/app`, `/report`, `/demo`, páginas institucionais, login/cadastro. `/dashboard` e `/history` exigem sessão; ambas usam o painel existente.

`src/services/api.js` concentra chamadas e renovação de cookies. `VITE_API_URL` recebe o domínio da API, sem `/api`; se ausente, usa proxy relativo.

Revisão de 08/10: guarda síncrona de conta/época; refresh não repete POST/FormData, leitura só repete no mesmo contexto e erro/logout antigos não encerram conta nova. Login/cadastro/Google invalidam contexto antes de mudar cookies. Não resolve pedidos já enviados, cookies tardios entre abas ou revogação; [evidências e limites](ENTREGA-BANCA-2026-10-08.md).

`hooks/authContext.js` fornece o contexto/hook compartilhado; `hooks/useAuth.jsx` exporta somente o provider de componente, mantendo a fronteira de Fast Refresh estável.

Relatório usa `components/report/EvidenceExplanation.jsx` e `AnimatedScore.jsx`. Fontes recuperadas e orientações cadastradas são separadas. Indicador não é porcentagem de acerto/veracidade. Inconclusivo não recebe valor inventado. Animação tem cancelamento e movimento reduzido; rolagem nativa é personalizada em `index.css`.

Landing mantém os destaques azul/ciano em variáveis `--brand-*`, sem mudar cores semânticas dos resultados. Testes de paleta e contraste estão em `landingTheme.test.js`; a configuração de fornecedores sem novas contratações está em [APIS-SEM-CUSTO.md](APIS-SEM-CUSTO.md).

Contrato atual separa `veracity_status` de `authenticity_status`, inclui `claim_assessments` e `content_analysis`. `False` é refutação atribuída, não mídia gerada por IA. O índice legado usa `score_semantics=legacy_decision_index_not_probability`; listas mostram índice/100 e deixam inconclusivos sem índice, não como precisão.

Decisões documentais acrescentam `source_corroboration`, `veracity_decision_basis`, cobertura completa explícita e `score_semantics=not_calibrated_source_corroboration`: pontuação não aparece no relatório/histórico/estatísticas. PDF preserva a camada, inclusive trechos insuficientes e exclusões, sem nova consulta. Corpos internos `_documents` nunca entram no relatório/snapshot. Checagem automática de OCR/ASR sem conferência desliga comparação e busca adicional; texto conferido usa o novo pipeline.

`utils/reportEvidence.js` normaliza dados, limita índices e bloqueia protocolos perigosos em links de referência. Testes do utilitário ficam em `frontend/tests/`. `score-preview.html` é controle visual do Vite, não resultado/rota publicada.

## Testes e publicação

Suíte backend: `python -B scripts/run_offline_tests.py`. Runner desliga credenciais, ignora dotenv, cria SQLite descartáveis, bloqueia transportes HTTP reais e exige zero skips; precisa de FFmpeg/ffprobe/Poppler. PostgreSQL exige `--postgres-test-url` local explícito com banco descartável: tabelas são recriadas. Não usar produção/túnel.

`.github/workflows/tests.yml`: checks de backend SQLite/PostgreSQL e testes/build frontend, sem secrets/deploy. Actions fixadas por SHA; instalação de dependências usa rede, testes não devem fazer chamadas reais a fornecedores. YAML e comandos verificados localmente; primeira execução no GitHub e regras que exijam aprovação antes do deploy permanecem pendentes. [Registro](PDF-READINESS-CI-2026-10-04.md).

Interface: `npm test` e `npm run build`. Controles HTTP opcionais: `backend/scripts/audit_probe.py`; contas de teste somente em localhost. `provider_probe.py` é opt-in e pode consumir créditos. Controles estáticos não medem precisão de deepfake.

`validation_ui_server.py` é harness descartável, nunca configuração de deploy. Registra fronteiras de análise/exportação em `http-boundaries.json` apenas com rota fixa, método, status e headers de tipo/cache: sem corpo, query, cookies, IDs ou tokens. A simulação local de página não valida HTTPS público. Um PDF/200 não comprova que o navegador o salvou.

Primeira etapa: `local_release_server.py` gera seu próprio banco descartável, desliga provedores e ignora `.env` privado antes de importar a aplicação. `release_http_probe.py` testa histórico/PDF/isolamento por HTTP somente em localhost. Instruções e resultados em [PRIMEIRA-ETAPA-2026-10-03.md](PRIMEIRA-ETAPA-2026-10-03.md).

Compose é desenvolvimento (portas 5174/8001/5433, recarga e senhas de exemplo). Perfil Evolution não provisiona sozinho todos os recursos nem o transporte autenticado. Dockerfiles raiz/backend instalam FFmpeg/ExifTool/Tesseract português e inglês e executam sem reload.

Vercel recebe frontend; Railway recebe backend/banco. Antes de publicar: builder/root corretos, segredos fortes, HTTPS/cookies, origens exatas, ferramentas de mídia e migrações. Limites e deduplicação são por processo; múltiplas réplicas exigem armazenamento compartilhado. Nenhum teste local prova que a revisão já esteja no deploy.
