# Verify — validação pela interface, 04/10/2026

## Resultado da rodada

Validação **local**, em cópia revisada do projeto, base Git `5db970da8f8a109472050ed96e3ab77d20e7f5e7` mais alterações não commitadas. **Não é homologação de Railway/Vercel nem benchmark de precisão.** Nenhum commit, push ou deploy realizado nesta rodada.

**Continuação posterior em 04/10:** conferência pré-checagem e nova análise textual vinculada foram implementadas/testadas, com 242 testes backend e 79 frontend aprovados. O registro abaixo preserva a rodada anterior e seus contadores/falhas; atualização em [CONFERENCIA-TEXTO-2026-10-04.md](CONFERENCIA-TEXTO-2026-10-04.md), sem novas chamadas externas.

- 223 testes backend passaram, sem skips, com SQLite descartável e Poppler local; 71 testes frontend passaram; build Vite passou; `git diff --check` passou.
- 16 controles offline passaram: regras factuais simuladas, OCR real Tesseract, silêncio/decodificação, amostragem FFmpeg e rejeição de URL privada. Esses controles não usam respostas reais de detectores.
- 18 relatórios obtidos pelo navegador local, incluindo comparações antes/depois e repetição do mesmo arquivo. Não são 18 amostras independentes. Uploads, texto e links foram operados pela interface, sem injetar resultados no navegador.
- A [matriz de 30 casos](MATRIZ-VALIDACAO-30-CASOS.md) tem 20 controles executados em pelo menos uma dimensão e 10 pendentes. **Execução não equivale a aprovação de todas as dimensões.** AUD02 tem falhas reais de transcrição; IMG02/IMG03 têm sinais errados de HF.

Registros publicados, sem chaves, tokens PDF, IDs de jobs ou respostas brutas:

- [Observações da UI](validation-ui-observations-2026-10-04.json).
- [Transporte dos provedores](validation-provider-transport-2026-10-04.json): HTTP/counters, não acurácia.
- [Controles offline](validation-offline-controls-2026-10-04.json).
- Referências/hashes dos PNGs: `backend/tests/fixtures/validation/ocr/manifest.json`.

Os registros anteriores às correções foram preservados. Um status `success` indica resposta aceita, **não leitura correta nem veredito correto**. O contrato legado `Suspicious` corresponde a “análise inconclusiva” quando `analysis_status=inconclusive`; não significa falsidade demonstrada.

## Ambiente e orçamento

Frontend Vite em `127.0.0.1:5176`, proxy local para backend Docker em `127.0.0.1:8027`. Banco temporário, autenticação/assinatura de teste independentes e sem conexão ao Postgres de produção. Imagem Docker local existente `verify-first-stage-root:20261004-pdf`, com código atual montado somente leitura; nenhuma imagem nova de release publicada.

`scripts/validation_ui_server.py` lê o `.env` privado por allowlist. Não importa banco, segredos de produção ou chaves Hive. Serviços são selecionados explicitamente; hosts desconhecidos são bloqueados antes do envio. Limites contam falhas e persistem entre reinícios desta sessão. No final, todos os provedores foram desligados para testes locais. Esta configuração descartável **não deve substituir a configuração de produção**.

| Serviço | Chamadas nesta sessão | Limite de teste |
|---|---:|---:|
| Gemini | 12 | 12 |
| OpenRouter | 3 | 8; interrompido após 429 |
| Google Fact Check | 33 | 40 |
| Serper | 12 | 16 |
| AssemblyAI | 10, incluindo uploads, jobs e polls | 2 uploads + 2 jobs; 40 requests totais |
| Sightengine imagem | 3 | 3 |
| Hugging Face compartilhado | 2 | 2 |
| Página pública NASA | 2 | 4 |

Hive permaneceu desligado: zero chamada paga, sem cartão ou recarga. Não houve endpoint HF dedicado provisionado. A conta SerpAPI foi consultada apenas para autenticação/metadados; **não houve busca reversa real homologada**. Nenhum consumo monetário exato foi auditado nos painéis de cobrança; os contadores não representam valor cobrado.

