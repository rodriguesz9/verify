# Validação real pela interface — 16/10/2026

## Resultado executivo

**Checagem factual geral ainda não homologada.** Seis controles textuais, três verdadeiros/três falsos autorados, ficaram inconclusivos. Abstenção não é veredito falso nem acerto de classificação. Mídias artificiais conhecidas receberam sinais de IA; fotografia/filmagem reais não receberam sinais fortes nem certificado de autenticidade. Voz teve sinal isolado, erro de transcrição e cobertura limitada pelo orçamento.

Bateria exploratória pequena, não aleatória, com controles reutilizados e mudanças durante a execução. **Não estima precisão populacional nem é benchmark independente da versão final.** Nenhum limiar ou requisito de duas famílias foi reduzido para obter respostas desejadas.

Execução local: navegador → formulário → API → provedores reais → conferência/relatório. Banco/autenticação descartáveis, sem banco produtivo. **19 cenários/etapas em 16 requisições da aplicação:** seis textos (quatro em lote), duas imagens, dois áudios, dois vídeos, duas páginas públicas, OCR, texto conferido, duas rejeições de entrada e PDF. Não são 19 conteúdos independentes.

Base: `558867c7def6be1ab5670dbd7dfce70ae81c00b0`. Dois textos antes da correção de recuperação, quatro depois. Correções de meses abreviados verificadas offline após a bateria, **sem nova homologação factual por APIs reais**.

## Números e definição

Medida: **conclusões compatíveis com a referência / todos os controles rotulados enviados**. Abstenções ficam no denominador. HTTP 200 e sinal isolado não contam como classificação correta.

| Dimensão | Controles | Conclusivos corretos | Inconclusivos/indisponíveis | Corretos e conclusivos / total |
| --- | ---: | ---: | ---: | ---: |
| Texto — veracidade | 6 | 0 | 6 | 0% |
| Imagem — origem artificial | 2 | 1 | 1 | 50% |
| Áudio — origem sintética | 2 | 0 | 2 | 0% |
| Vídeo — origem dos quadros | 2 | 1 | 1 | 50% |

Não interpretar como precisão dos fornecedores. Na foto/vídeo reais, ausência de sinal não prova autenticidade. Áudio humano **não recebeu detecção paga de origem**, pois o teto de áudio estava consumido; sua linha mede cobertura ponta a ponta, não erro/especificidade do Hive. Em imagem/vídeo houve um acerto de um entre os classificados de cada modalidade; um positivo reutilizado não sustenta “100% de precisão”.

Links: sem percentual de acerto, pois não foi anotada a verdade de todas as afirmações dos artigos. Um falhou no acesso; outro gerou relatório inconclusivo/extração parcial. Página oficial não é confirmação independente de si mesma.

## Corpus factual

Referências anteriores às previsões, separadas da descoberta automática. Falsos são alterações autoradas para teste, não boatos virais coletados.

