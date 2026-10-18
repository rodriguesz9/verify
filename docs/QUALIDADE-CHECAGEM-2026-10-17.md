# Recuperação, correspondência, prazos e mídias — 17/10/2026

Continuação posterior: [revisão local de 18/10](RECUPERACAO-CONTEXTUAL-2026-10-18.md). Os resultados reais abaixo permanecem históricos; novos testes/replays offline não substituem sua porcentagem nem comprovam publicação.

## Meta e método

Meta solicitada: pelo menos 80% de decisões factuais corretas. Critério: esperado `supported`/`refuted` contra resultado efetivo, com **inconclusivos e erros no denominador**, sem repetir cada caso até acertar e sem reduzir critérios de evidência para atingir um número.

Manifesto definido antes da rodada: [12 controles textuais](../backend/tests/fixtures/validation/text-quality-2026-10-17.json), oito já usados no desenvolvimento e quatro adicionais com referência pública. Os quatro adicionais não constituem corpus independente representativo. Resultados dos oito anteriores precisam ser comparados separadamente ao checkpoint [online-v3](PESQUISA-ONLINE-2026-10-17.md), que obteve 3/8 acertos e 5/8 abstenções.

O índice de execução permanece congelado durante as chamadas da rodada `quality-v1`: `0ccd735b941d7a5ef5cf8600446693d7ec23b1dc282394f8571fd8c5567491c8`. Abrange caminhos/conteúdos Python do backend e JS/JSX/CSS do frontend; não congela os provedores, dependências, quotas, páginas nem o índice de busca públicos.

## Correções implementadas

### Recuperação e publicação

- Propriedades explícitas de publicação podem trazer timestamp civil como `2022-09-08 14:32:00`, sem fuso. O parser agora preserva o dia escrito, sem inventar fuso nem aceitar data arbitrária de URL/atualização. O HTML público capturado da Folha reproduziu essa perda de metadados.
- O segmentador mantém `Art. 1º` junto à disposição literal. Não funde artigos diferentes, não reescreve a fonte e não transforma título em texto probatório.
- Falhas de rede, HTTP 401/403, formatos não suportados e corpo ausente continuam sendo falhas, não prova de falsidade. Não houve contorno de bloqueios.

### Correspondência contextual

- Referência literal próxima pode identificar número/data de diploma e artigo numerado, enquanto o teor continua exigindo corpo efetivamente recuperado. Guarda exige identidade de número, data, artigo, objeto e negação; rejeita referência negada, rumor, fabricação, simulação e instruções. Em `quality-v1`, exigia duas famílias também nesse caso.
- Ortografia histórica explícita (`extincta`/`extinta`, `Brazil`/`Brasil`) e flexão da declaração não devem inutilizar citação do mesmo conteúdo. Troca de objeto, país, lei, artigo ou data continua bloqueada.
- Decisão financeira só ganha ligação temporal quando o próprio verbo concluído é seguido de dia relativo explícito e compatível com publicação (por exemplo, “reduziu nesta quarta-feira (18)”). Publicação isolada, data de outro anúncio ou promessa futura não datam a decisão.
- O comparador recebe explicação dos vínculos de divulgação, período anual e artigo. Todos os IDs/citações e guardas continuam pertencendo ao servidor.

### Planejamento e prazos

- Planejador tem até 45 segundos compartilhados entre Gemini e alternativa gratuita OpenRouter, em vez de 30. Pipeline reserva 20 segundos do teto de recuperação para busca/leitura; não deixa planejamento consumir silenciosamente o prazo todo.
- Plano vazio/timeout não suprime toda pesquisa adicional: um slot não usado pode executar uma consulta neutra sem filtro, derivada somente da entrada original. Essa consulta é identificada como **determinística**, não atribuída à IA.
- Mantidos no máximo cinco buscas, dez tentativas cumulativas de página, 105 segundos de recuperação e três documentos na comparação final. Falhas contam; sem rotação de chaves, novos serviços, plugins pagos ou repetição semântica até obter uma conclusão desejada.
- Cancelamento externo informa que detalhes individuais das tentativas não foram recuperados, em vez de presumir sucesso ou ausência de tentativa.

