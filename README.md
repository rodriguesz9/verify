# Verify

Aplicação de apoio à checagem de mensagens, links, imagens, áudio e vídeos. Feita para ajudar pessoas a reconhecer sinais de risco e consultar evidências antes de compartilhar ou agir.

Não é uma perícia, um certificado de autenticidade ou uma garantia de detecção de deepfake.

Guias novos: [configurar APIs sem novas contratações](docs/APIS-SEM-CUSTO.md) · [ativar Hugging Face, Hive e Gemini; situação do OpenRouter](docs/ATIVAR-DETECTORES.md) · [landing, Modo Fácil e testes visuais](docs/INTERFACE-MODO-FACIL.md).

## Estado atual — revisão de 3 de outubro de 2026

A versão publicada foi testada em [verifybr.vercel.app](https://verifybr.vercel.app). Foram encontradas falhas de validação de mídia, erros em texto/WhatsApp e resultados de voz dependentes do nome do arquivo.

A revisão corrige esses comportamentos e separa veracidade da informação da origem da mídia. A publicação foi autorizada via Git; **deploy e provedores devem ser confirmados separadamente**. Consulte o [passo a passo de configuração em produção](docs/CONFIGURACAO-PRODUCAO.md), o [guia de verificações e chaves](docs/VERIFICACOES-2026-10-03.md), o [relatório histórico da auditoria](docs/AUDITORIA-2026-10-02.md) e os resultados reproduzíveis:

- [Produção, antes das correções](docs/audit-production-2026-10-02.json).
- [Fluxos locais corrigidos](docs/audit-local-2026-10-02.json).
- [25 controles HTTP finais desta etapa](docs/audit-verifications-local-2026-10-03.json).
- [Teste limitado com provedores reais](docs/audit-providers-2026-10-02.json).
- [Origem e limites das mídias de teste](backend/tests/fixtures/README.md).

Última execução da revisão de verificações: **137 testes backend + 66 subtestes, 15 testes de interface e 25 controles HTTP aprovados; build concluído**. Na etapa visual subsequente, o frontend passou em **21 casos** e novo build, com correções do Modo Fácil e landing. Houve dois avisos de descontinuação de dependências (AnyIO/Starlette e python-jose), não erros. São testes funcionais, não medição da precisão dos detectores. Um HTTP 200 não significa análise conclusiva. Testes de políticas usam respostas controladas e chaves externas desligadas; resultados reais de provedores citados acima são históricos, não validação das novas integrações.

Preparação para o push: a suíte backend também passou com **PostgreSQL 16 descartável**. A atualização de um enum antigo foi repetida sem erro, e `FALSE` foi gravado/lido corretamente. Corrigidos isolamento de conexões e ordem dos dados nos testes reais de banco. A imagem Docker da raiz compilou, carregou a API e confirmou FFmpeg/ffprobe/ExifTool; agora ambos os contextos de build excluem `.env`, bancos locais e caches, e ambos os comandos respeitam `PORT`. Não houve acesso ao banco de produção, teste pago novo de provedores ou comprovação de precisão.

## O que a aplicação faz

| Entrada | Verificações disponíveis | Limite importante |
| --- | --- | --- |
| Texto | Padrões de risco e checagens atribuídas: duas famílias editoriais distintas com correspondência literal conservadora | LLM não decide verdade; paráfrase, contexto relativo, discordância ou cobertura incompleta ficam inconclusivos |
| Link | Consulta pública limitada com validação DNS/IP/TLS; conteúdo segue a política factual de texto | Não certifica legitimidade nem consulta idade do domínio; bloqueios e limites podem impedir leitura |
| Imagem | Decodificação real, Sightengine/Hive/Hugging Face, metadados, C2PA, OCR e inspeção visual auxiliar | Metadados podem ser forjados; visão de um LLM não é prova de geração por IA |
| Áudio | Transcrição Gemini/AssemblyAI, triagem do discurso, Hive específico e Sightengine `ai_speech` opt-in | Transcrição não prova clonagem; segundo detector exige autorização ao modelo, não só chave |
| Vídeo | Amostragem adaptativa de até nove quadros por padrão e análise separada da faixa de áudio | Não verifica todos os quadros, sincronização labial ou identidade; média temporal não vira consenso |

Outros recursos: login com cookies HTTP-only, histórico autenticado, lotes de texto, PDF do resultado, demonstração educativa e simulador de WhatsApp.

O relatório na interface explica os sinais encontrados, destaca os trechos que acionaram regras e mostra fontes de checagem quando retornadas. Orientações oficiais cadastradas ficam separadas das consultas externas. Vídeos mostram o número de quadros e os tempos amostrados. O indicador animado é **heurístico, não porcentagem de veracidade**: sem evidência, aparece “Não determinado”. A interface usa rolagem nativa personalizada e respeita movimento reduzido.

O registro SHA-256 compara bytes com um registro anterior. Não comprova autoria, captura por câmera, veracidade da cena nem assinatura C2PA.

## Política de resultado

- Falta de evidência, erro de API ou discordância relevante: **inconclusivo**.
- Indícios concordantes de detectores: **resultado parcial**, sujeito a revisão.
- C2PA só é tratado como credencial validada quando a validação e a confiança criptográfica estiverem configuradas.
- Ausência de sinais de IA nunca transforma uma mídia em “autêntica”.
- Corroborada/refutada é classificação atribuída às checagens correspondentes; `False` não é sinônimo de `AI_Generated`. OCR/transcrição têm relatório factual separado.
- Pontuações são sinais não calibrados. Não são porcentagens de acerto do Verify.

As políticas experimentais estão em `backend/app/services/evidence_policy.py` e `claim_policy.py`. Limiares precisam de validação com um conjunto rotulado representativo; concordância entre dois serviços ou famílias editoriais não garante independência estatística.

`GET /api/capabilities` informa configuração/ferramentas sem expor chaves nem fazer chamadas pagas. Presença de configuração não comprova acesso ou quota: disponibilidade operacional fica `not_tested`. Para métricas offline com resultados inconclusivos incluídos, use `backend/scripts/evaluate_predictions.py`, seguindo o [formato e plano de avaliação](docs/VERIFICACOES-2026-10-03.md#como-medir-precisão-de-verdade-sem-esconder-inconclusivos).

## Arquitetura

- Interface: React, Vite, Tailwind CSS e Lucide.
- API: FastAPI e Pydantic.
- Persistência: SQLAlchemy assíncrono e PostgreSQL; SQLite em testes isolados.
- Mídia: Pillow, FFmpeg/ffprobe; ExifTool e c2patool opcionais.
- Hospedagem: frontend na Vercel, API e banco na Railway.

Uploads, relatórios completos e PDFs usam o mesmo fluxo de análise de mídia. Arquivos aceitos: imagens decodificáveis JPEG/PNG/WebP/GIF, áudio e vídeo suportados pelo servidor. Limites: 25 MB, 20 megapixels e dois minutos. Imagens animadas têm cobertura limitada ao primeiro quadro.

## Executar com Docker

Copie `backend/.env.example` para `backend/.env` e configure o necessário. Não comite esse arquivo.

```bash
docker compose up --build
```

- Interface: http://localhost:5174
- API: http://localhost:8001
- Documentação: http://localhost:8001/docs
- Saúde: http://localhost:8001/health
- PostgreSQL de desenvolvimento: porta 5433

O Compose é para desenvolvimento: possui senhas de exemplo, volumes locais e recarga automática. Não exponha o banco nem use essas senhas em produção. O Dockerfile do backend instala FFmpeg e ExifTool; c2patool exige instalação adicional.

O perfil opcional `whatsapp` não foi certificado de ponta a ponta com um número real. O webhook não envia automaticamente uma mensagem só porque retornou um JSON; integração de transporte, autenticação e provisionamento do gateway ainda precisam de validação.

## Testes reproduzíveis

Dentro de `backend`, com dependências instaladas:

```bash
TEST_DATABASE_URL=sqlite+aiosqlite:////tmp/verify-test.db python -m pytest -q
```

Use **somente um banco descartável de testes**: a suíte de integração recria suas tabelas. Os testes desabilitam credenciais externas; não dependem de créditos pagos.

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
| Hugging Face | [Tokens](https://huggingface.co/settings/tokens) · [Endpoints](https://endpoints.huggingface.co/) | `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_IMAGE_API_URL`, `HUGGINGFACE_AI_LABEL` |
| AssemblyAI | [Painel](https://www.assemblyai.com/dashboard/) · [transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/getting-started/transcribe-an-audio-file) | `ASSEMBLYAI_API_KEY` — alternativa de transcrição, não detector de clonagem |
| Google Fact Check | [Console Google Cloud](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com) · [documentação](https://developers.google.com/fact-check/tools/api/reference/rest/) | `GOOGLE_FACT_CHECK_KEY` |
| Serper | [Serper](https://serper.dev/) | `SERPERAPI_KEY` |
| SerpApi | [Chave](https://serpapi.com/manage-api-key) · [Lens](https://serpapi.com/google-lens-api) | `SERPAPI_KEY` |
| OpenRouter, cliente legado/opcional | [Chaves](https://openrouter.ai/settings/keys) · [documentação](https://openrouter.ai/docs/quickstart) | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`; não decide veracidade no fluxo atual |

Hive v2 exige chave do projeto/modelo apropriado: chave de imagem não habilita automaticamente manipulação facial, áudio ou texto; chaves v3 não são intercambiáveis com v2. Duas chamadas Hive não contam como dois detectores independentes. HF exige endpoint hospedado oficial explicitamente configurado e classe positiva documentada, não apenas um token. Sightengine `ai_speech` tem acesso enterprise/parceiro; mantenha desligado sem autorização e confirme preço/acesso antes de contratar.

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
