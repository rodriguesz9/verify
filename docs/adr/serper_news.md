# Serper News (`serper_news`) — Decisão e Considerações de Implementação

## Por que `serper_news`?

O pipeline de texto/URL depende de três fontes de evidência para o relatório final
(`generate_final_report` em `gemini_analyzer.py`):

1. **Google Fact Check API** (`fact_checker.py`) — consulta o banco de reviews de
   organizações de fact-checking. Cobre apenas alegações que algum órgão já checou.
   Uma notícia real mas não checada (ex.: "Sony anunciou edição limitada do PS5")
   retorna vazio — sem evidência, o Gemini recai na análise estrutural do texto e
   tende a marcar como Suspicious.
2. **Serper News** (`serper_client.py`) — busca ativa em notícias indexadas do
   Google News. Preenche o vão do item 1: corroboração via imprensa para alegações
   factuais recentes.
3. **GPTZero + domain checker + Gemini** — forense de IA e heurística de domínio.

A decisão foi usar **Serper.dev** (`google.serper.dev/news`) em vez de grounding do
Gemini porque:

- API simples: POST JSON, retorna `{title, link, snippet, date}` estruturado — sem
  scraping nem parsing de HTML.
- Custo previsível e pago por uso (~1 crédito/consulta).
- Controle explícito das queries (usamos as alegações extraídas).
- Grounding "nativo" do Gemini não funciona com prompt de texto puro — precisa de
  tool config via SDK (`GoogleSearchRetrieval`), suporte incerto para o modelo
  custom `gemini-1.5-flash-lite-8b` e retorna resultados em `grounding_metadata`
  (requer parsing).

## Implementação

- `serper_client.py`: `search_news(query)` → POST em `https://google.serper.dev/news`,
  header `X-API-KEY` (env `SERPERAPI_KEY`), payload `{q, gl: "br", hl: "pt-br", num: 5}`.
  Sem chave → retorna `[]` (degradação silenciosa).
- `pipeline.py`: para cada alegação extraída (top 3) dispara busca concorrente com o
  fact-check. Deduplica por `link`. Injeta tudo em `context_data.serper_news`.
- `gemini_analyzer.py`: passo 5 do prompt obriga o Gemini a comparar alegações com
  `serper_news`; corroboração por múltiplos veículos eleva score/`positives`;
  cobertura conflitante ou ausente vira red flag / aviso na summary. Não pode
  inventar cobertura. Saída em `serper_news_evidence`.
- Endpoints `check-text`/`check-url`: `ai["serper_news"]` exposto no payload e
  persistido em `raw_result`.

## Considerações / Caveats

**Custo.** Cada análise gera até 3 chamadas pagas (1 por claim). `claims[:3]` limita
o gasto, mas é arbitrário e fixo. Considerar: env-configurável, cache por query,
ou reduzir para 2 em tiers gratuitos.

**Ordem das claims.** Usamos as 3 primeiras da extração Gemini. A ordem não é
garantia de relevância — uma claim importante no meio da lista fica sem cobertura.
Mitigação futura: selecionar por score do Gemini.

**Truncamento `[:200]`.** Query cortada em 200 chars; claims muito longas podem
perder o sujeito. Ajustável por env.

**Busca por keyword ≠ verdade.** Serper mostra o que está indexado, não julga
veracidade. Corroboração em múltiplos veículos eleva confiança, mas não é prova
absoluta — o prompt já instrui o Gemini nesse sentido.

**Idioma fixo.** `gl: "br"` / `hl: "pt-br"` — cobre o público-alvo pt-BR, mas
ignora cobertura internacional. Para claims globais, considerar `gl` configurável
ou segunda consulta.

**Dedupe por link apenas.** Mesmo link com título/snippet diferentes não duplica
corretamente (link igual é ignorado na segunda ocorrência). OK na prática, mas a
chave poderia ser `(title casefold, link)`.

**Degradação silenciosa.** Sem `SERPERAPI_KEY` ou erro de rede → `[]`. Pipeline e
Gemini funcionam sem notícias; a análise apenas perde a corroboração de imprensa.
Nenhum log/warning é emitido — vale adicionar.

**Data do resultado.** `date` vem do Serper e não é validada; o Gemini recebe como
string. Pode ser usado para `temporal_issues`, mas sem parsing robusto.

**Rate limit / 429.** Sem retry nem backoff em `serper_client.py`. Em picos, erros
vazam como `[]`. Considerar `tenacity` ou retry simples.