### Áudio quase silencioso

Inspeção local limitada precede os detectores de origem. Somente quase silêncio confirmado bloqueia envios Hive/Sightengine; falha/indisponibilidade não vira silêncio. ASR continua paralelo. Bytes, MIME e duração validada originais dos detectores são preservados. Silêncio não autentica voz e não prova falsidade.

## Testes automatizados

Revisão `quality-v1`: **837 testes backend, zero skips** no runner isolado/sem rede. **22 arquivos de teste frontend passaram, zero skips; build concluído**. Após as correções adicionais, `quality-v2` passou **868 testes backend em 28,624 s, zero skips**, além dos mesmos 22 arquivos frontend e build. **Fechamento local em 18/10, após o reparo de segurança: 872 testes backend/27,952 s, zero skips; 22 arquivos frontend, zero skips, e build passaram novamente.** Execuções complementares não são somadas como testes distintos. Nenhuma chamada externa foi permitida nessa suíte; PostgreSQL/produção não foram revalidados nesta rodada.

Novas regressões cobrem timestamps civis, datas conflitantes, artigo preservado, vínculo genérico de diploma, países/objetos/datas/artigos errados, identidade negada/fabricada, decisão futura versus concluída, plano vazio/timeout, silêncio real sem chamadas pagas, fala preservada e cancelamento da inspeção. Testes funcionais não medem porcentagem geral de veracidade.

## Orçamento de revalidação de mídia