Gemini iniciou com `gemini-3.7-flash`; OCR/áudio e a comparação posterior usaram `gemini-3.1-flash-lite`. Sem rotação paga. OpenRouter usou `openrouter/free`, preço máximo zero e nenhum fallback pago. A disponibilidade gratuita pode mudar: conferir [preços Gemini](https://ai.google.dev/gemini-api/docs/pricing), [OpenRouter](https://openrouter.ai/pricing/) e [HF](https://huggingface.co/docs/inference-providers/en/pricing) antes de nova execução.

## O que os serviços realmente fizeram

| Serviço/modalidade | Observação real | Limite da conclusão |
|---|---|---|
| Tesseract OCR | Quatro linhas impressas exatas; valores/datas distintos; azul sem texto não gerou palavras. UI também exibiu o texto literal. | Controles renderizados; ainda faltam foto/print degradado e escrita difícil. |
| Gemini OCR/inspeção | OCR impresso exato; imagens sem texto retornaram string vazia. Inspeção respondeu após respeitar o modelo de mídia configurado. | Inspeção de LLM não vota em autenticidade. Houve 503 e extração textual incompleta na configuração inicial. |
| Gemini ASR | Pedido fictício: leu “Pix urgente”, mas “Faz” virou “Faço”. | Falha residual de sentido/ato de fala; não considerar transcrição integralmente aprovada. |
| OpenRouter | Extraiu literalmente “Não pague uma taxa para liberar seu Pix.”; modelo efetivo `liquid/lfm-2.5-2.6b:free`. | Link longo retornou resposta inválida/incompleta; OCR retornou 429. Texto curto funciona; OCR não homologado. Sem insistência após quota. |
| AssemblyAI `universal-2` | Conversa sintética foi transcrita exatamente; pedido financeiro teve “Pix urgente” → “pic surgente”. | Erros críticos reais. Confiança informada pelo provedor não mede taxa de acerto. |
| Sightengine imagem | Sinal IA 0,99 no café sintético; 0,001 no gráfico impresso e na composição de satélite. | Três controles, apenas um gerador sintético; scores não calibrados. Não houve face-swap/deepfake real de referência. |
| HF compartilhado | Gráfico impresso: sinal IA 0,999914; café sintético: 0,002527. | Responde, mas falhou nestes controles. Gráfico é fora do domínio de fotos naturais. Continua experimental/sem voto; não extrapolar taxa de precisão a partir de duas imagens. |
| Google Fact Check/Serper | Google respondeu sem checagens correspondentes; Serper recuperou notícias em algumas buscas. | Recuperação não confirma a frase. Nenhuma afirmação real foi corroborada/refutada automaticamente nesta rodada. |

O endpoint HF testado foi `https://router.huggingface.co/hf-inference/models/Ateeqq/ai-vs-human-image-detector`, rótulo positivo `ai`. Token autenticado e metadados do modelo consultados antes das duas inferências. Isso não configura automaticamente o Railway nem torna o modelo apto a decidir.

Sightengine áudio `ai_speech`, Hive voz/facial, voz clonada consentida, lip-sync e C2PA assinado **não foram homologados**. Nomes dos arquivos antigos `voz_humana_real.mp3` e `voz_golpe_clonado.mp3` não foram aceitos como prova de origem.

## Controles e falhas preservadas

1. **OCR01/IMG03:** PNG criado sem IA, com “Nao pague”, R$ 123,45 e 03/10/2026. Tesseract e Gemini preservaram as quatro linhas. HF deu falso sinal alto; nenhum certificado de falsidade foi produzido.
2. **IMG02:** personagem fictícia gerada por IA, procedência registrada. Sightengine alto, HF baixo; resultado de origem inconclusivo por cobertura insuficiente. É abstenção, não acerto universal de detecção.
3. **AUD01:** eSpeak lendo conversa fictícia, sem imitar pessoa real. AssemblyAI preservou as 16 palavras. Não classificou a voz como humana pelo conteúdo cotidiano.
4. **AUD02:** referência de 17 palavras, “Mãe, caí na rua e perdi meu celular. Faz um Pix urgente para o guincho, por favor.” AssemblyAI fez duas substituições críticas; Gemini uma (“Faz” → “Faço”). Na comparação literal minúscula, sem pontuação, equivalem a 2/17 e 1/17 palavras, respectivamente. Não são métricas de população nem de clonagem. A correção da triagem reconhece o relato de perda de celular, mas **não corrige o ASR silenciosamente**.
5. **Afirmação verdadeira:** pouso da Apollo 11 em 20/07/1969, referência manual [NASA](https://www.nasa.gov/mission/apollo-11/). **Boato falso:** “A NASA admite que a Terra é plana”, incompatível com a descrição oficial da estrutura e forma do planeta em [NASA Earth Facts](https://science.nasa.gov/earth/facts/). Na aplicação, ambas ficaram `unverified`: nenhuma review correspondente retornou. A fonte manual deste ensaio não foi injetada como review da API.
6. **Link público NASA:** inicialmente virou `Scam` pelo token genérico “gov”; após correção, `is_scam=false`, sem certificar as alegações da página. O primeiro erro de acesso veio do limitador de testes não reconhecer conexão com IP fixado; a proteção SSRF/HTTPS do aplicativo não foi removida.
7. **Imagem pública adicional:** [Blue Marble 2012](https://science.nasa.gov/image-detail/amf-gsfc_20171208_archive_e001386/), composição de faixas reais de satélite VIIRS, não uma foto única de câmera nem IA generativa. SHA-256 `7086bb4b90dc2660c3e76fdb4ddf91536a38796ea8da2e153b77758021111a8d`. Crédito NASA/NOAA/GSFC/Suomi NPP, sujeito às [orientações de mídia](https://www.nasa.gov/nasa-brand-center/images-and-media/). Não substitui IMG01/foto própria, não implica endosso da NASA.
8. **AUD03:** silêncio WebM sem duração no cabeçalho. Primeiro recusado por MIME do navegador; após correção, áudio decodificado, duração de ~1 s e `no_speech` local, texto vazio, sem chamadas ASR. A falta de chave não apagou a observação local.
9. **VID01:** MP4 de três segundos derivado do café sintético, três quadros em 0,3/1,5/2,7 s, sem faixa de voz. UI mostrou amostragem e resultado inconclusivo com detectores desligados. Não é benchmark de vídeo generativo ou manipulação facial.
10. **Texto afirmativo/negado:** pedido de taxa recebe indício de possível golpe; “Não pague…” não recebe esse alerta. Veracidade permanece não determinada. URLs loopback foram recusadas tanto em porta 8000 quanto em porta 80, antes de consultar qualquer provedor.

Exportação PDF de AUD02 foi acionada na interface: arquivo original exportado, sem nova inferência. Duas páginas renderizadas e inspecionadas, sem cortes/overlaps. O download ocorreu, embora o evento de download da ferramenta de navegador tenha expirado. Existe pendência cosmética: alguns valores ausentes ainda aparecem como `None` no PDF; não confundir esse defeito com sinal de detector.

## Correções implementadas

- Relatório mostra OCR/transcrição literal, método/provedor e aviso para conferir negação, valor e data. Há link para nova checagem textual; não é editor pré-análise nem alteração retroativa do resultado original.
- Consulta vazia do Google é distinguida de falha/ausência de chave. Falha parcial permanece visível.
- OCR vazio vira `no_text`; silêncio vira `no_speech`, sem fabricação de palavras ou percentuais.
- Inspeção Gemini respeita `GEMINI_MEDIA_MODEL_NAME`; falha preserva estado/razão sanitizada, sem score fictício 50.
- Extração Gemini passou de duas chamadas/reformulação para uma saída estruturada literal; trechos inventados são descartados. Falha/timeout entra na cobertura, sem perder a busca literal.
- Triagem de áudio contempla “perdi meu celular” e mantém negações. Não transforma “pic” em “Pix” por suposição.
- Domínios estrangeiros `.gov` não imitam automaticamente Gov.br. Imitadores `gov.br.evil.test` e `consulta-gov-br.xyz` continuam sinalizados; domínio conhecido não prova verdade.
- WebM só de áudio pode ter MIME `video/webm` do navegador, **apenas após validação real das faixas**. Vídeo disfarçado de áudio e imagem com MIME falso continuam recusados.
- OpenRouter rejeita truncamento com explicação específica e mantém o provedor correto mesmo em falha de OCR. Sem retry/reparo pago.

## Próximas prioridades para 17/10

1. Obter originais próprios autorizados: foto de objeto, vídeo curto sem pessoas e voz lendo negação/valores/datas. Completar os 10 controles restantes e comparar versões comprimidas. Não usar nome de arquivo como ground truth nem enviar conteúdo privado sem consentimento.
2. Melhorar recuperação factual com consultas conservadoras e revisão de evidências correspondentes. Medir abstenções e casos verdadeiros/falsos; não promover notícia relacionada ou opinião de LLM a prova apenas para aumentar cobertura.
3. Conferência **antes** de checar afirmações extraídas, com edição explícita pelo usuário e novo resultado identificado. O bloco de revisão atual é uma mitigação, não uma solução para todos os erros ASR.
4. Corrigir detalhes do PDF e explicitar “sem faixa de áudio” em vídeos; testar fluxo completo autenticado no deploy candidato, incluindo histórico/exportação, limites/429 e restauração do banco.
5. Validar Railway/Vercel da versão candidata, revisar configuração pública vs privada e só depois publicar/registrar o release. Esta rodada não verificou valores secretos do Railway nem implantou alterações.

Não adicionar detector pago como atalho. Para entrega, comunicar “verificador assistido com evidências e limites”, não “detector 100% certeiro”.
