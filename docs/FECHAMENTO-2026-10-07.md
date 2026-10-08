# Verify — correções e validação de 07/10/2026

Revisão local, base `5db970da8f8a109472050ed96e3ab77d20e7f5e7`. Não é novo commit nem certificação do deploy. Prazo antecipado pelo responsável: [até 11/10](ENTREGA-ATE-11-OUTUBRO.md). O [manual completo](DOCUMENTACAO-COMPLETA.md) e o [plano de 14 dias](PLANO-ENTREGA-14-DIAS.md) permanecem complementares.

## Resultado executivo

- Prazos curtos de 12–20 segundos que cortavam o Gemini foram corrigidos. Há prazo total configurável, não espera infinita.
- Gemini 3.8 respondeu ao controle mínimo de texto; OCR/inspeção ainda retornaram **HTTP 503**. Não declarar Gemini multimodal homologado.
- OCR local leu corretamente o controle impresso na interface, preservando negação, valor e data. Nova checagem do texto conferido também respondeu; nenhuma API externa recebeu esse controle no ensaio local.
- OpenRouter já auxilia extração literal para pesquisa; o sucesso observado em texto não valida sua modalidade de visão/OCR. Não é coautor de um veredito factual e não vota sobre autenticidade.
- Falhas de APIs são visíveis. Relatório inconclusivo não afirma falsidade nem autenticidade.
- Testes offline atuais: **382 backend em SQLite e no modo PostgreSQL descartável, 101 frontend e build**. Execuções repetidas não são testes distintos nem benchmark de precisão.
- Ainda sem novo commit/push/deploy. O original sujo não foi sobrescrito; esta revisão está em checkout separado.

## 1. Correções implementadas

| Área | Mudança | Verificação / fronteira |
| --- | --- | --- |
| Gemini | Deadline total 60 s; inteiro 10–90; inválido volta a 60; fallback explícito compartilha o prazo | Configuração, limites HTTP, expiração sanitizada e uma única janela testados offline |
| OCR / transcrição | Camadas externas não cancelam Gemini aos antigos 12–20 s | OCR espera deadline + 2; camada inclui preparação e fallback; transcrição humana ainda pendente |
| OCR OpenRouter | Janela externa 27 s para cliente de 25 s; camada OCR completa até 100 s padrão | Corrige cancelamento aos antigos 12 s; formato/limites/preço zero preservados; sucesso remoto ainda não homologado |
| Extração textual | Limite de saída da extração Gemini elevado de 768 para 2.048 tokens | Trechos continuam obrigatoriamente literais; geração incompleta é recusada |
| Erros Gemini | HTTP 503 vira `unavailable`; timeout de OpenRouter não esconde indisponibilidade primária | Sem corpo de erro do fornecedor, chave ou dado privado retornado |
| Interface | Texto/conferência/simulador 150 s; link/mídia/lote 180 s; aviso de espera acessível | 101 regressões frontend e build; auth 60 s / PDF 30 s preservados |
| Modelo default | Código e template passam a `gemini-3.8-flash` | Só texto mínimo respondeu; variáveis já configuradas em produção NÃO mudam automaticamente |
| Autenticação | Conta inativa bloqueada; Google exige email verificado booleano, subject canônico e associação conservadora | 26 testes focados com mocks; OAuth real / revogação de refresh / constraint Google ID ainda pendentes |
| URL | Entrada e URL final até 512; trim e `https://` contam; sem truncamento | Limites e interface testados; não migrar coluna nem alterar registros históricos |
| Vídeo | Dimensões visual/acústica preservadas no JSON, título, explicação e PDF | Sinal somente na voz não vira deepfake visual; identidade e lip-sync não são comprovados |
| C2PA | Inspeção de ações/URI exatas; runtime não concede confiança/voto | Não inferir trust por variável presente, comentários, substrings ou status vazio |
| Voz educativa | WAV válido preservado; PCM16LE encapsulado uma vez; base64/formato/tamanho limitados | 29 regressões de formato; fidelidade de TTS real ainda não homologada |
| Vision auxiliar | Schema completo obrigatório; vazio/parcial/tipos errados recusados; sem voto | 12 campos validados; explicação gerada não vira prova |
| TinEye / Wayback | Erro não aparenta zero matches / consulta bem-sucedida | Falha sanitizada; integração real desses serviços não homologada |
| Template | `DATABASE_URL` local explicitamente identificado; nova variável de timeout | Não copiar SQLite local, secrets ou habilitações pagas para Railway |

