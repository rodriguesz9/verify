# Verify — estrutura e arquitetura

Guia da revisão local, atualizado em 3 de outubro de 2026. Não é prova de implantação. Para execução, chaves e limites, veja [README](../README.md); para achados históricos, veja [auditoria](AUDITORIA-2026-10-02.md) e [continuação](CONTINUACAO-2026-10-02.md). Novas regras, configuração e avaliação estão em [verificações](VERIFICACOES-2026-10-03.md).

## Componentes

- `frontend/`: React 18, Vite, Tailwind, Lucide e React Router.
- `backend/app/`: FastAPI, serviços de análise, autenticação e persistência.
- PostgreSQL em produção; SQLite somente para desenvolvimento/testes isolados.
- FFmpeg/ffprobe para validar áudio/vídeo e extrair quadros, Pillow para imagem. ExifTool/c2patool são opcionais e devem informar indisponibilidade quando ausentes.

## Fluxos

Texto/link: entrada limitada → admissão/quota → consulta pública segura (link) → afirmações literais + checagens recuperadas → `claim_policy.py` → relatório → histórico se autenticado. LLM só auxilia extração/busca; não decide verdade/falsidade.

Mídia: limite de bytes → decodificação real/limites de dimensão e duração → `media_analysis.py` → camadas disponíveis → `evidence_policy.py` → resposta/histórico/PDF.

WhatsApp: segredo do webhook → parser de evento → ignorar eventos próprios/duplicados → bytes base64 ou download público limitado → fluxo de texto/mídia → JSON de resposta. Envio efetivo ao número exige gateway/integração adicional.

## API

Todos os routers ficam sob `/api`.

| Router | Rotas principais | Uso |
| --- | --- | --- |
| `auth.py` | `/auth/register`, `/auth/login`, `/auth/google`, `/auth/refresh`, `/auth/logout`, `/auth/me` | Cookies HTTP-only; JWT não é retornado ao JavaScript |
| `check_text.py` | `/check-text`, `/check-text-batch` | Texto e até dez mensagens por lote |
| `check_url.py` | `/check-url` | Extrai até 5.000 caracteres de documento público limitado |
| `upload.py` | `/upload` | Imagem, áudio ou vídeo pelo fluxo centralizado |
| `verificacao.py` | `/verificar/completo`, `/verificar/audio-rapido`, `/verificar/relatorio-pdf` | Análise de mídia, conteúdo da fala, exportação |
| `verificacao.py` | `/capturar/selo`, `/verificar/selo` | Registro/comparação de bytes SHA-256; não comprova autenticidade |
| `history.py` | `/history`, `/history/stats`, `/history/{id}` | Consulta restrita ao usuário autenticado |
| `whatsapp.py` | `/whatsapp/webhook`, `/whatsapp/simulate` | Webhook autenticado e demonstração pública limitada |

`/health` é liveness, não um teste completo de provedores ou readiness do banco. `/api/capabilities` informa presença de configurações/ferramentas, sem valores de segredos ou chamadas pagas; disponibilidade operacional continua `not_tested`. Lifespan inicializa tabelas e encerra o pool no desligamento. Alterações aditivas de enum (`SCAM`, `FALSE`) existem; precisam de staging PostgreSQL e não substituem migrações completas.

## Serviços importantes

- `core/pipeline.py`: recupera checagens/notícias, registra falhas e passa afirmações literais à política de veracidade. Padrões de golpe não são prova de identidade nem investigação concluída.
- `services/claim_policy.py`: duas famílias editoriais distintas com avaliação explícita, data válida e correspondência exata conservadora; negação/valores/datas preservados. Discordância, contexto relativo e cobertura incompleta impedem aprovação global. Classificação é atribuída às fontes, não garantia de verdade.
- `core/scam_detector.py`: regras de triagem com trechos encontrados. Extensão de domínio isolada não produz veredito de golpe. Referências de orientação são cadastradas, não consultas automáticas.
- `core/gemini_client.py`: cliente assíncrono com modelo explícito e erros; nada de inventar sucesso em falhas.
- `core/request_budget.py`: admissão por IP/processo, concorrência e corpo limitado; proteção de origens de escrita.
- `services/public_fetch.py`: valida DNS e conecta ao IP validado com TLS/SNI correto. Revalida redirecionamentos, limita bytes/tempo; não usa proxy do ambiente.
- `services/media_validation.py`: valida bytes reais; 25 MiB, 20 megapixels e 120 segundos. Não confia em nome/extensão/MIME declarado.
- `services/media_analysis.py`: fluxo comum de imagem/áudio/vídeo. Vídeo amostra até nove quadros por padrão, exige concordância no mesmo quadro e analisa áudio em paralelo. OCR/transcrição têm checagem factual separada; não faz perícia temporal completa.
- `services/speech_detector.py`: Sightengine `ai_speech` opt-in com acesso ao modelo; Hive de áudio é outro projeto. Transcrição não comprova clonagem e pontuação máxima de um trecho não se aplica automaticamente ao arquivo inteiro.
- `services/benchmark_metrics.py`: métricas offline por dimensão/modalidade/split, com inconclusivos nos denominadores. Não gera ground truth nem valida precisão sem corpus real independente.
- `services/evidence_policy.py`: cobertura, discordância, limitações e política versionada. Ausência de sinal de IA nunca vira mídia autêntica; resultados sem cobertura são inconclusivos.
- `services/c2pa_service.py`: marcador não é assinatura validada. Confiança criptográfica depende de ferramenta/configuração.
- `services/whatsapp_security.py`: autenticação, parser, base64 e deduplicação limitada por processo.
- `services/gemini_service.py`: fala real quando disponível, PCM em WAV. Falha não vira beep apresentado como voz.
- `services/pdf_report_service.py`: PDF do resultado real e suas limitações.

