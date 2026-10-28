# Rodada completa e correções posteriores — 28/10/2026

**Resultado real: 5/12 acertos (41,7%), sete inconclusivos, nenhuma conclusão errada observada e nenhum erro terminal HTTP.** Os doze textos foram enviados pelo formulário e seus doze relatórios foram observados no navegador. A meta de 80% não foi atingida. [Dados sanitizados, cobertura e provas](validation-quality-2026-10-28.json).

## O que foi medido

- Código congelado: `e0c6dc67d177516b1b2b9ca09cf9319036a78d7a`.
- SHA-256 de implementação: `1013d26497876341c0abdb539234b08bd57ed000a9d1d1060d3bb954817cb3df`.
- Os mesmos doze controles de desenvolvimento, já conhecidos, na mesma ordem. Uma tentativa por texto; nenhum rótulo esperado ou URL de referência foi passado à aplicação.
- Ambiente separado, banco e conta descartáveis, interface e API na mesma origem local. Não usou o banco principal, Railway ou uma implantação de produção.
- Congelamento verificado após todos os relatórios, antes das correções posteriores. Rodada encerrada, servidor temporário parado e aba temporária fechada. Registros e reservas persistentes preservados.

Inconclusivos e erros entram no denominador. O resultado não estima precisão geral, não é avaliação cega e não mede autenticidade de imagem, voz ou vídeo.

| Grupo esperado | Corretos | Inconclusivos | Conclusões erradas | Acerto sobre todos do grupo |
| --- | ---: | ---: | ---: | ---: |
| Verdadeiros | 3/6 | 3/6 | 0 | 50,0% |
| Falsos | 2/6 | 4/6 | 0 | 33,3% |
| Total | 5/12 | 7/12 | 0 | 41,7% |

| Controle | Resultado observado | Comparação com 27/10 |
| --- | --- | --- |
| Declaração da OMS | Verdadeiro, correto | Manteve |
| Brasil campeão da Copa de 2014 | Inconclusivo | Manteve |
| Temperatura do Copernicus, direção invertida | Inconclusivo | Manteve |
| Decisão do Copom, taxas invertidas | Falso, correto | Manteve |
| Artigo da Lei Áurea, declaração negada | Inconclusivo | Perdeu um acerto |
| Lançamento do James Webb | Verdadeiro, correto | Manteve |
| Lançamento de Artemis I, ano falso | Inconclusivo | Manteve |
| Falecimento de Elizabeth II, data verdadeira | Verdadeiro, correto | Manteve |
| PIB brasileiro divulgado pelo IBGE | Inconclusivo | Perdeu um acerto |
| Falecimento de Elizabeth II, data falsa | Falso, correto | Ganhou um acerto |
| Impacto intencional da DART | Inconclusivo | Manteve |
| Promulgação da Constituição | Inconclusivo | Perdeu um acerto |

Em 27/10 foram 7/12 acertos (58,3%). Esta rodada perdeu três acertos e ganhou um: queda líquida de dois, ou 16,7 pontos percentuais. Não se combinam os melhores resultados de versões diferentes. Código, buscas, disponibilidade das páginas e modelos selecionados variaram; não é um experimento que isola o efeito do código.

## As APIs responderam?

| Serviço | Enviadas / limite autorizado | Respostas |
| --- | ---: | --- |
| Gemini | 8/16 | Oito HTTP 200; oito planos de pesquisa aceitos |
| OpenRouter | 4/12 | Quatro HTTP 200; quatro comparações completas aceitas |
| Google Fact Check | 12/12 | Doze HTTP 200 |
| Serper | 60/60 | Sessenta HTTP 200 |
| Leituras públicas | 73/120 | 59 HTTP 200; duas 401; quatro 403; quatro 301; duas 307; duas tentativas incompletas |
| Hive, Sightengine, AssemblyAI e Hugging Face | 0 | Não chamados |

Gemini usou `gemini-3.5-flash-lite` para planejamento. O OpenRouter usou o roteador gratuito com preços máximos zero; os modelos observados foram `dots-studio/dots-3-note-preview:free`, `liquid/lfm-2.5-2.6b:free` e `nvidia/nemotron-3.5-super-vl:free`. Não houve chamada de comparação Gemini: nas quatro comparações executadas, o provedor primário respondeu validamente.

**Os sete inconclusivos pararam antes da comparação pelas IAs.** Faltaram trechos utilizáveis de duas famílias de fontes. O caso correto do Copom usou o registro original da própria instituição, dentro da exceção documental já delimitada. HTTP 200 de busca ou planejamento não significa que o fato foi confirmado.

Tempo mediano de execução: 29,154 s. Percentil 95 pelo método de posto mais próximo: 57,853 s. São tempos do processamento registrado, sem o intervalo entre ações do navegador.

O teto de sessenta buscas foi atingido. No último controle, a recuperação editorial reportou `error`, não houve planejamento adicional e só uma família ficou elegível. O encerramento do orçamento é uma limitação concreta desta avaliação; o registro não conserva a exceção dessa consulta para atribuir o erro exclusivamente ao teto. Não houve aumento de limite, reinício ou reenvio para escolher um resultado melhor.

## Causas demonstradas e próximos reparos

### Lei Áurea: a busca mudou de documento

