# Pesquisa online orientada por IA — 17/10/2026

## Implementação

O aplicativo oferece pesquisa online às IAs usando o serviço de busca já integrado. Não simula navegação nem habilita plugins pagos de pesquisa nativa.

Fluxo: afirmação original → pesquisa/leitura inicial → avaliação de lacunas por afirmação → IA solicita até duas consultas neutras e escolhe IDs de páginas já encontradas → servidor executa a busca e lê documentos públicos → comparação com citações literais → validação/relatório.

`source_research.py` fornece essa etapa. A IA recebe a afirmação intacta, pistas reais com IDs, trechos de documentos já lidos e as afirmações que ainda precisam de evidência. Pode orientar onde pesquisar; **não pode retornar um veredito, uma probabilidade, uma citação ou um endereço inventado** nessa etapa.

O servidor valida o plano: até duas consultas, 20–180 caracteres cada, vínculo com o assunto e a identidade originais (incluindo aliases de tradução), grupos de fontes definidos, IDs conhecidos e ausência de URLs/operadores/instruções de transporte. Um envelope fora do contrato é descartado. Dentro de um envelope válido, cada operação é validada separadamente: uma operação recusada não invalida outra consulta segura, e a cobertura informa o descarte parcial. Não há repetição até conseguir uma resposta favorável.

Título, resumo de busca e concordância entre IAs continuam sem voto factual. A decisão usa o corpo efetivamente recuperado, com URL e trechos pertencentes ao servidor. Metadados da pesquisa informam planejamento, execução, falhas e limites, sem registrar segredos.

## Orçamento e segurança

