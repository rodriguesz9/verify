# Revisão de 24/10 — leitura de eventos e comparação completa

Continuação após `47186b5`, na branch de entrega. Não representa implantação nem garantia de 80% de precisão. Medições anteriores permanecem em [23/10](RESILIENCIA-RECUPERACAO-MIDIA-2026-10-23.md).

## Correções e limites

### Comparação incompleta das IAs

O diagnóstico anterior do OpenRouter respondeu HTTP 200, mas revisou um de dois pares afirmação/fonte. O schema de geração permitia comprimentos variáveis e IDs genéricos; a exigência de cobertura completa existia no texto e no decoder. Não havia resposta bruta preservada para atribuir o problema a um campo específico.

Agora cada requisição possui contagens exatas de afirmações/fontes, enums dos IDs realmente selecionados e checklist de todos os pares a revisar. A mesma restrição é enviada aos clientes Gemini e OpenRouter. O decoder continua verificando completude, unicidade, correspondência fonte/trecho e relações; schema válido não comprova leitura nem verdade. Não se preenche célula ausente, não se repete resposta insuficiente e não se aumenta prazo/quota nesta mudança. O uso do schema segue o formato de [saídas estruturadas do OpenRouter](https://openrouter.ai/docs/guides/features/structured-outputs), somente em rotas compatíveis.

Oito testes novos atravessam transportes HTTP simulados dos dois clientes: cobertura 2×2, omissão 1/2, IDs repetidos/errados, campo de sentença inválido, insuficiência válida e truncamento. Não são testes remotos nem porcentagens de acerto.

### Duas classificações, duas datas

Um texto pode dizer que um órgão declarou uma emergência em uma data e caracterizou um surto como pandemia em outra. Comparar apenas o conjunto de datas confundia esses vínculos. O novo serviço puro `classification_body_dates.py` reconhece uma construção completa e limitada de classificações coordenadas.

- Órgão, objeto, classificação e data precisam estar explicitamente vinculados no corpo.
- A expressão “o surto” exige definição literal na mesma janela BODY, com no máximo uma frase intermediária sobre o mesmo agente patogênico.
- A citação completa, a definição, as duas cláusulas e ambas as datas são preservadas; não há recorte para eliminar uma divergência.
- O vínculo permite somente apoio, nunca inventa refutação de outra data, não fornece família independente e não dispensa a revisão do modelo.
- Outra identidade, qualificador adicional, data inválida/futura, negação, ficção e contexto condicional continuam impedindo a aceitação.

Há dez controles puros com nomes/datas sintéticos diferentes dos casos conhecidos e quatro testes de fluxo. Duas famílias e revisão completa continuam necessárias fora dos registros originais já previstos pela política.

### Publicação da própria notícia, sem importar texto oculto

Algumas páginas publicam `datePublished` em JSON-LD em vez das propriedades já lidas. O leitor agora aceita esse metadado somente de um objeto Article compatível, com URL da página e headline correspondente a um h1 visível. [Schema.org define esse campo como data de publicação](https://schema.org/datePublished), não como data do evento.

São inspecionados apenas objetos delimitados no cabeçalho, listas ou grafo direto; sem executar JavaScript, resolver contexto remoto ou percorrer conteúdo arbitrário. Vídeos, artigos relacionados, campos duplicados, valores conflitantes/inválidos e `dateModified` não substituem publicação. `articleBody` oculto nunca vira evidência. Uma data de publicação isolada continua incapaz de datar uma morte, lançamento ou impacto sem vínculo explícito no corpo. Sete novos testes cobrem essas barreiras.

### Crédito da imagem não é sujeito da notícia

Uma estrutura de crédito visual estava sendo concatenada ao parágrafo seguinte. O leitor conserva o crédito em contexto, separado do BODY. A regra depende da estrutura de mídia e do marcador de crédito, não de apagar a palavra “BBC” ou um nome encontrado no texto. Figuras também delimitam contexto e não são concatenadas à notícia. Quatro controles novos preservam prosa comum e impedem legenda de fornecer uma afirmação factual.

## Verificação da versão

- 1.430 testes backend passaram, sem rede, sem `.env`, sem skips e sem transportes HTTP inesperados.
- 22 arquivos de testes frontend passaram; build de produção concluído.
- Política factual: `2026-10-24.1`. Política de mídia não alterada.
- SHA-256 congelado: `6d0c4d2421e493d311eec48e2f55133bfd6c7974b7111000e245e001c0af7fbb`, calculado sobre os caminhos/bytes de `backend/app/*.py` e `frontend/src` JS/JSX/CSS.
- Os controles offline do novo roteiro verificaram limites, linhagem, bloqueios após quota, exclusão de mídia, congelamento antes de chaves e impossibilidade de repetir uma reserva ambígua.

## Nova medição real

Mesmas doze entradas conhecidas, sem alterar os textos, com uma tentativa por entrada e código congelado antes das chamadas. Uma submissão pelo formulário e onze pedidos HTTP comuns; não são doze testes visuais. [Resultados sanitizados](validation-bindings-2026-10-24.json): **9/12 corretos (75%), três inconclusivos, nenhuma conclusão errada observada e nenhum erro de execução**. Os inconclusivos permanecem no denominador. A rodada anterior teve 6/12; a meta de 80% não foi atingida.

| Controle | Resultado |
| --- | --- |
| Elizabeth II, data verdadeira | Verificada como verdadeira |
| Elizabeth II, data falsa | Refutada |
| DART, impacto intencional | Inconclusivo |
| OMS, classificação como pandemia | Verificada como verdadeira |
| IBGE, PIB | Verificada como verdadeira |
| Copom, redução alegada | Refutada |
| Copernicus, temperatura abaixo da média | Refutada |
| Lei Áurea, negação da abolição | Refutada |
| Webb, lançamento | Verificada como verdadeira |
| Constituição, promulgação | Verificada como verdadeira |
| Brasil campeão de 2014 | Inconclusivo |
| Artemis I, ano de lançamento falso | Inconclusivo |

O apoio à afirmação da OMS veio do discurso original, com data de publicação vinculada ao registro institucional. Não foi resultado do novo parser de classificações coordenadas. As páginas recuperadas também variam entre rodadas: o ganho observado não prova que uma única alteração causou os três acertos adicionais.

O controle verdadeiro de Elizabeth II retornou na interface “Verificada como verdadeira nas fontes consultadas”, com trechos G1/Agência Brasil. Nenhuma alteração de código ocorreu durante a rodada e esse resultado isolado não estabelece melhora geral.

Limites da rodada: Gemini 13, OpenRouter gratuito 4, Fact Check 12, busca 70 e leituras públicas 120; todas as mídias desativadas. Acumulado conservador OpenRouter começa em 44, incluindo a reserva anterior sem envio, e não pode ultrapassar 48. Mudança de data não zera registros. Sem contratação, recarga, rotação de chave/modelo ou nova chamada Hive.

Consumo observado: Gemini 13, OpenRouter 2, Fact Check 12, busca 63, leituras públicas 71; total 161 chamadas. Gemini/OpenRouter/Fact Check/busca retornaram HTTP 200, o que não implica evidência factual suficiente. Nas leituras públicas: 59 HTTP 200, quatro redirecionamentos, três 401, dois 403, um 504 e dois transportes incompletos. Os redirecionamentos não são contados automaticamente como falhas finais.

As duas chamadas OpenRouter foram de planejamento de pesquisa, não comparação de fontes. A comparação remota desta rodada usou Gemini; os testes simulados dos dois clientes não substituem uma homologação remota do novo contrato OpenRouter. Acumulado conservador OpenRouter final: 46/48. Nenhuma chamada de mídia foi realizada.

## Trabalho restante

Esta revisão não resolve genericamente citações com data ausente, abreviações não definidas ou evidência repartida por seções distantes. Em particular, “on Thursday afternoon”, sem dia numérico ou vínculo temporal suficiente, não recebe automaticamente a data de publicação. DART ainda exige evidência que conecte identidade, intenção e data completa; não basta a ocorrência de um impacto.

Nos três inconclusivos, a comparação não chegou a ser solicitada: DART e Copa não forneceram famílias elegíveis; Artemis forneceu somente uma. DART continua perdendo o vínculo completo de identidade, intenção e data. Copa/Artemis continuam sem trechos completos aceitos pela relação de título esportivo/lançamento. Os motivos por candidato são diagnósticos delimitados, não prova de que todas as exclusões estejam certas.

Próximas prioridades: revisar essas rejeições com corpos completos preservados, ampliar testes sintéticos de paráfrases sem aceitar qualificadores omitidos, verificar referências primárias acessíveis e medir novamente em casos novos previamente separados. Não resolver reduzindo o denominador ou obrigando uma conclusão sem prova. Doze exemplos de desenvolvimento não são um conjunto representativo de notícias, e testes automatizados não demonstram precisão geral. Os resultados de mídia da revisão anterior não foram revalidados nesta rodada.