| ID | Referência | Observado |
| --- | --- | --- |
| C01 — DART/26-09-2022 | Verdadeiro: impacto em Dimorphos, [NASA](https://www.nasa.gov/news-release/nasa-confirms-dart-mission-impact-changed-asteroids-motion-in-space/) | Inconclusivo; zero famílias utilizáveis |
| C05 — OMS/11-03-2020 | Verdadeiro: caracterização de pandemia, [OMS](https://www.who.int/news-room/speeches/item/who-director-general-s-opening-remarks-at-the-media-briefing-on-covid-19---11-march-2020) | Inconclusivo; uma família utilizável |
| C02 — temperatura de 2024 “abaixo” | Falso: direção invertida, [Copernicus](https://climate.copernicus.eu/global-climate-highlights-2024) | Inconclusivo |
| C03 — PIB/3,4% divulgado em 07-03-2025 | Verdadeiro na divulgação, [IBGE](https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/42774-pib-cresce-3-4-em-2024-e-fecha-o-ano-em-r-11-7-trilhoes); não afirma ausência de revisão posterior | Inconclusivo |
| C04 — Selic/18-09-2024 “reduziu” | Falso: ação/valores invertidos, [BCB](https://www.bcb.gov.br/publicacoes/atascopom/18092024) | Inconclusivo |
| C06 — Lei Áurea com “não declarou” | Falso: negação inserida, [texto da lei](https://www.planalto.gov.br/ccivil_03/leis/lim/lim3353.htm) | Inconclusivo |

NASA/OMS/Copernicus tiveram corpos consultados na pesquisa de referência. IBGE recusou abertura direta; BCB depende de JavaScript, com corroboração editorial nas notas do corpus de 14/10. Referências **não foram injetadas no backend**. Planalto abriu na ferramenta de pesquisa, mas falhou no transporte local.

## Mídias e leitura

| Controle | Origem | Observado / limite |
| --- | --- | --- |
| I01 — zínia | Fotografia Scott Kelly/NASA de 2016, [publicação](https://www.nasa.gov/image-article/first-flower-grown-space-stations-veggie-facility-2/), fixture existente | Dois detectores sem sinal forte; origem não certificada. Gemini visual respondeu |
| I02 — planta | Fixture gerada por IA em 07/10, origem conhecida | Hive/Sightengine concordaram sobre IA; Gemini visual 503 |
| A01 — sintético/5 s | Recorte eSpeak da demonstração, controle reutilizado | Hive: sinal alto de 99,1%, não calibrado, sem segundo detector. AssemblyAI retornou “pixu da gente, tá bom?”, erro não corrigido silenciosamente. Interface pediu conferência |
| A02 — humano/15,65 s | Rennê Luduvico/LibriVox, artigo 1 da DUDH em português, gravação de 2006, domínio público, edição declarada; [arquivo/licença](https://commons.wikimedia.org/wiki/File:Universal_Declaration_of_Human_Rights_-_bra_-_rljb_-_Art1.ogg) | Transcrição coerente com artigo; detecção de origem indisponível por teto Hive/Sightengine voz desligado. Sem escuta/transcrição independente, não publicar WER nem fidelidade exata |
| V01 — histórico/5 s | [NASA/Apollo 11](https://www.nasa.gov/wp-content/uploads/static/history/alsj/a11/video11.html), TV digitalizada, clipe Ken Glover; recorte 20–25 s, H.264/640 px, sem áudio | Três quadros sem sinal forte; nenhuma voz inventada. Não autentica vídeo inteiro |
| V02 — foto IA em vídeo/5 s | I02 repetida, H.264/640 px, sem áudio | Concordância em 0,5 s; sinais isolados em 2,5/4,5 s. **Não testa movimento generativo, troca de rosto ou lip-sync** |
| OCR | Gráfico impresso não generativo, fixture `validation/ocr/impresso-base.png` | Leitura exata de 4/4 linhas no único controle: `Nao`, `R$ 123,45`, `03/10/2026` preservados. Não é precisão geral de OCR |

Solicitados dois quadros por vídeo na QA; produto aplica mínimo documentado de três. Teto financeiro independente continuou ativo: vídeo real consumiu três imagens Hive; artificial teve Hive só no primeiro quadro, Sightengine nos três. Não houve aumento/reset do limite.

## APIs: disponibilidade não é acerto

| Integração | Rede | Ressalva |
| --- | --- | --- |
| OpenRouter gratuito | 8 HTTP 200; 1 solicitação sem resposta completa no prazo | Extração/OCR exercidos; artigo longo terminou em timeout. `openrouter/free`, preço máximo zero; sem comparação factual homologada |
| Gemini `gemini-3.1-flash-lite` | 1 HTTP 200; 5 HTTP 503 | Visão funcionou na foto real; demais falharam. Mais timeout não resolve necessariamente 503 imediato |
| Google Fact Check | 16 HTTP 200 | Sem correspondência utilizável nos controles factuais; resultados não relacionados foram excluídos |
| Serper notícias/web | 30 HTTP 200 | Recuperação insuficiente; teto QA atingido no texto conferido. Não confundir com credencial inválida de produção |
| Sightengine imagem | 8 HTTP 200 | Duas imagens/seis quadros; voz `ai_speech` não habilitada/validada |
| Hive v3 | 7 HTTP 200 | Seis imagens/quadros e um áudio/5 s; modelo IA/facial não conta como dois fornecedores |
| AssemblyAI | 9 HTTP 200, dois trabalhos | Duas transcrições, uma com erro crítico. Nove requisições não são nove transcrições. ASR não detecta clonagem |
| Páginas públicas | 30 tentativas, incluindo redirecionamentos/falhas | Corpos responderam; também houve 403, falhas de conexão e JavaScript. Não remover TLS/DNS/IP/SSRF |
| Hugging Face | Desativado | Sem endpoint gratuito compatível homologado; não testado |

Hive: seis imagens a US$ 0,006 e cinco segundos a US$ 10/h = **estimativa nominal de US$ 0,049888889**, dentro de US$ 0,05 autorizado. [Preços públicos](https://thehive.ai/pricing). Fatura/saldo não auditados. Reservas antes da rede, diário persistente/lock; sem recarga, contratação ou repetição paga. Reinício preservou contadores.

## Defeitos corrigidos

1. **Busca estreita:** NASA restrita a `science.nasa.gov`; assuntos fora de nascimento/morte/lançamento não usavam terceira consulta. Agora fontes primárias/editoriais recebem buscas separadas do texto literal, incluindo `nasa.gov`/Planalto. Mantidos três buscas, seis páginas, prazo, parada por quota e guardas. Quatro controles posteriores ainda inconclusivos: necessário, mas insuficiente para homologação.
2. **Datas fragmentadas:** `Sept. 26`/`Oct. 8` viravam segmentos separados, chegando a pesquisa por `26.`. Segmentador preserva mês abreviado seguido de número; comparador reconhece mês sem ignorar dia/ano. Testes incluem data errada, publicação, negação, valores, quebra de linha e frase seguinte. Verificação offline, não nova precisão real pós-correção.
3. **Vídeo ambíguo:** resumo juntava concordância/sinais isolados. Agora explicita tempos de cada estado. Conferido na interface sobre relatório real armazenado, sem repetir APIs ou alterar veredito.
4. **Lote com código interno:** `SUSPICIOUS` aparecia para inconclusivos. Agora português/estado apropriado, sem acusação automática. Cartões são botões acessíveis por teclado; abertura individual conferida.

Sem mudança de limiar, voto de Gemini visual, concordância de LLMs como prova ou certificado por pontuação baixa.

## Outros fluxos

- NASA: relatório/correspondência com a própria página, sem confirmação independente. Extração ainda mistura cabeçalho/legenda/corpo; apenas primeiros 5.000 caracteres. Artigo inteiro não homologado.
- Planalto: erro de consulta segura; consulta externa de cabeçalhos também expirou. Não há evidência de que trocar chave resolveria a rede.
- OCR: conferência gerou `/api/check-extracted-text`, com referência ao original, sem falso rótulo de golpe para `Nao pague`. Pesquisa posterior limitada pelo teto QA.
- URL privada: HTTP 400, mensagem compreensível, zero chamadas de provedores.
- Texto renomeado `.png`: HTTP 422 antes dos detectores, zero chamadas de provedores.
- PDF: clique retornou HTTP 200, cabeçalho `%PDF`, zero novas análises. Interface mostrou “PDF preparado”. Evento de download expirou: **salvamento/abertura do arquivo não confirmados**.

## Regressão e evidências

- **739 testes backend passaram**, com quatro integrações SQLite descartáveis, sem rede/chaves e sem skips finais. Não é nova homologação PostgreSQL/produção.
- Frontend: **20 arquivos de teste passaram**; não confundir arquivos com casos internos históricos. Build passou após alterações de frontend; `git diff --check` limpo.
- [Métricas sanitizadas](validation-ui-summary-2026-10-16.json): sem chaves, cookies, tokens de PDF/conferência, IDs remotos, artigos completos ou dados produtivos.
- Corpus/hashes/transcrições/diário/avaliador na pasta local `qa-real-ui-oct16.W8BxJZ`, fora do Git.
- Sem publicação Vercel/Railway nesta rodada. Testes não demonstram estado atual da hospedagem.

## Próximos critérios de conclusão

**P0 — texto:** melhorar descoberta/seleção sem privilegiar controles; separar metadados/legendas/afirmações; tratar siglas/paráfrases/contexto entre sentenças com testes adversariais. Guardas de sentença única têm baixa cobertura. Reavaliar em corpus novo/separado, medindo abstenções, falsos positivos/negativos e cobertura. Não substituir evidência ausente por memória de IA.

**P0 — disponibilidade:** revalidar Gemini após recuperação e OpenRouter em artigos longos, com prazo único/alternativa suportada, sem rodízio para contornar quotas. Uma resposta visual não homologa todas as modalidades.

**P0 — voz:** segundo detector com acesso/custo confirmados; gravações humanas autorizadas, dois geradores e diferentes compressões. Referência por escuta independente antes de WER. Preservar revisão humana de nomes, negações, datas, valores e pedidos financeiros.

**P1 — mídias:** corpus independente com movimento gerado, manipulação facial autorizada, voz fora do quadro e vídeo com áudio. Foto IA repetida não é outro gerador nem lip-sync.

**P1 — entrega:** salvar/abrir PDF; após renovação da hospedagem, repetir na URL pública com commit, variáveis, banco, cookies/CORS confirmados. Sem contratação automática.

**Conclusão:** várias APIs responderam e quatro defeitos foram corrigidos. Classificação factual continua não homologada. Não apresentar como “100% certeiro” ou todas as verificações finalizadas.