Em 27/10, a busca levou à publicação original da Câmara, com o artigo 1º literal. Em 28/10, a mesma consulta levou à ficha “Dados da Norma”. Essa ficha não contém o artigo, mas tem uma âncora visível “Texto - Publicação Original”. A descoberta ignorava o link porque ele está fora de parágrafo/callout e seu rótulo é genérico.

A correção posterior implementada segue apenas esse vínculo institucional delimitado: mesmo host, diploma, data, tipo, faixa e identificador do registro; cabeçalho legal visível completo; âncora real única. Não fabrica URL nem transforma ementa, metadados ou cabeçalho em conteúdo de artigo. A leitura usa as mesmas duas referências diretas e dez tentativas existentes.

### Artemis: o corpo recuperado contém uma construção não reconhecida

Uma página da Folha recuperada nesta rodada afirma a partida da missão em uma quarta-feira, com dia 16 explícito e publicação em 16/11/2022. A gramática temporal não reconhecia a missão como sujeito de “partiu”, com a explicação nominal do voo de foguete e cápsula entre sujeito e verbo.

A correção posterior implementada exige frase completa, missão numerada, lançamento inequívoco, dia e semana concordantes com a publicação. “Partiu” exige a explicação explícita de primeiro voo com foguete e cápsula; “decolou” é reconhecido como predicado de lançamento. Ida à plataforma, transporte, preparação, hipótese, negação, datas de outro evento e qualificadores adicionais da afirmação continuam impedindo a equivalência automática. Citação e contexto literais permanecem disponíveis. Previsão ou plano adjacente sobre a mesma missão impede a leitura como fato concluído, inclusive quando a citação se repete; uma discussão futura independente não é automaticamente uma previsão desse evento.

A ponte vídeo→artigo corrigida antes da rodada não foi exercida nesse caso: a página de vídeo da BBC usada no teste anterior não foi recuperada agora. O artigo textual apareceu diretamente na busca; nenhum corpo dele foi salvo. Os registros não distinguem ausência de seleção de falha de leitura desse endereço.

### PIB: faltou recuperar a segunda fonte

G1 continuou elegível. A consulta que antes encontrava uma notícia completa da CNN passou a retornar um arquivo de notícias e textos de outros períodos. O arquivo capturado não tem a afirmação completa com valor, período e divulgação nem o link necessário para recuperar aquele artigo. Não há quebra demonstrada do parser: o replay com os documentos antigos preserva as duas famílias.

Uma melhoria a avaliar é diversificar um slot existente com entidade, ano e quantidade/unidade literais, mantendo consultas neutras para afirmações com números falsos. Ainda é proposta; não foi medida nem serve para reutilizar o endereço esperado do controle.

## Limites das correções posteriores

A medição termina em `e0c6dc6`. Reparos feitos depois do encerramento são verificações locais separadas: testes sintéticos e corpos públicos já capturados podem demonstrar descoberta, vínculo e proteção contra falsos positivos, mas não criam novos acertos reais. A precisão permanece 41,7% até outra avaliação autorizada e completa.

## Validação posterior sem rede

**1.739 testes backend passaram, sem falhas ou testes ignorados**, incluindo 32 novos: quinze de referência legislativa e dezessete de data/escopo de lançamento. A revisão independente também reproduziu e verificou o bloqueio de previsões e de contextos com citações repetidas. A suíte do frontend não foi repetida; não houve alteração em seus arquivos.

O replay usa exatamente os documentos e HTMLs da rodada de 28/10, comparando `e0c6dc6` com as correções posteriores, sem modelo, credencial ou acesso externo. [Resumo sanitizado, contagens e hashes](validation-post-round-offline-2026-10-28.json).

- **Artemis:** passou de uma para duas famílias elegíveis nos documentos salvos, tanto no conteúdo estruturado quanto na releitura do HTML. A declaração da Folha passa a ser ligada à data completa sem perder a citação literal; NASA permanece elegível. Isso permite uma comparação que estava bloqueada, mas não equivale a executar novamente a aplicação com APIs reais.
- **Lei Áurea:** a ficha agora fornece o endereço original pelo seu link real. O destino não foi buscado nesta etapa; a ficha continua sem evidência de artigo e sem conclusão factual.
- **Outros controles:** contagens de famílias elegíveis preservadas nesse recorte. O replay de HTML omite o registro estruturado oficial do Copom e, portanto, não reproduz isoladamente seu acerto real; essa lacuna não é tratada como regressão nem preenchida com o resultado esperado.

Permanecem pendentes recuperação estável de fontes independentes, vínculo auditável de definições locais de medidas, controles ainda não usados no desenvolvimento e revalidação de mídia. Aumentar o prazo não basta para corrigir ausência de documento ou vínculo incompleto quando as leituras já terminaram.

Ambiente local revisado reiniciado com os mesmos volumes: `/health` e `/ready` retornaram HTTP 200, banco pronto; `/app` em `http://127.0.0.1:5176` respondeu HTTP 200. Os quatro arquivos de implementação no contêiner coincidem com os hashes testados. Nenhuma análise remota foi submetida após os reparos; não houve deploy de Railway/Vercel nesta etapa.

Provas visuais preservadas: [data falsa corretamente refutada](evidencias-2026-10-28/data-falsa-refutada.jpg) e [Constituição inconclusiva](evidencias-2026-10-28/constituicao-inconclusiva.jpg). As demais dez capturas e provas de submissão permanecem no registro local da rodada; seus hashes constam no resumo sanitizado.
