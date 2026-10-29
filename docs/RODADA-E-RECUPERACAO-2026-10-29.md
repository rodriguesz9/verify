# Nova medição e recuperação de fontes — 29/10/2026

**A taxa real permaneceu em 5/12 acertos (41,7%), com sete inconclusivos, nenhuma conclusão errada observada e nenhum erro terminal de execução.** O ganho da Lei Áurea foi compensado pela perda da data verdadeira de Elizabeth II. A meta de 80% não foi atingida. [Resultados sanitizados, cobertura, hashes e provas dos doze casos](validation-quality-2026-10-29.json).

## Como foi medido

- Commit medido: `08fa80a4807305bed6e24f567170639de5797b05`.
- SHA-256 de implementação congelada: `d48aa4d3f3f0686654d42bdc4a1d1b91335340e199d223ac2db8259b0752c6a6`.
- Mesmos doze textos conhecidos e mesma ordem de 28/10, uma análise iniciada por texto. Rótulos esperados e URLs de referência usados somente na apuração, sem serem fornecidos à aplicação.
- Doze submissões pelo formulário e doze relatórios observados no navegador, cada qual com captura e prova de correspondência da afirmação. Nenhum envio HTTP alternativo. Um clique no segundo formulário não iniciou requisição; a ausência foi conferida antes de acionar novamente. Nenhuma análise iniciada foi repetida.
- Servidor, conta e banco descartáveis, separados do ambiente principal. Código, interface compilada, entradas, instrumento e limites congelados antes de carregar as quatro credenciais selecionadas. Congelamento reconferido após todos os relatórios e antes das correções posteriores.
- Rodada encerrada, contêiner removido e aba temporária fechada. Registros persistentes preservados. Nenhum limite não usado é transferido para outra rodada. Railway/Vercel e mídias não foram testados.

Inconclusivos e erros entram no denominador. Os controles já foram usados no desenvolvimento; isto não é uma avaliação cega nem uma estimativa de precisão geral.

| Grupo esperado | Corretos | Inconclusivos | Conclusões erradas | Acerto no grupo |
| --- | ---: | ---: | ---: | ---: |
| Verdadeiros | 2/6 | 4/6 | 0 | 33,3% |
| Falsos | 3/6 | 3/6 | 0 | 50,0% |
| Total | 5/12 | 7/12 | 0 | 41,7% |

| Controle | Resultado | Mudança em relação a 28/10 |
| --- | --- | --- |
| Declaração da OMS | Verdadeiro, correto | Manteve |
| Brasil campeão da Copa de 2014 | Inconclusivo | Manteve |
| Temperatura do Copernicus, direção invertida | Inconclusivo | Manteve |
| Taxas do Copom, direção invertida | Falso, correto | Manteve |
| Declaração negada do artigo da Lei Áurea | Falso, correto | Ganhou um acerto |
| Lançamento do James Webb | Verdadeiro, correto | Manteve |
| Artemis I, ano falso | Inconclusivo | Manteve |
| Elizabeth II, data verdadeira | Inconclusivo | Perdeu um acerto |
| PIB brasileiro divulgado pelo IBGE | Inconclusivo | Manteve |
| Elizabeth II, data falsa | Falso, correto | Manteve |
| Impacto intencional da DART | Inconclusivo | Manteve |
| Promulgação da Constituição | Inconclusivo | Manteve |

Não se somam os melhores acertos de versões diferentes. Buscas, documentos disponíveis e planos dos modelos variaram junto com o código; esta comparação não isola causalmente o efeito de cada mudança.

## As IAs responderam?

| Serviço | Envios / teto da rodada | Respostas |
| --- | ---: | --- |
| Gemini | 9/16 | Nove HTTP 200; nove planos de pesquisa aceitos |
| OpenRouter | 3/12 | Três HTTP 200; três comparações completas aceitas |
| Google Fact Check | 12/12 | Doze HTTP 200 |
| Serper | 60/60 | Sessenta HTTP 200 |
| Leitura pública | 68/120 | 53 HTTP 200; quatro 401; quatro 403; quatro 301; uma 307; uma 404; uma incompleta |
| Hive, Sightengine, AssemblyAI e Hugging Face | 0 | Não chamados |

