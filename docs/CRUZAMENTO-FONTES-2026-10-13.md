# Verify — cruzamento fundamentado de fontes

Registro de 13/10/2026, horário de Brasília. O usuário informou que o Railway expirou e autorizou testes locais, commit e envio ao GitHub após os testes. Não houve renovação, contratação, recarga, alteração de variáveis remotas nem acesso ao banco de produção. Publicar código não demonstra retorno da hospedagem.

Este é um registro histórico. Recuperação, provedor primário e controles foram revistos em 14/10; para o funcionamento atual, consulte [validação de APIs](VALIDACAO-APIS-2026-10-14.md) e o [guia de retomada atualizado](REATIVAR-RAILWAY-2026-10-13.md).

## Dois caminhos factuais

Google Fact Check continua recuperando checagens editoriais publicadas, avaliadas pela política existente de correspondência literal e famílias distintas. Quando faltam checagens correspondentes, o novo caminho pode comparar a afirmação original com **trechos completos dos corpos de páginas recuperadas**, usando as APIs existentes de busca e leitura/comparação.

O modelo propõe relações com IDs de trechos; o servidor verifica citações, URLs, contexto, entidades, negação, datas, valores e famílias antes de aceitar apoio/refutação. Concordância de IAs, título, snippet, reputação do domínio e notícias apenas relacionadas não são prova. Possíveis resultados: corroborada/refutada nas fontes consultadas, conflito, resultado misto ou evidência insuficiente.

**Os controles públicos desta etapa continuaram inconclusivos.** Não foi demonstrado que a mudança resolva todos os casos dos colegas ou produza classificações conclusivas reais. A melhoria implementada é um segundo caminho fundamentado e rastreável; precisão/recall em notícias reais permanecem por medir.

## Limites e salvaguardas

| Etapa | Teto e regra |
| --- | --- |
| Entrada | Até 5.000 caracteres, sem reformular afirmações para obter outro rótulo. |
| Busca de páginas | Uma consulta literal completa; no máximo uma segunda consulta com a mesma frase e filtro de sites curados, se a primeira responder e indicar menos de duas famílias elegíveis. Sem retry de quota/erro nem corte da frase. |
| Recuperação | Até três páginas, 2 MiB/oito segundos por página e 50.000 caracteres de corpo. Busca/leitura compartilham 30 segundos quando a camada está habilitada. |
| Seleção | Prioriza famílias distintas; página enviada e sua família não confirmam independentemente. Wikipedia/hosts não curados não votam. |
| Comparação | Até cinco segmentos, três documentos, oito passagens por documento, 18.000 caracteres de corpos no prompt; sentença central até 1.200 caracteres, contexto adjacente limitado. |
| Modelo | Uma comparação OpenRouter gratuita; Gemini pode ser alternativa em ausência de configuração ou falha de transporte/quota, no mesmo prazo total de 60 segundos. Configuração inválida/JSON inválido abstêm, sem repetição para buscar conclusão. |
| Contrato | IDs/URLs/horário/sentenças/famílias são do servidor. Citação inventada, campos extras, IDs duplicados, JSON parcial ou truncado não viram prova. |
| Decisão | Duas famílias elegíveis com evidência correspondente por afirmação; duplicatas, mesmo grupo e crédito de agência não contam duas vezes. Independência real não é certificada. |
| Cobertura | Parte confirmada não aprova texto inteiro. Mais de cinco segmentos, qualificadores não cobertos, conflito e ambiguidade exigem abstenção/revisão. |

`_documents` é removido antes de publicar relatório, histórico e snapshot; só trechos/contexto selecionados são retornados. A seleção de links precede leitura: crédito de agência, duplicação ou texto inutilizável encontrados depois podem reduzir cobertura sem disparar recuperação ilimitada.

Correções defensivas da revisão:

- Metadata de publicação/atualização não é data do evento. Elementos de data editorial são excluídos; data narrativa inline é preservada. Morte/nascimento com data exigem construção lexical explícita ligada ao predicado; homenagem, anúncio ou outro evento não emprestam sua data. Construções nominais/indiretas podem abster.
- Um desmentido vizinho sobre taxa/outro assunto não refuta a sentença central. Negação/desmentido precisam respeitar o escopo da alegação; falsidade de conjunto não refuta uma parte isolada.
- Ordinais no nome são comparados explicitamente: Elizabeth I não é Elizabeth II; não são apagados números arbitrários. Negação, moedas, unidades e valores são preservados.
- Datas de pagamentos repetidos não são automaticamente o mesmo evento; previsão não confirma ocorrência concluída. Instruções prescritivas médicas/financeiras/jurídicas não recebem aprovação automática; afirmações declarativas de alto risco conservam limitações e orientação de confirmação especializada.
- Alertas de golpe e checagens editoriais já decisivas não são cancelados por apoio parcial. Relatórios antigos não são reanalisados silenciosamente.

São regras lexicais conservadoras, não prova formal de compreensão semântica. Fontes/modelos/regras podem errar; cópias sem crédito podem esconder dependência. HTML estático não resolve toda visibilidade CSS/JavaScript, proteção ou paywall. Não há precisão universal garantida.

## Modalidades, relatório e PDF

Texto, link, lote e texto explicitamente conferido após OCR/transcrição usam o novo caminho. Link preserva o trecho extraído: uma conclusão sobre trecho limitado não aprova o restante da página.

**OCR/ASR automático não conferido** mantém o caminho anterior, sem comparação nova, segunda busca ou corpos adicionais para ela. Flag propagada à recuperação mantém uma busca/prazo de 20 segundos. Conferência humana é outra etapa e não comprova fidelidade da leitura ou origem da mídia.

Políticas de origem de imagem/voz/vídeo permanecem separadas e não foram rehomologadas nesta etapa. Texto corroborado não certifica foto, identidade ou voz.

A interface mostra afirmação, relação do trecho, documento/link/contexto e horário da consulta. Fornecedores ficam nos detalhes recolhidos. Documentos não são apresentados como duas ClaimReviews nem como porcentagem de certeza.

`score=0` nas decisões desse caminho é somente compatibilidade com a coluna inteira legada. `score_semantics=not_calibrated_source_corroboration` faz interface/histórico/estatísticas omitirem esse valor; não há índice calibrado nem migração destrutiva.

PDF reutiliza análise assinada sem nova consulta/detector. Distingue documentos de checagens, preserva observações insuficientes/contexto/exclusões/limites e até seis evidências por afirmação. Trecho já apresentado não vira outra fonte independente; omissões além dos limites são declaradas.

## Variáveis para a retomada

Guia completo de banco/volume, Docker, cookies, CORS e URL pública: [reativação Railway](REATIVAR-RAILWAY-2026-10-13.md). Conferir no backend da revisão correspondente:

```dotenv
SOURCE_CROSSCHECK_ENABLED=true
SOURCE_CROSSCHECK_TIMEOUT_SECONDS=60
SOURCE_CROSSCHECK_SEARCH_LIMIT=2
```

Defaults true/60/2. `SEARCH_LIMIT` aceita 1/2; 1 desliga só a segunda consulta. `TIMEOUT` aceita 10–60 segundos para toda comparação, não por fornecedor.

Integrações existentes precisam de acesso/cota válidos: `SERPERAPI_KEY` para páginas (**não** `SERPAPI_KEY`); `OPENROUTER_API_KEY`, `OPENROUTER_ENABLED=true`, `OPENROUTER_MODEL=openrouter/free` e limite coerente; `GEMINI_API_KEY`/modelo explicitamente configurado e acessível, como Lite, para alternativa; `GOOGLE_FACT_CHECK_KEY` preserva o caminho editorial. Falta de ClaimReviews não bloqueia documentos utilizáveis.

Não copiar `.env` inteiro, trocar PostgreSQL por SQLite, rotacionar JWT/HMAC válidos desnecessariamente nem expor segredos em `VITE_*`. HF continua desligado; Hive conserva somente autorização/tetos já acordados. Nenhuma API paga nova é requisito desta mudança.

## Testes e controles reais

Regressões offline usam HTTP bloqueado, dotenv/credenciais ignorados e bancos descartáveis. Validam regras/respostas, citações fabricadas, fonte submetida/dependência, temporalidade, valores/negação, conflito, refutação, cobertura, integração com ClaimReview, histórico e PDF. Não medem precisão real.