- Caminho determinístico preservado: até três pesquisas, seis tentativas de página e 45 segundos quando pesquisa por IA está desabilitada/sem configuração.
- Pesquisa por IA habilitada e configurada: até cinco pesquisas no total, dez tentativas cumulativas de página e 105 segundos para recuperar documentos; a comparação continua com seu prazo separado limitado.
- Falhas e redirecionamentos continuam contando nos respectivos limites. Uma página que falhou não é tentada novamente nessa análise.
- Quota/credencial de busca com falha impede pesquisas adicionais. Não há rotação de chaves, contratação, recarga ou execução de código proposto pelo modelo.
- Endereços passam pela leitura pública com DNS/IP validado, TLS e validação de redirecionamentos. Sem acesso a redes privadas e sem contornar autenticação, bloqueios ou paywalls.
- Câmara, Senado e LexML são identificados como família legislativa brasileira; não são contados como três confirmações editoriais independentes.
- Gemini planeja a pesquisa; OpenRouter gratuito é alternativa limitada em falhas do provedor. Nenhum modelo dá voto por memória própria.
- O [plugin de pesquisa do OpenRouter](https://github.com/OpenRouterTeam/docs/blob/main/guides/features/plugins/web-search.mdx) pode cobrar mesmo com modelo gratuito. A [pesquisa nativa do Gemini](https://ai.google.dev/gemini-api/docs/google-search/) também tem regras próprias por modelo/plano. Não foram habilitadas silenciosamente.

## Correspondência de datas e períodos

A data de uma divulgação não é o período econômico divulgado. A leitura agora aceita uma divulgação explicitamente datada no corpo por “hoje (dia)” ou dia da semana, somente quando compatível com a publicação validada. Data de atualização não serve como publicação.

“Ano anterior” só é ligado ao único ano anual explícito do trecho, não à data de consulta. Crescimento percentual concluído do PIB/economia em um ano calendário pode usar a convenção de variação anual em relação ao ano precedente. A anotação dessa interpretação é preservada no relatório; a citação original não é reescrita.

Essa convenção não se aplica a previsões, indicadores arbitrários, vários anos de evento ou períodos trimestrais/semestrais/mensais. Ano/valor/ator divergentes continuam bloqueando apoio. O valor precisa pertencer à medição do PIB, não a outro percentual no mesmo parágrafo.

Ter duas famílias no conjunto de documentos não basta quando cada uma cobre uma afirmação diferente. A necessidade de pesquisa é verificada por afirmação. As exceções já delimitadas de registro institucional original não foram transformadas em confiança geral em qualquer página oficial.

## Configuração

`SOURCE_RESEARCH_ENABLED=true` é o padrão. Requer a busca Serper e pelo menos um dos clientes de IA já configurados. `false` desativa somente a etapa orientada por IA, preservando a recuperação determinística. Não é necessário adicionar outra chave de pesquisa ou serviço pago para usar esse caminho.

Chaves permanecem apenas no backend. OpenRouter continua restrito a `openrouter/free`/modelos específicos `:free` e preço máximo zero. O uso da busca existente consome seus créditos/quota; “sem nova contratação” não significa quantidade ilimitada.

## Verificação

A primeira execução com o novo pesquisador foi um controle diagnóstico do PIB. A IA escolheu uma notícia com resultado efetivo e uma referência do IBGE, mas ainda faltou correspondência do período. Esse registro é piloto, não foi apagado nem contado como rodada congelada completa.

Um segundo piloto, com o controle verdadeiro de Elizabeth II, retornou plano recusado. Nos controles locais do validador, uma consulta traduzida válida também era recusada; isso não permite reconstruir o texto bruto não registrado do provedor. A validação passou a reutilizar os aliases de identidade/evento da comparação, mantendo a rejeição de outra pessoa e assunto. Também passou a preservar uma consulta válida quando um ID independente é inválido. O piloto inconclusivo permanece registrado separadamente; não foi convertido retroativamente em acerto.

Depois das correções de período, a avaliação final repete os oito controles públicos previamente definidos, sem escolher casos novos mais fáceis. Cada requisição registra a impressão SHA-256 dos arquivos de execução antes/depois; mudança de código bloqueia nova análise nessa rodada. Código e casos ficam constantes, embora busca, quota e páginas públicas possam mudar.

Os inconclusivos e os erros continuam no denominador. Resultados desta sequência não são porcentagem geral de precisão, nem validam imagem, áudio ou vídeo. Testes de mídias que precisem de novo crédito pago permanecem separados; não houve nova autorização de gasto Hive nesta etapa.

## Resultado congelado `online-v3`

Oito controles enviados uma única vez cada pela interface local, com login em conta descartável, espera pelo relatório e conferência do resultado visível. Todos responderam HTTP 200 e mantiveram a mesma impressão de execução antes/depois: `795e9bfe707e0f69284673126314141bb5fe12076870c11f32bbb7c588e437e3`. A impressão cobre caminhos/conteúdo de Python do aplicativo e JS/JSX/CSS do frontend; não congela dependências, ambiente, modelos, páginas ou o índice público de busca.

| Controle | Esperado | Obtido | Evidência aceita / obstáculo |
| --- | --- | --- | --- |
| Elizabeth II — 08/09/2022 | Corroborar | Inconclusivo | Uma família elegível; plano adicional vazio |
| Elizabeth II — 09/09/2022 | Refutar | Refutada | BBC e Mundo Educação registram dia 8 |
| DART — impacto em 26/09/2022 | Corroborar | Inconclusivo | Duas referências NASA selecionadas pela IA, mas somente uma família com trecho elegível |
| OMS — pandemia em 11/03/2020 | Corroborar | Corroborada | CNN e Brasil Escola; pesquisa adicional executada |
| PIB — divulgação de 07/03/2025 | Corroborar | Inconclusivo | Trecho da Agência Brasil aceito; faltou segundo apoio aceito |
| Copom — suposta redução em 18/09/2024 | Refutar | Inconclusivo | Nenhum corpo elegível; Gemini e alternativa OpenRouter excederam o prazo do planejador |
| Copernicus — supostos 1,60 °C abaixo | Refutar | Contradita no registro | Documento original registra acima, não abaixo |
| Lei Áurea — negação do artigo 1º | Refutar | Inconclusivo | Nenhum trecho completo admissível, mesmo após a pesquisa adicional |

**Acertos: 3/8 (37,5%). Inconclusivos: 5/8 (62,5%). Vereditos conclusivos errados observados: 0/8.** Entre quatro controles verdadeiros: um acerto e três abstenções. Entre quatro falsos: dois acertos e duas abstenções. Tempos de API: 11,474–50,372 segundos, média 34,294 segundos. HTTP 200 não é acerto factual.

Registro sanitizado com entradas integrais, esperado/obtido, URLs, pesquisas e contadores: [validation-online-research-2026-10-17.json](validation-online-research-2026-10-17.json).

O corpus pequeno já foi usado no desenvolvimento, portanto não é teste cego nem avaliação representativa de todas as notícias. A rodada anterior tinha 4/8 acertos nos últimos resultados de revisões misturadas, não em uma execução congelada pareada. **Esta rodada não demonstra melhora agregada e não homologa a checagem factual.** Os dois pilotos anteriores ficaram fora dessa métrica, preservados como diagnósticos, não apagados para aumentar a taxa.

### APIs efetivamente exercidas

- Gemini: 11 requisições reservadas, dez HTTP 200 e uma incompleta. Planejamento real e comparação de citações exercidos com `gemini-3.1-flash-lite`; não revalida OCR/fala/imagem.
- OpenRouter gratuito: nove requisições, sete HTTP 200 e duas incompletas. Extração auxiliar e tentativa alternativa de planejamento exercidas. Resposta de transporte não certifica qualidade de todas as saídas.
- Google Fact Check: oito HTTP 200. Consulta sem avaliação correspondente não bloqueia o caminho documental e também não constitui prova factual.
- Serper: 35 HTTP 200, incluindo buscas de contexto/recuperação e três consultas adicionais efetivamente propostas pela IA (OMS, PIB e lei).
- Leitura pública: 64 requisições, incluindo redirecionamentos; 48 HTTP 200, oito redirecionamentos, seis bloqueios 401/403 e duas incompletas. Páginas sem conteúdo estático utilizável continuam sem virar evidência.
- Hive, Sightengine e AssemblyAI: zero chamadas novas nesta rodada. Hugging Face e plugins nativos de pesquisa pagos não habilitados.

Suíte isolada sem rede: **810 testes backend, zero skips**. Frontend: **22 arquivos de teste passaram, zero skips; build concluído**. Não confundir esses testes funcionais com porcentagem de acerto de notícias reais.

Conferência adicional do relatório inconclusivo em viewport de 375 × 812: documento com largura de 360 px, título e cartão dentro da área disponível, sem overflow horizontal medido. Modo Fácil manteve-se ativo. A captura nessa largura falhou no navegador integrado; isso não equivale a validação visual completa em celular. Viewport restaurado ao padrão. Captura do relatório climático em desktop foi salva localmente. Nenhuma consulta de API foi repetida para essa conferência.

## Pendências para reduzir abstenções com segurança

1. Reproduzir as exclusões dos corpos realmente recuperados (DART, decisão de juros e artigo de lei) em testes locais. Melhorar correspondência de parágrafos/data/anáfora apenas com controles negativos de ator, dia, ano, direção, valor e negação; não liberar apoio genérico por domínio oficial ou título.
2. Melhorar o planejamento quando faltam evidências e o modelo escolhe plano vazio ou apenas referências já pouco úteis. Medir o ganho em recuperação, não repetir provedores até obter o veredito desejado.
3. Avaliar o prazo compartilhado do planejador e a priorização de documentos retrospectivos. O timeout de 30 segundos do Copom foi real; aumentar indiscriminadamente todos os prazos não resolve ausência de corpo ou correspondência.
4. Tratar HTML público incompleto e documentos em outros formatos em camada própria limitada, sem executar JavaScript remoto nem contornar bloqueios. PDF público não é atualmente lido como corpo nesse caminho.
5. Montar corpus adicional independente/rotulado, balanceado e com notícias fora destes oito exemplos; congelar revisão, registrar todos os pedidos e apresentar abstenção junto de acerto/erro. Validar mídia separadamente por autenticidade e conteúdo factual, respeitando créditos autorizados.
6. Só publicar após revisão e staging. Esta etapa é local: não comprova atualização do GitHub, Vercel, Railway, chaves de produção ou salvamento visual do PDF.