Gemini usou `gemini-3.5-flash-lite`. As comparações OpenRouter usaram `openrouter/free`, com todos os preços máximos em zero; modelos observados: `dots-studio/dots-3-note-preview:free` e `nvidia/nemotron-3.5-super-vl:free`. O OpenRouter foi o primário da comparação; suas três respostas foram válidas, portanto não houve comparação adicional pelo Gemini. Copom e Lei Áurea usaram a regra documental delimitada do registro original, sem precisar de um julgamento extra dos modelos.

**Os sete inconclusivos ficaram sem fontes utilizáveis suficientes antes da comparação.** Nenhum deles foi provocado por uma comparação Gemini/OpenRouter que continuava pendente. Planejamento válido e busca HTTP 200 não equivalem a obter um trecho que comprove a afirmação.

Tempo mediano registrado: 22,468 s; percentil 95 por posto mais próximo: 51,536 s. Não anunciar ganho de velocidade: o teto atingido também abreviou a última execução, e a disponibilidade remota variou.

## O que a rodada revelou

**Lei Áurea:** a aplicação conseguiu usar a publicação original e refutar a negação do artigo. [Relatório observado](evidencias-2026-10-29/lei-aurea-refutada.jpg). A correção legislativa anterior está presente na versão medida; a rodada não é um experimento isolado dessa correção.

**Elizabeth II, data verdadeira:** em 28/10, Agência Brasil/EBC e G1 eram elegíveis. Agora somente G1 ficou elegível, após dez tentativas e seis falhas de leitura, contra oito tentativas e três falhas antes. Houve duas consultas planejadas validamente e executadas; EBC não apareceu nas cinco buscas web registradas nem nos documentos recuperados. Duas referências Reuters falharam na leitura. G1 principal, G1 do atestado e Guardian retrospectivo preservam exatamente as mesmas sentenças e papéis entre as duas datas, verificados por hashes; não há regressão de extração demonstrada nesses três textos. [Resultado inconclusivo preservado](evidencias-2026-10-29/data-verdadeira-inconclusiva.jpg). As outras páginas lidas não podem receber a data ausente apenas pela publicação ou pelo título.

**IBGE:** a variante determinística com quantidade literal foi executada uma vez dentro do espaço existente. G1 permaneceu como única família elegível; o arquivo paginado da CNN e páginas de outros períodos não forneceram a afirmação completa. A mudança foi exercida, mas não demonstrou aumento de acerto nesse controle.

**Artemis:** NASA permaneceu a única família elegível. A segunda família que uma reprodução offline anterior conseguia usar não foi recuperada como evidência nesta execução real. Trechos salvos de versões diferentes não substituem uma nova medição.

**Constituição:** o teto de sessenta buscas já estava esgotado antes do último controle. Sua busca inicial registrou `error`, não houve leitura de documento e a execução terminou em 0,826 s. O instrumento não permitia mais envios de busca; nenhum aumento de limite ou reenvio foi realizado. Isso limita a avaliação desse caso e não prova indisponibilidade do Serper, que respondeu HTTP 200 nas sessenta chamadas efetivamente enviadas. O registro não conserva a exceção da consulta para uma atribuição adicional de causa.

**Documentos longos:** uma auditoria separada do HTML já salvo em 28/10 encontrou o fecho da Constituição depois do trecho de 50.000 caracteres que o leitor conserva. A assinatura está no mesmo documento, mas longe do preâmbulo. Recuperá-la exige representar partes não contíguas com origem e lacunas explícitas, além de validar que a assinatura pertence ao ato correto. Isso ainda não foi implementado. Concatenar preâmbulo e assinatura como uma frase comum ou usar data de publicação como data do fato produziria evidência artificial.