Nova autorização explícita do titular em 17/10: até **US$ 0,05 adicionais do saldo Hive existente**, sem recarga, cartão ou contratação. Contadores antigos preservados. Limite da nova rodada: seis requisições de imagem/quadro e cinco segundos arredondados de áudio, sem retry pago. Pelo [preço público consultado](https://thehive.ai/models/hive/ai-generated-and-deepfake-content-detection), teto nominal de US$ 0,049888889; reserva não é extrato de faturamento.

Controles: planta IA conhecida, fotografia NASA publicada, vídeo de still IA com três quadros, eSpeak de até cinco segundos, silêncio e arquivo de imagem inválido. Após timeout da planta, o sexto envio de imagem foi reservado para **outro controle IA** (café) na revisão seguinte, sem reenviar a planta nem devolver sua reserva. Impresso OCR será testado somente depois de esgotado o teto pago, sem chamada Hive. Foto publicada não é prova criptográfica de câmera; vídeo still não é face-swap/lip-sync nem geração de movimento; eSpeak não é controle de voz humana ou clonagem neural. OCR e transcrição têm métrica própria, não serão somados como acertos factuais.

Hugging Face permanece desativado. Só Hive está configurado para origem da voz: um sinal isolado não será apresentado como consenso de dois detectores. Baixo sinal na foto não será promovido a autenticidade comprovada.

## Resultados reais

### `quality-v1` — rodada encerrada, preservada

Dezoito pedidos reais pela interface local: 12 textos, cinco controles válidos de mídia e um arquivo inválido. Todos executados com o mesmo índice de código; 17 HTTP 200 e uma recusa esperada HTTP 422. HTTP 200 não é acerto factual.

| Controle textual | Esperado | Obtido | Tempo (s) |
| --- | --- | --- | ---: |
| Elizabeth II — data verdadeira | sustentado | sustentado | 7,435 |
| Elizabeth II — data falsa | refutado | refutado | 12,505 |
| DART — impacto | sustentado | inconclusivo | 35,017 |
| OMS — pandemia | sustentado | sustentado | 34,051 |
| IBGE — divulgação do PIB | sustentado | sustentado | 55,090 |
| Copom — direção/taxas falsas | refutado | inconclusivo | 39,703 |
| Copernicus — direção falsa | refutado | refutado | 36,588 |
| Artigo legal — declaração negada | refutado | inconclusivo | 22,980 |
| Webb — lançamento | sustentado | sustentado | 31,427 |
| Constituição — promulgação | sustentado | sustentado | 16,698 |
| Copa 2014 — vencedor falso | refutado | inconclusivo | 27,638 |
| Artemis I — ano falso | refutado | inconclusivo | 21,203 |

**12 textos: 7/12 corretos (58,3%), 5/12 inconclusivos (41,7%), nenhum conclusivo errado observado. Meta de 80% não atingida.** No subconjunto anterior de oito, 5/8 (62,5%) contra 3/8 (37,5%) no checkpoint `online-v3`. As condições externas/modelos não são congeladas; essa diferença não isola o efeito de cada alteração. Nos quatro adicionais, 2/4 corretos, 2/4 inconclusivos.

Falhas preservadas:

- DART: dez tentativas cumulativas de documentos, só uma família com passagem elegível; referências NASA não passaram pela seleção de trechos.
- Copom: plano adicional pediu apenas fontes primárias; páginas BCB dependentes de JavaScript não forneceram corpo utilizável. Essa rodada não foi um timeout global.
- Artigo legal: texto original efetivamente recuperado continha preâmbulo e `Art. 1º` na mesma frase; parser impedia o vínculo ao artigo. Mesmo após corrigir segmentação, a única família disponível não bastaria para a regra genérica de duas fontes.
- Copa: Gemini escolheu citações genéricas cujo contexto mencionava resultado, mas o trecho escolhido não demonstrava a contradição. Guarda recusou a conclusão; não transformamos contexto/título em prova.
- Artemis: oito corpos recuperados, nenhum elegível. A configuração dessa rodada não capturava corpos dos quatro controles novos; não há diagnóstico local suficiente para atribuir a causa a uma guarda específica.

### Mídias em `quality-v1`

| Controle | Resultado real | Alcance |
| --- | --- | --- |
| Silêncio WAV/2 s | 0,280 s; nenhuma chamada remota; leitura sem fala e detectores bloqueados por sinal insuficiente | Proteção funcional, não acerto de autenticidade |
| Planta IA conhecida | Sightengine IA 0,99; Hive timeout/15 s; Gemini OCR sem texto e visão respondeu | Sinal isolado, não consenso. Timeout permanece na contagem |
| Foto NASA | Hive IA 0,00012459 e Sightengine IA 0,001; ambos responderam | Sem sinal forte, não certificação de foto humana |
| Still IA em vídeo/5 s | Hive e Sightengine com sinal alto nos três quadros/0,5; 2,5; 4,5 s, em 3,578 s | Consenso sobre quadros; vídeo sem áudio; sem perícia de movimento/identidade/lábios |
| eSpeak/5 s | Hive respondeu com sinal forte; AssemblyAI transcreveu, 4,341 s | Um único detector de voz; transcrição contém erro e exige conferência |
| PNG inválido | HTTP 422, 0,026 s; nenhuma chamada remota | Validação de formato, não amostra factual |

AssemblyAI retornou “Mãe, caí na rua e perdi meu celular. Faz um pixu da gente, tá bom?”. A interface pediu conferência, e foi escolhido “Ver só sinais da mídia”; não houve checagem factual da transcrição nem correção silenciosa. Não calculamos fidelidade ASR sem referência alinhada do recorte. A ausência de fala humana autorizada e de corpus diverso impede medir acurácia geral de voz/imagem/vídeo.

### Revisão seguinte

As correções posteriores são medidas em `quality-v2`, com novo índice de código `4c6691f82d78ee7493ed88f6000af64f0a25d05254e7b51f66f52037c23ff921` e os mesmos 12 textos, sem repetir controles até acertar:

- Planejamento de duas consultas apenas primárias/abertas tem a segunda direcionada ao filtro editorial, com escopo solicitado/executado e motivo registrados. Uma consulta única primária pode usar um slot restante para busca neutra editorial. Consulta exatamente repetida não é reenviada: se a busca neutra editorial já ocorreu, pode haver uma busca neutra aberta inédita. Nenhum terceiro slot extra, novo serviço ou voto de snippet.
- Segmentador separa introdução normativa explícita (“a Lei seguinte: Art. ...”) do artigo literal, mantendo o preâmbulo como contexto. Texto livre, título e legenda não viram disposição legal.
- A exceção já existente para registros institucionais originais passa a aceitar **apenas a leitura do que um artigo numerado declarou**, em publicação original da Câmara: host/rota originais, número/data coincidentes em rota/cabeçalho/artigo, corpo recuperado, negação/objeto compatíveis. Não aceita réplica, comentário, URL de exemplo, texto atualizado, fonte submetida, vigência atual ou efeitos sociais. Continua explicitamente **uma fonte primária**, nunca duas confirmações independentes; regra genérica de outras afirmações não foi reduzida.
- Hive passa de 15 para **45 segundos totais** por tentativa; camada externa tem 50 segundos. Prazo total é compartilhado entre fases da rede, não 45 segundos por fase. Outros detectores mantêm 18 segundos. Não há retry, reposição de reserva nem criação automática de novo trabalho.
- Interface aguarda até 240 segundos em mídia, cobrindo validação/transcrição/camadas limitadas; autenticação mantém 60 e PDF 30 segundos. Espera maior não garante resposta nem muda o conteúdo de uma decisão.

`quality-v2` foi interrompida após dois pedidos: o instrumento local de diagnóstico atingiu seu teto cumulativo de 240 documentos e lançou erro na recuperação. Ambos permaneceram inconclusivos (18,616 s e 4,163 s), com registros preservados. Não foi atribuída essa falha às APIs nem descartada como se os pedidos tivessem funcionado. O limite de armazenamento de diagnósticos foi aumentado para 600, mantendo todos os registros e reservas. `quality-v2b` repetiu o manifesto inteiro com **o mesmo código/fingerprint da aplicação**, sem reajustar rótulos ou evidências; só o instrumento de teste mudou.

### `quality-v2b` — encerrada

Quinze pedidos, todos HTTP 200, sem alteração de código durante a execução: os mesmos 12 textos, outro controle IA, impresso para OCR e um link público. Nos últimos controles houve duas abas simultâneas. O delta global de chamadas por pedido pode abranger chamadas da outra aba: **não somar nem atribuir esses deltas individualmente**. Status/citações de cada relatório e o diário cumulativo de transporte permanecem fontes apropriadas para suas respectivas dimensões.

| Controle textual | Obtido em v1 | Obtido em v2b | Tempo v2b (s) |
| --- | --- | --- | ---: |
| Elizabeth II — data verdadeira | sustentado | sustentado | 71,962 |
| Elizabeth II — data falsa | refutado | refutado | 24,930 |
| DART | inconclusivo | inconclusivo | 34,549 |
| OMS | sustentado | sustentado | 14,686 |
| IBGE/PIB | sustentado | inconclusivo | 46,705 |
| Copom | inconclusivo | inconclusivo | 24,579 |
| Copernicus | refutado | refutado | 58,362 |
| Artigo legal | inconclusivo | refutado | 14,190 |
| Webb | sustentado | inconclusivo | 67,708 |
| Constituição | sustentado | inconclusivo | 27,266 |
| Copa 2014 | inconclusivo | inconclusivo | 36,194 |
| Artemis I | inconclusivo | inconclusivo | 48,099 |

**Última rodada completa: 5/12 corretos (41,7%), 7/12 inconclusivos (58,3%), zero conclusivos errados observados. Meta de 80% NÃO atingida.** Nos oito anteriores, permanece 5/8; nos quatro adicionais, caiu de 2/4 para 0/4. A mediana textual subiu de 29,533 para 35,372 segundos. Não selecionar apenas a melhor rodada, somar versões como se fossem um benchmark único ou apresentar 5/5 conclusivos como acurácia de 100%.

O artigo legal passou a ser contradito pela citação real `Art. 1º É declarada extincta desde a data d'esta Lei, a escravidão no Brazil.`. A interface identificou uma fonte primária original, não duas confirmações. Leitura DOM em viewport de 390 px não apontou largura excedente (`scrollWidth=375`), mas a captura de tela reduzida desse ensaio não permite homologar a responsividade visual completa. Viewport foi restaurado.

Resultados auxiliares:

- **Café IA:** 45,683 s; Sightengine IA 0,99; Hive novamente timeout, agora com 45 segundos totais; Gemini visual respondeu e OCR não encontrou texto. **Aumentar prazo não resolveu a indisponibilidade nesse controle.** Sem retry, sem reposição de reserva, sinal isolado preservado.
- **Impresso OCR:** 56,720 s; Tesseract leu `CONTROLE DE TESTE / Nao pague taxa para liberar seu Pix. / Valor: R$ 123,45 / Data: 03/10/2026`. O próprio impresso usa `Nao` sem acento. Negação, valor e data preservados; a UI pediu conferência. Hive não recebeu arquivo (teto pago esgotado); a visão Gemini ficou indisponível. Não foi feita checagem factual automática desse texto fictício.
- **Link NASA/Webb:** leitura pública funcional, HTTP 200/51,267 s; data de lançamento presente no texto lido, mas página inteira inconclusiva. OpenRouter retornou saída inválida para extração e Gemini fez o fallback com sucesso. Localização de trechos em outras páginas não foi promovida a verdade do artigo completo.

Nova autorização Hive consumida em reservas: seis imagens/quadros e cinco segundos de áudio, sete pedidos, cinco respostas e dois timeouts. Contagem inclui falhas, não equivale a extrato. Nunca houve contratação/recarga. Não há homologação estatística das modalidades de mídia: faltam vozes humanas, vídeos reais autorizados e corpus independente/diverso, e continuam ausentes acesso de voz Sightengine e endpoint HF.

### Diagnóstico das abstenções e trabalho restante

1. **Recuperação temporal:** PIB v2b recuperou uma CNN anual compatível, EBC de outros períodos e fonte IBGE sem corpo utilizável; a EBC correta de v1 não apareceu nas pistas. Buscar/rankear melhor por divulgação versus ano de referência, sem acrescentar datas corretas conhecidas ou URLs por caso.
2. **Corpos institucionais estruturados:** Copom teve páginas BCB sem corpo por dependência de JavaScript. EBC foi lida integralmente, inclusive na URL terminada em `%2C`; isso não causou a falha. Trecho dizia elevação de 0,25 ponto para 10,75%, sem a transição/data explícita exigida. Precisam ser estudados adaptadores públicos estruturados e contratos de decisão/data/percentual, não relaxamento geral de números.
3. **Correspondência PT/EN:** Webb tem data explícita em NASA, mas a ligação de nomes ainda não equipara todos os componentes de “Telescópio Espacial” a “Space Telescope”. A outra fonte elegível era UOL; Folha e Brasil Escola não são famílias independentes. Tradução tipada e testes adversariais são pendências concretas de código.
4. **Autoria/metadados fundidos:** Constituição apresentou data de autoria/2015 junto ao corpo/1988 em EBC, impedindo comparação segura. CNN trazia `1888` no corpo capturado, enquanto a legenda dizia `1988`; não corrigimos silenciosamente a fonte. A rodada anterior recuperou outros artigos. Melhorar classificação de blocos de metadados, preservando discrepâncias reais.
5. **Relações tipadas de evento:** Copa teve famílias elegíveis, mas o modelo citou contexto da final, sem o vencedor na própria citação; guarda recusou. Artemis recuperou fonte com 16/11/2022, porém refutação por data diferente só cobre eventos singulares previstos no contrato atual; lançamento não é um deles. São limitações de comparação, não falhas das chaves. Expandir relações competição/vencedor/categoria/ano e missão/lançamento/identidade com novos controles positivos e negativos, sem liberar qualquer diferença de ano como refutação.
6. **Prazos externos:** duas imagens Hive excederam 15/45 segundos; uma foto, três quadros e a voz responderam. Investigar latência/modalidade síncrona com o fornecedor antes de autorizar novos envios. Visão Gemini e saídas OpenRouter também têm indisponibilidade/erros semânticos; manter cobertura e fallback explícitos.
7. **Validação independente:** definir corpus novo rotulado, diferentes fontes/épocas/idiomas, versões comprimidas e controles fora do desenvolvimento. Os 12 textos atuais não permitem prometer 80% geral. Estabilizar recuperação e medir precisão/cobertura/latência antes de nova publicação.

### Reparo de segurança após a medição

A revisão independente encontrou um caso em que um aviso **depois** do artigo dizia que a reprodução era fabricada/hipotética, mas ainda era possível usar a exceção de registro original. Reparo posterior rejeita declaração explícita sobre esta reprodução/artigo corrente em qualquer posição, sem bloquear mera discussão hipotética de outro artigo nem o rodapé “não substitui o original”. Política final `2026-10-17.4`.

Esse reparo é posterior ao fingerprint das rodadas acima. Índice final de código `637248a67c3b0a5d035f58ba9cdeb710bf611450642cbd0d4631b997f611f0e5`, política `2026-10-17.4`. Não foi inventada nova porcentagem para a versão final. Replay **offline**, com transporte bloqueado, remapeou somente as nove citações literais já aceitas nos cinco controles conclusivos de `quality-v2b`: todos os cinco mantiveram status; zero busca, fetch ou API real. Modelo simulado apenas selecionou os mesmos URL/trecho/relação com novos IDs internos. Isso é regressão sobre evidências congeladas, não nova checagem factual, rodada de interface ou medição de precisão. [Resumo sanitizado com todos os controles](validation-quality-2026-10-17.json). Logs brutos, capacidades de exportação e respostas privadas não são publicados.

## Retomada em produção

Esta rodada é local, com banco descartável, sem alteração do `.env` privado, Railway, Vercel ou banco de produção. Os prazos Hive/interface são definidos no código; não existe nova chave nem variável paga a cadastrar para recebê-los.

Roteiro operacional futuro, condicionado à revisão identificada, validação correspondente e autorização de publicação: ao reativar o Railway, conferir as variáveis já suportadas antes de publicar: `SOURCE_CROSSCHECK_ENABLED=true`, `SOURCE_CROSSCHECK_PRIMARY_PROVIDER=gemini`, `SOURCE_CROSSCHECK_TIMEOUT_SECONDS=60`, `SOURCE_CROSSCHECK_SEARCH_LIMIT=3`, `SOURCE_RESEARCH_ENABLED=true`, `GEMINI_MODEL_NAME`/`GEMINI_MEDIA_MODEL_NAME` válidos no projeto e `GEMINI_REQUEST_TIMEOUT_SECONDS=60`. OpenRouter continua exclusivamente gratuito; Serper precisa ter quota disponível. Chave existente não garante acesso ao modelo, créditos ou resposta em cada pedido. Esta documentação não comprova deploy nem autoriza novos gastos.

Não copiar o harness QA para produção: contadores, rotas diagnósticas, usuário e SQLite são descartáveis. Não publicar os JSONL brutos, HTMLs locais nem tokens de relatório. Conferir segredos estáveis, origens, cookies, migrações e ferramentas conforme [retomada do Railway](REATIVAR-RAILWAY-2026-10-13.md), preservando banco e volume. Testes locais não confirmam o deploy nem a capacidade de carga de múltiplas réplicas.
