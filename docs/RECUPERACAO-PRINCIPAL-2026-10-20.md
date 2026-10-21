# Recuperação de evidências — segunda revisão de 20/10/2026

## Objetivo e limites

Meta: aumentar acertos reais, incluindo inconclusivos no denominador, sem aceitar opinião de IA como prova. O checkpoint anterior foi **5/12 acertos (41,7%)**, em [comparação completa das fontes](COMPARACAO-FONTES-2026-10-20.md). Este documento descreve a revisão seguinte; não substitui ou seleciona os melhores casos das rodadas anteriores.

A avaliação de desenvolvimento tem doze textos conhecidos. Atingir pelo menos 80% nesse conjunto exige dez acertos; não significa 80% em qualquer notícia, imagem, voz ou vídeo. Uma alegação ampla exige amostra independente e representativa. Mídias não entram nesta rodada textual.

## Correções implementadas

### 1. Ler fontes pertinentes antes de gastar a cota

- G1 incluído nos filtros editoriais, usando família já reconhecida pela política.
- Na construção anual delimitada, o ano medido recebe prioridade sobre o ano de comparação. A afirmação original mantém ambos; o ranking não certifica nenhum deles.
- Artigos HTML têm prioridade sobre PDFs, arquivos de mídia e galerias que o leitor atual não suporta. Candidatos não são eliminados nem ganham crédito factual pelo formato.
- Compatibilidade de assunto precede preferência por domínio oficial. Uma instituição não transforma uma página sobre outro tema em evidência.
- Permanecem dez recursos e 105 segundos com pesquisa por IA; seis/45 segundos no fluxo sem essa pesquisa. Falhas, cancelamentos e índices oficiais também gastam recursos. Sem restituição ou repetição até acertar.

### 2. Recuperar o comunicado original do Copom