Suíte final backend: **637 testes passaram**, em Docker/Python 3.11, rede desligada, SQLite descartáveis, sem skips ou chamadas HTTP inesperadas (11,746 s). Frontend: **181 testes passaram**, com renderização dos componentes nos cinco estados; build de produção passou, 1.977 módulos. Não foram instaladas novas dependências/SDKs nem alterada a paleta. Não somar execuções repetidas SQLite/PostgreSQL como casos distintos; CI/deploy devem ser confirmados no commit publicado.

Controles pela interface anônima local, banco descartável, sem chaves de autenticação/banco de produção/Hive. Gemini configurado Lite; OpenRouter gratuito. Limites de chamadas persistiram no mesmo diário após reinício, sem reset de orçamento. Harness só permite leitura HTTPS de hosts curados, mais restritivo que o fetch público normal.

| Controle | Observação real | Não comprova |
| --- | --- | --- |
| “Elizabeth II morreu em 8 de setembro de 2022.” — primeira execução | JSON/200, Google sem ClaimReviews, busca respondeu; um corpo lido, comparação não iniciada. | Confirmação factual; encontrou limite de recuperação/alias. |
| Mesma frase — única rechecagem após busca direcionada/ordinal | JSON/200; três páginas selecionadas, duas lidas; OpenRouter executou comparação; um trecho apresentado; inconclusivo. | Validação final: trecho incorporava metadata/data; auditoria posterior acrescentou defesas. Não reutilizar esse trecho como prova de acerto. |
| “Elizabeth II morreu em 9 de setembro de 2022.” — negativo | JSON/200; três páginas selecionadas, duas lidas; uma família elegível; comparação não iniciada; inconclusivo. | Refutação binária: data falsa não foi aprovada, mas também não refutada conclusivamente. |

Ground truth: [comunicado real datado de 8/9/2022](https://www.royal.uk/statement-king-following-death-queen?page=2). Negativo é alteração de teste, não notícia real. Textos/arquivos exatos dos colegas não foram fornecidos.

Transporte: **4 OpenRouter, 3 Google Fact Check, 7 Serper e 5 leituras públicas**, chamadas registradas HTTP 200. Modelos gratuitos efetivos incluíram `nvidia/nemotron-3-super-120b-a12b:free`, `liquid/lfm-2.5-2.6b:free`; comparação `dots-studio/dots-3-note-preview:free`. Disponibilidade é variável. **Zero Gemini, Hive, Sightengine, AssemblyAI e Hugging Face nesta rodada**; Gemini não foi necessário como fallback, não foi revalidado realmente.

Exportação do negativo PDF/200/no-store, sem novas chamadas. Arquivo localizado nos downloads; duas páginas extraídas/renderizadas/inspecionadas sem corte/sobreposição. Foi antes da seção final de evidências parciais, coberta por regressão offline separada. Não homologa todos os PDFs, mídia, cookies ou recuperação de contas.

A seção final também foi renderizada/inspecionada em PDF de duas páginas com fonte/contexto explicitamente fictícios, exclusão e estado insuficiente preservados. É controle de apresentação offline, não chamada real de fornecedor ou veredito correto. A retomada posterior da interface local foi bloqueada pela política do navegador; não houve contorno ou novas chamadas a APIs para repetir os ensaios.

Não calcular precisão nesses ensaios: dois repetem a mesma afirmação, controles abstiveram, nenhuma comparação conclusiva real foi demonstrada. Há cobertura funcional e gargalo real documentado, não “todas as APIs corretas”.

## Pendências para aceite

- Titular reativar hospedagem, confirmar volume/contas/histórico e revisão servida antes de testar produção.
- Validar política final em corpus real independente com duas famílias utilizáveis, datas de evento explícitas, negativos próximos, paráfrases, longos/citações/relativos; inconclusivos no denominador.
- Melhorar seleção/extração por casos registrados, sem baixar critérios para produzir rótulos na banca.
- Revalidar modalidades/APIs autorizadas em arquivos próprios/consentidos. Chave presente não comprova acesso/cota/acerto.
- Homologar login cross-site, isolamento de contas, persistência e exportação no domínio publicado; UI nesta rodada foi anônima.
- Retenção/exclusão, backups restauráveis, monitoramento e limites compartilhados entre réplicas permanecem no plano; contador por processo não é teto financeiro global.

Usar [roteiro da banca](ROTEIRO-BANCA.md) declarando alcance/abstenção. Registros e planos anteriores são históricos; não ensaiar até selecionar apenas resultados favoráveis.