Essas correções não substituem migrações, avaliação de precisão ou revisão de privacidade para lançamento irrestrito.

## 2. Comparação real do Gemini

Chave privada lida somente por allowlist, sem importar banco/JWT/HMAC do `.env` original. Controles fixos, fictícios e sem dados pessoais. Sem geração de voz, rotação automática, retry, cartão ou recarga.

| Modelo / cenário | Prazo | Resultado | Interpretação |
| --- | ---: | --- | --- |
| 3.1 Flash-Lite, texto e OCR, primeiro diagnóstico | 20 s | Timeout nas duas tentativas | Observação anterior desta sessão; prazo insuficiente não prova modelo inexistente |
| 3.7 Flash, controle mínimo de texto | 60 s | HTTP 503, 3.882 ms | Indisponibilidade real do serviço |
| 3.7 Flash, OCR impresso | 60 s | HTTP 503, 2.540 ms | Sem transcrição utilizável |
| 3.8 Flash, controle mínimo de texto | 60 s | HTTP 200 / STOP, 4.608 ms | Transporte e JSON booleano funcionaram; não é teste de veredito/extração complexa |
| 3.8 Flash, OCR impresso | 60 s | HTTP 503, 5.088 ms | Não homologado |
| 3.8 Flash, upload pela UI: OCR + inspeção | 60 s por chamada | Duas chamadas HTTP 503; API de upload 200 / no-store | Aplicação retornou relatório inconclusivo com falhas visíveis; não falso sucesso |

Evidências persistidas:

- [3.7: controles](evidencias-2026-10-07/gemini-37-diagnostics.json).
- [3.8: controles](evidencias-2026-10-07/gemini-38-diagnostics.json).
- [UI: transporte](evidencias-2026-10-07/gemini-app-transport.json), [fronteira HTTP](evidencias-2026-10-07/gemini-app-boundaries.json), [captura do relatório](evidencias-2026-10-07/ui-gemini-unavailable.jpg).

Contagem reportada desta sessão: quatro gerações Gemini nos uploads anteriores, duas no primeiro diagnóstico, quatro na comparação e duas no upload final = **teto conhecido de 12 tentativas**, incluindo falhas. Os primeiros seis eventos são observações anteriores, não um journal completo preservado neste diretório. Os artefatos da comparação registram esse teto prévio como informação reportada, não contagem independente do painel Google. O harness final restringiu a duas chamadas; nenhum novo retry para “forçar” sucesso.

DNS/TLS/HTTP sem geração responderam; catálogo autenticado retornou 200 e listou os modelos. Isso enfraquece a hipótese de bloqueio geral de rede/chave inválida, mas não explica sozinho toda indisponibilidade multimodal. IPv6 do contêiner não tinha rota; IPv4/TLS funcionavam. Não foram desativados TLS, validação de certificado ou guardas de rede.