Novo adaptador puro `official_source_body.py`, baseado na [especificação pública do BCB](https://www.bcb.gov.br/conteudo/dadosabertos/BCBDeinf/copom.yaml):

1. Lê o índice oficial de até cem comunicados, limitado a 256 KiB.
2. Seleciona somente uma referência com a data literal exata da afirmação; não usa reunião vizinha, mais recente nem aproximação.
3. Lê o detalhe pelo número oficial de reunião, vinculando novamente número e data.
4. Entrega somente `textoComunicado` ao leitor HTML existente. Título permanece contexto; data de referência permanece metadado tipado, fora da citação.

Dois GET públicos, sem chave ou nova contratação, pelo mesmo leitor com validação de DNS/IP/TLS. Origem, caminho, query, tipo de conteúdo, tamanho, chaves JSON, duplicatas, número e data são conferidos. Sem executar JavaScript, usar proxy pago, desbloquear paywall ou presumir que ID de notícia equivale a número de reunião.

As duas consultas são reservadas antes do envio e debitadas da cota existente. O índice é localização, **não uma segunda fonte nem um voto**. Falhas não viram corpo de documento. O detalhe permanece no fluxo normal mesmo se o buscador não encontrar a URL da API. O retorno por prazo esgotado preserva o número de tentativas já consumidas.

### 3. Comparar a decisão formal, sem confundir datas ou unidades

`monetary_decisions.py` reconhece uma construção completa e delimitada de afirmação sobre Selic/Copom e a decisão formal comunicada no registro original. A data é a referência daquele comunicado, não horário de reunião, vigência de série de juros ou data arbitrária de uma notícia.

- Taxa, direção e transição anterior→final precisam pertencer à mesma decisão.
- Apoio à taxa anterior exige valor explícito ou cálculo inverso de um único ajuste em **pontos percentuais**, junto da taxa final. Variação percentual e pontos percentuais não são intercambiáveis.
- Falta de taxa anterior não é, sozinha, refutação. Direção ou alvo incompatíveis da mesma decisão são contradições explícitas.
- Previsões, condições, boatos, instruções financeiras, outras instituições, datas incompatíveis, valores dispersos e unidades ambíguas não passam.
- Contexto anterior hipotético, negado, incerto, planejado ou de reunião anterior não pode desaparecer. Uma negação posterior da mesma decisão também bloqueia. Orientação futura separada não apaga automaticamente o ato já comunicado.

Política factual desta revisão: **`2026-10-20.1`**. Amplia o caso delimitado de registro institucional original para essa decisão formal. Não reduz genericamente duas famílias para uma; não certifica juros atuais, economia ou orientação de investimento. A conclusão de uma única publicação original é identificada como tal no relatório. Continua exigindo comparação completa do modelo e verificação literal pelo servidor; o índice não produz veredito.

### 4. Não confundir lugar com outra pessoa

Uma construção fechada como “monarca mais longeva do Reino …” pode qualificar o mesmo nome antes de uma segunda frase com pronome. Somente esse vínculo territorial é reconhecido; não se apagam vírgulas ou nomes próprios indiscriminadamente. Parentes, outra pessoa, frase intermediária, data de publicação incompatível e contexto de desmentido permanecem bloqueados.

Essa correção foi reproduzida também com HTML público previamente capturado. Replay não é nova medição online e não garante que o buscador voltará a encontrar a página.

### 5. Lançamento concluído e dia relativo explícito

- Formas delimitadas “lifted off”, “blasted off” e “decolou” são reconhecidas como lançamento concluído, preservando missão/voo, agência, tripulação, sucesso, local e horário quando alegados.
- Um lançamento passivo de objeto nomeado pode ligar “neste domingo (10/3)” ao metadado explícito de publicação se dia, mês e semana concordarem. URL, título e dia da consulta não fornecem essa data.
- A ligação relativa só atende afirmações completas de nome/tipo/data, sem alegação adicional de agência, local, horário ou sucesso. A ordem do nome e o descritor “espacial”, quando alegado, não podem desaparecer.
- A citação exibida permanece literal. Normalização interna serve apenas à conferência; não vira texto atribuído à fonte.
- Capturas, planos, negativas, condições, outro evento, objeto diferente e publicação posterior à recuperação continuam bloqueados.

Algumas páginas reais de Artemis e DART simplesmente não apresentam ano/dia completo do evento no corpo. Não se inventou essa informação a partir da URL ou da data de publicação para tornar tais páginas elegíveis.

## Verificações antes da medição real

**Antes do congelamento desta rodada de 20/10, 1.133 testes backend passaram, zero skips, em contêiner sem rede e sem credenciais. Os 22 arquivos de testes frontend e a compilação passaram.** Esse é o checkpoint anterior à medição abaixo, não a contagem da revisão atual nem uma taxa de acerto factual. Um teste de referência foi ajustado apenas para a ordem nova por assunto: mantém as mesmas três leituras iniciais, seis totais e profundidade máxima de um link.

Revisão de segurança separada encontrou e corrigiu duas falhas antes do congelamento: qualificador hipotético fora da frase formal podia ser perdido; diagnóstico de tentativas oficiais podia desaparecer num prazo esgotado precoce. Controles negativos foram acrescentados. Testes automatizados exercitam contratos e regressões, não contam como acerto de notícias.

Código congelado para a nova rodada: `5976eb40b7c72e279978b4a59e2798786dd720268162fafb679217ed39768ca5` (mesmo algoritmo e escopo de arquivos da rodada anterior). Gemini `gemini-3.1-flash-lite`, alternativa `openrouter/free`, sem rotação automática de modelo, sem novas chamadas Hive. Perfil configurado no ambiente de testes; não presume alteração no Railway ou deploy.

## Fechamento da rodada real

**Rodada encerrada: 2/12 acertos (16,7%), 10/12 inconclusivos (83,3%), nenhuma conclusão errada observada e nenhum erro terminal do pipeline. A meta de 80% não foi atingida.** Os acertos foram James Webb e Constituição. [Dados sanitizados por caso, tempos e contadores](validation-main-recovery-2026-10-20.json).

São os mesmos doze textos conhecidos, seis verdadeiros e seis falsos, com manifesto SHA-256 `47397f9ffa4022db414d2b85614efd70bdbfe3db4510b221d3d67bcb16625e04`. Uma tentativa por caso, rótulos esperados fora das chamadas, banco descartável, contadores persistentes, fontes públicas recuperadas ao vivo. O resumo offline conferiu os doze registros completos contra os textos, IDs, manifesto e hash do código congelado acima; não houve seleção dos melhores casos entre rodadas.

O resultado ficou abaixo dos 5/12 da [rodada anterior](COMPARACAO-FONTES-2026-10-20.md), que permanece registrada separadamente. A variação das fontes encontradas e da disponibilidade dos fornecedores impede atribuir a diferença somente às correções. Duas conclusões corretas em duas conclusões emitidas não equivalem a 100% de acerto global: os dez inconclusivos continuam no denominador.

| Controle | Esperado | Resultado real | Acerto | Tempo do pipeline |
| --- | --- | --- | --- | --- |
| Elizabeth II — data correta | Verdadeira | Inconclusivo | Não | 44,167 s |
| Elizabeth II — data falsa | Falsa | Inconclusivo | Não | 45,141 s |
| DART — impacto intencional | Verdadeira | Inconclusivo | Não | 37,496 s |
| OMS — declaração de pandemia | Verdadeira | Inconclusivo | Não | 75,880 s |
| IBGE — PIB de 2024 | Verdadeira | Inconclusivo | Não | 24,860 s |
| Copom — redução alegada | Falsa | Inconclusivo | Não | 54,434 s |
| Copernicus — abaixo da referência | Falsa | Inconclusivo | Não | 21,959 s |
| Lei nº 3.353 — negação do artigo | Falsa | Inconclusivo | Não | 38,612 s |
| James Webb — lançamento | Verdadeira | Verdadeira nas fontes | Sim | 33,512 s |
| Constituição — promulgação | Verdadeira | Verdadeira nas fontes | Sim | 54,757 s |
| Brasil — campeão de 2014 | Falsa | Inconclusivo | Não | 47,560 s |
| Artemis I — data falsa | Falsa | Inconclusivo | Não | 48,143 s |

Acertos nos verdadeiros: **2/6 (33,3%)**; nos falsos: **0/6 (0%)**. Mediana do pipeline: **44,654 s**, mínimo 21,959 s e máximo 75,880 s. Os registros cobrem de `2026-10-20T21:21:10.082046+00:00` a `2026-10-20T21:30:00.205252+00:00`. Esses tempos pertencem ao ambiente local de avaliação, não são latência homologada de produção.

## Transporte e limitações observadas

Os doze casos foram submetidos por **HTTP local ordinário ao endpoint real, não pelo formulário do navegador**. Os doze retornaram HTTP 200 JSON com `Cache-Control: no-store`. Isso comprova recebimento das respostas, não doze acertos nem doze testes pela interface. Abrir histórico e relatório no navegador comprova renderização desses relatórios, não submissão pelo formulário nem teste de todas as modalidades.

| Serviço | Envios de transporte | Estados registrados |
| --- | --- | --- |
| Gemini | 18 | 8 HTTP 200, 10 HTTP 503 |
| OpenRouter gratuito | 16 | 14 HTTP 200, 2 HTTP 502 |
| Google Fact Check | 12 | 12 HTTP 200 |
| Busca existente | 60 | 60 HTTP 200 |
| Leitura pública | 87 | 71 HTTP 200, 3 HTTP 307, 2 HTTP 301, 5 HTTP 403, 1 HTTP 401, 5 sem status HTTP registrado |

Limites fixos da rodada: Gemini 36, OpenRouter 16, Fact Check 24, buscas 72 e leituras públicas 180 envios. O diário anterior não foi reiniciado; quatorze envios OpenRouter prévios conhecidos motivaram o teto conservador de dezesseis para esta rodada. Reservas, falhas e redirecionamentos contam. Não houve rotação de chave nem repetição de caso até acertar.

OpenRouter consumiu o teto local de dezesseis envios; os dois últimos casos registraram `rate_limited` na extração auxiliar. Na comparação de fontes, dois casos terminaram em `success` (os dois acertos), quatro em `invalid_response` (OMS, Copom, Copernicus e Lei nº 3.353) e seis em `not_requested`. HTTP 200 não garante JSON válido, comparação utilizável ou evidência factual. Falhas de serviço e cobertura insuficiente permaneceram inconclusivas, sem virar refutação.

Mídias, OCR, transcrição, Hive, Sightengine e Hugging Face **não foram revalidados nesta rodada textual**; não houve novos envios a esses fornecedores. Esta é uma medição local de doze controles públicos de desenvolvimento, não uma amostra independente, cega ou representativa nem prova de deploy. Alterações posteriores precisam de outra rodada congelada; não herdam esta taxa ou a taxa anterior.