Os clientes Hive, Sightengine e Hugging Face não são intercambiáveis. Hive exige projetos apropriados (incluindo facial separado); token HF exige endpoint hospedado oficial explícito e classe positiva documentada. Erros diminuem cobertura, não viram evidência de falsidade. Duas chamadas Hive não são dois detectores independentes.

## Persistência e privacidade

Modelos de usuário, verificação, métricas, registro de integridade e conversas WhatsApp ficam em `models/`.

- Histórico pertence ao usuário autenticado.
- Cache MD5 legado não é reutilizado globalmente no upload. Se reintroduzido, precisa de versão, isolamento/contexto e validade explícitos.
- Registro SHA-256 apenas relaciona bytes a registro anterior. Não é C2PA nem certificado de câmera.
- WhatsApp guarda histórico somente se habilitado e com chave HMAC independente. Hash é pseudônimo; texto pode conter dados pessoais. Simulações não entram no histórico real.
- Não registrar mensagens, parâmetros SQL, credenciais ou URLs sensíveis em logs.
- Exclusão de conta/retenção completa ainda são pendências, não funcionalidades garantidas.

## Interface

Rotas públicas: `/`, `/app`, `/report`, `/demo`, páginas institucionais, login/cadastro. `/dashboard` e `/history` exigem sessão; ambas usam o painel existente.

`src/services/api.js` concentra chamadas e renovação de cookies. `VITE_API_URL` recebe o domínio da API, sem `/api`; se ausente, usa proxy relativo.

`hooks/authContext.js` fornece o contexto/hook compartilhado; `hooks/useAuth.jsx` exporta somente o provider de componente, mantendo a fronteira de Fast Refresh estável.

Relatório usa `components/report/EvidenceExplanation.jsx` e `AnimatedScore.jsx`. Fontes recuperadas e orientações cadastradas são separadas. Indicador não é porcentagem de acerto/veracidade. Inconclusivo não recebe valor inventado. Animação tem cancelamento e movimento reduzido; rolagem nativa é personalizada em `index.css`.

Contrato atual separa `veracity_status` de `authenticity_status`, inclui `claim_assessments` e `content_analysis`. `False` é refutação atribuída, não mídia gerada por IA. O índice legado usa `score_semantics=legacy_decision_index_not_probability`; listas mostram índice/100 e deixam inconclusivos sem índice, não como precisão.

`utils/reportEvidence.js` normaliza dados, limita índices e bloqueia protocolos perigosos em links de referência. Testes do utilitário ficam em `frontend/tests/`. `score-preview.html` é controle visual do Vite, não resultado/rota publicada.

## Testes e publicação

Suíte backend desliga provedores externos. Para testes reais de banco, `TEST_DATABASE_URL` deve apontar somente para banco descartável: tabelas são recriadas. Execute `python -m pytest -q`.

Interface: `npm test` e `npm run build`. Controles HTTP opcionais: `backend/scripts/audit_probe.py`; contas de teste somente em localhost. `provider_probe.py` é opt-in e pode consumir créditos. Controles estáticos não medem precisão de deepfake.

Compose é desenvolvimento (portas 5174/8001/5433, recarga e senhas de exemplo). Perfil Evolution não provisiona sozinho todos os recursos nem o transporte autenticado. Dockerfile backend instala FFmpeg/ExifTool e executa sem reload.

Vercel recebe frontend; Railway recebe backend/banco. Antes de publicar: builder/root corretos, segredos fortes, HTTPS/cookies, origens exatas, ferramentas de mídia e migrações. Limites e deduplicação são por processo; múltiplas réplicas exigem armazenamento compartilhado. Nenhum teste local prova que a revisão já esteja no deploy.