Catálogo e opção gratuita conferidos nas fontes oficiais em 07/10: [modelos](https://ai.google.dev/gemini-api/docs/models), [preços](https://ai.google.dev/gemini-api/docs/pricing), [diagnóstico de erros](https://ai.google.dev/gemini-api/docs/troubleshooting). HTTP 503 deve ser registrado e tratado como falha; timeout maior não garante resposta. Não ativar faturamento como solução implícita.

### Configuração recomendada para o candidato

Sem alterar ou publicar secrets automaticamente:

```dotenv
GEMINI_MODEL_NAME=gemini-3.8-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=60
GEMINI_FALLBACK_MODELS=
GEMINI_MEDIA_MODEL_NAME=
LOCAL_OCR_ENABLED=true
OPENROUTER_ENABLED=true
OPENROUTER_MODEL=openrouter/free
OPENROUTER_FALLBACK_MODELS=
HIVE_V3_MEDIA_TYPES=
SIGHTENGINE_AUDIO_ENABLED=false
```

`GEMINI_MEDIA_MODEL_NAME` vazio herda o principal; isso não homologa OCR/fala. Se já houver variável explícita antiga no Railway, o default novo não a substitui. Pode-se aumentar Gemini para 90 s de modo controlado, mas não repetir chamadas diante de HTTP 503 para gastar créditos sem diagnóstico. Tesseract exige binário e idiomas `por+eng`; os Dockerfiles da revisão os incluem. Aplicação continua pedindo conferência da leitura antes da checagem factual.

OpenRouter requer chave privada válida. `openrouter/free`/variantes `:free` e preço máximo zero permanecem obrigatórios. Não usar `openrouter/auto`, fallback pago ou endpoint dedicado cobrado. Mesmo com chave, pode não haver modelo gratuito disponível/compatível para imagens ou JSON estruturado.

## 3. OCR local → conferência → relatório

Ensaio separado, banco descartável, APIs/chaves externas desabilitadas, teto Gemini zero. Nenhum envio remoto permitido.

1. Selecionar Imagem em `/app` e enviar `impresso-base.png`.
2. Tesseract produziu literalmente 88 caracteres:

```text
CONTROLE DE TESTE
Nao pague taxa para liberar seu Pix.
Valor: R$ 123,45
Data: 03/10/2026
```

3. Interface exibiu original, texto editável, procedência `tesseract`, aviso sobre negação/valores/datas e confirmação explícita.
4. Depois de conferir, `/api/check-extracted-text` retornou 200 / no-store, preservando leitura original e origem.
5. Sem Fact Check/Serper habilitados nesse ensaio, resultado permaneceu **não determinado**. Não houve detecção falsa de golpe pela frase negada nem avaliação inventada de verdade.

[Captura](evidencias-2026-10-07/ui-local-ocr-review.jpg) · [HTTP de upload/conferência](evidencias-2026-10-07/local-ocr-boundaries.json).

Um controle limpo correto não mede fidelidade em prints degradados, manuscritos, documentos ou todo português. Isso valida um caminho funcional de contingência, não substitui o conjunto de avaliação.

## 4. Outras observações de APIs nesta sessão

Os números abaixo descrevem observações anteriores da sessão, não novos testes repetidos no ensaio final do Gemini. Logs temporários dessa primeira parte não foram encontrados na retomada; não são reconstruídos como journals brutos.

| Serviço | Observado | O que falta |
| --- | --- | --- |
| OpenRouter | Controle textual respondeu com `liquid/lfm-2.5-2.6b:free`; OCR teve 404/incompletude | Texto maior, preservação literal e OCR gratuito compatível reproduzíveis |
| Fact Check | Três consultas HTTP 200, sem checagens correspondentes ao controle fictício | Controles verdadeiros/refutados com fontes editoriais correspondentes |
| Serper | Duas consultas HTTP 200 com contexto relacionado | Contexto não vota como checagem; disponibilidade/quotas no candidato |
| Sightengine imagem | Foto publicada: sinal IA 0.001; imagem gerada: 0.99; deepfake 0.001 nos dois | Dois exemplos não medem precisão; áudio/face-swap e transforms ainda não homologados |
| Hugging Face | Dois uploads HTTP 200, camada experimental sem voto | Modelo já errou controles anteriores; não promovê-lo a decisor por responder |
| Hive | Zero novas chamadas nesta rodada | Autorização anterior de US$ 0,01 era só smoke; sem tráfego pago automático |
| AssemblyAI / TTS | Novas regressões offline, sem novas gravações humanas | Fidelity humana, retomada de jobs pendentes e TTS real |

Foto publicada e imagem gerada terminaram inconclusivas por cobertura insuficiente. Um sinal alto isolado não foi promovido a veredito final. Não contar esses dois resultados como dois “acertos de classificação”.

## 5. Corpus e arquivos humanos

- Duas imagens publicadas por fontes primárias NASA, origem/licença/hashes descritos no [manifesto](../backend/tests/fixtures/validation/internet-real-2026-10-07/manifest.json) e [README](../backend/tests/fixtures/validation/internet-real-2026-10-07/README.md). São derivados publicados, não RAWs de câmera certificados.
- Uma imagem inteiramente gerada por IA, sem pessoas/dados, declarada no [README do controle](../backend/tests/fixtures/validation/generated-2026-10-07/README.md). Prompt/procedência/hash preservados; não usar como foto humana.
- Caixa de entrada local criada: `/mnt/externo/IMPORTANTES/mostra/arquivos-para-validacao/`, com `audios/`, `videos/`, `fotos/` e instruções. Nenhum upload automático, nenhum dado privado em Git.
- Aguardar gravações humanas e dois vídeos autorizados do responsável. Arquivos gerados/programáticos não substituem os controles humanos.

## 6. Regressões e reprodução

Python 3.11 no Docker QA já disponível; backend bind somente leitura, usuário não-root, capacidades removidas, `no-new-privileges`, `/tmp` descartável. SQLite: sem rede. Modo PostgreSQL: banco isolado sem porta pública; HTTP real bloqueado pelo runner. Nenhum banco/contêiner existente do usuário foi alterado.

```bash
# Backend: dependências e FFmpeg/ffprobe/Poppler já instalados
cd backend
python -B scripts/run_offline_tests.py
# PostgreSQL só com banco DESCARTÁVEL local explícito: recria tabelas
python -B scripts/run_offline_tests.py --postgres-test-url postgresql+asyncpg://verify_test:local-disposable-test-only@127.0.0.1:5432/verify_release_test

# Frontend: Node 22 e dependências já instaladas
cd ../frontend
node --test --experimental-test-isolation=none tests/*.test.js
npm run build
```

Backend SQLite final: 382 testes / 8.737 s, zero skips e zero HTTP inesperado. Modo PostgreSQL final: mesmos 382 / 8.722 s. Frontend: 101 / zero falhas; build transformou 1.975 módulos. Só três testes são integração real PostgreSQL (consulta/histórico, stats e readiness); os restantes continuam SQLite/mocks. Não somar 382 + 382 como testes diferentes nem afirmar que toda autenticação/upload foi homologada no PostgreSQL.

PDF: quatro regressões de separação visual/acústica; snapshot e renderização preservam resultado original. A versão de teste visual não deve ter disclaimer órfão em segunda página. A resposta PDF/200 observada anteriormente não comprova arquivo salvo/aberto pelo navegador; essa fronteira permanece pendente.

CI continua preparado, não executado remotamente nesta rodada. Checks de branch/autodeploy precisam ser conferidos antes de declarar proteção de publicação.

## 7. Produção e próximos gates

Inspeção read-only anterior desta sessão:

- Railway: último deploy SUCCESS de 04/10 associado à base `5db970d…`, sem esta revisão nova.
- Vercel: último production READY de 04/10; alias `https://verifybr.vercel.app`. SHA não identificado pelo retorno de inspeção utilizado.
- Configuração presente em `/api/capabilities` não prova acesso, quota ou precisão. Hive v3 sem modalidades autorizadas permanece desabilitado para chamadas pagas.

Nenhuma variável remota, PR ou deploy foi alterado nesta rodada. Não sobrescrever o repositório original sujo nem fazer push cego de um checkout antigo.

Próximos gates para candidato desta semana:

1. Resolver/retestar disponibilidade do Gemini por modalidade; avaliar outro modelo gratuito apenas com teto novo registrado. Não usar texto mínimo como prova de OCR/transcrição.
2. Retomada limitada de AssemblyAI implementada na continuação: [registro de ASR](TRANSCRICAO-PENDENTE-2026-10-07.md). Ainda fechar checkpoint durável/reinício/réplicas e fala humana; não tratar garantia local finita como idempotência permanente.
3. Comparar arquivos humanos e derivados; registrar falhas, inconclusivos, cobertura e falsos positivos/negativos por dimensão.
4. Testar mobile, Modo Fácil, zoom 200%, teclado e movimento reduzido no candidato; confirmar PDF salvo/aberto.
5. Integrar as mudanças preservando o original; versionar candidato; CI real; homologar PostgreSQL e publicar revisão identificável com smoke/rollback.
6. Para lançamento aberto: retenção/exclusão, backup/restore, revogação de sessões e orçamento/quotas compartilhadas. Sem esses gates não chamar entrega pública “100% pronta”.

O [plano até 11/10](ENTREGA-ATE-11-OUTUBRO.md) atribui prioridade, aceite e dependência a cada item. Indisponibilidade externa é bloqueio de homologação, não motivo para fabricar resultado conclusivo.