## Correções locais posteriores à medição

Estas alterações são posteriores ao encerramento e não mudam os 41,7% registrados:

1. **Nomes curtos na pesquisa:** preservar nomes e siglas capitalizados de duas letras e sufixos romanos curtos ligados ao nome, sem convertê-los em números. Antes, `Helena II`, `Aurora IX`, `UK`, `UE` e `Xi` podiam perder parte da identidade na consulta neutra. Artigos, pronome `I` inicial, unidades e números soltos não recebem esse tratamento; a afirmação e as verificações factuais continuam intactas. Isso não é uma solução universal de identidades compostas: a deduplicação de palavras preexistente ainda pode colapsar nomes repetidos em entradas com várias pessoas.
2. **Buscas realmente repetidas:** a recuperação base deixa de reenviar uma consulta web idêntica, no mesmo idioma, já registrada. Preserva operadores, aspas, maiúsculas e espaços internos; somente espaços nas extremidades equivalem ao transporte. Outra consulta ou outro idioma permanece distinto. `/news` continua separado de `/search`. Falha ou timeout não repõe uma chamada nem autoriza repetir a consulta. A reprodução sintética passa de três envios para dois, mas não há duplicata comprovada desse tipo nos doze controles anteriores; não atribuir a essa correção um ganho de precisão ou a resolução do teto atingido na rodada.
3. **Mês escrito no caminho do artigo:** reconhecer uma data calendária completa em segmentos como `/2001/sep/18/` somente para ordenar referências ainda não lidas. O ranking pode distinguir um relato do mês alegado de uma retrospectiva meses depois. A data do endereço não preenche publicação nem corpo de evidência; query string, fragmento e datas inválidas não recebem a nova regra.

Uma reprodução offline com endereços Guardian registrados em 29/10, sem títulos para isolar a dica, mudou a faixa de setembro de “mês desconhecido” para “mês correspondente” e a retrospectiva de dezembro para “outro mês”. Antes eram indistinguíveis nesse recorte. O artigo não lido de setembro não foi buscado posteriormente; seu conteúdo e efeito no veredito permanecem desconhecidos.

**Validação posterior: 1.791 testes backend passaram, sem falhas, testes ignorados ou tentativas HTTP inesperadas.** Inclui 24 novos: oito de nomes curtos, nove de consultas repetidas e sete de caminhos com mês escrito. Rodaram em contêiner sem rede, sistema somente leitura, `.env` mascarado e bancos descartáveis. Os oito controles do apurador de porcentagem também passaram separadamente. Nenhum arquivo do frontend foi modificado; sua suíte e build não foram repetidos nesta etapa. Esses testes não representam uma nova medição de precisão factual.

O ambiente local principal foi reiniciado com os mesmos volumes. `/health`, `/ready` e a página `/app` responderam HTTP 200; hashes dos três arquivos de implementação no contêiner coincidem com os testados. Nenhuma nova análise foi enviada após as correções posteriores. Não houve alteração de chaves ou deploy no Railway/Vercel.

## Próximos passos para aumentar o acerto

- Priorizar recuperação estável de textos completos e independentes, em vez de aumentar novamente o prazo de uma busca que já terminou.
- Tratar definições locais e partes formais de documentos com vínculos auditáveis, sem misturar fatos de trechos ou atos diferentes.
- Avaliar a distribuição das buscas por análise. A busca de notícias e a busca web são corpora diferentes; retirar uma delas sem medir pode perder referências. Nenhuma fusão ou retirada foi feita nesta revisão.
- Medir as correções posteriores em outra rodada delimitada e, depois, em controles novos, apresentados separadamente dos textos conhecidos. Para superar 80% neste conjunto de doze seriam necessários pelo menos dez acertos; isso ainda não estima 80% em conteúdo geral.
- Revalidar imagem, voz e vídeo com autorizações e conjuntos próprios. Estes doze textos não fornecem porcentagem para outras modalidades.
