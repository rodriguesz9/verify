# Checagem factual: correções e resultado real — 16/10/2026

## Situação da entrega

Correções implementadas e testadas localmente. **Ainda não homologado para a apresentação como verificador factual confiável.** Seis pedidos reais pela interface permaneceram inconclusivos. Testes automatizados verificam contratos e regressões; não demonstram precisão de notícias do mundo real.

Este registro sucede a [bateria multimodal da mesma data](VALIDACAO-INTERFACE-2026-10-16.md), sem substituir seus resultados históricos. Base de código: `f92df07`. Desenvolvimento e testes ocorreram na cópia revisada, não sobre o checkout original com alterações do usuário. Sem publicação Vercel/Railway nesta rodada.

## Problemas corrigidos

1. **Busca excessivamente literal.** A afirmação original continua intacta. A recuperação adicional usa nomes, assunto e anos, sem exigir que a página repita um valor adulterado ou uma negação. Um vocabulário pequeno e explícito permite procurar instituições e assuntos em inglês. Não são afirmações reescritas por modelo nem evidências.
2. **Corpus primário inadequado.** Quando a entrada nomeia uma instituição conhecida, a busca primária é dirigida ao seu domínio: NASA, OMS/WHO, IBGE, Banco Central/Copom e Copernicus. Instituições desconhecidas mantêm a busca curada geral. A consulta editorial tem filtro próprio, sem NASA/Royal, para não devolver apenas outra página da mesma instituição.
3. **Pouca diversidade de candidatos.** A busca web passa de cinco para até dez links por chamada. Isso não aumenta o número máximo de chamadas de busca ou de páginas efetivamente lidas. Notícias contextuais continuam separadas da evidência.
4. **Recuperação sem oportunidade real de leitura.** Resultados das consultas qualificadas ganham prioridade. Uma página falha ou sem trecho utilizável deixa de reservar o lugar de toda a sua família editorial. Outra página da mesma família pode ser consultada, mas nunca conta como segunda confirmação independente.
5. **Siglas e tradução.** OMS/WHO e o nome completo da organização, assim como IBGE, recebem equivalência explícita. Há vocabulário restrito para impacto espacial, pandemia, PIB, temperatura e outros termos. Isso não resolve entidades arbitrárias ou toda paráfrase. A NASA não é intercambiável com a ESA; testes impedem essa troca.
6. **Direção de variações.** Os mesmos números não bastam para apoiar uma frase se origem/destino percentuais estiverem invertidos. Refutação por oposição exige uma transição percentual explícita invertida, ou uma comparação medida acima/abaixo com mesmo valor e unidade, além das demais guardas e da avaliação do modelo. Verbos opostos soltos não viram refutação.
7. **Datas e unidades.** Ano temporal introduzido por “em/in” pode corresponder a uma data completa daquele ano; uma data incompleta não comprova um dia específico. Quantias monetárias não são anos. `May` em data completa não é interpretado como o modal inglês. Celsius e Fahrenheit são unidades distintas; `°C` não é um nome em numeral romano. Eventos futuros apresentados como concluídos permanecem bloqueados.
8. **Metadados e navegação.** Datas soltas, inclusive seguidas de identificador de release, ficam como contexto e não se juntam ao parágrafo seguinte. O leitor reconhece `role="main"`. Cabeçalhos globais de navegação podem ser removidos, preservando manchetes e preâmbulos de negação. Essas últimas correções de extração receberam controles HTML offline; não houve nova homologação real de todos os sites após elas.
9. **Artigos longos.** A decisão documental pode preservar a evidência dos primeiros cinco segmentos de um texto maior. O restante continua fora da cobertura, impedindo aprovação global do artigo. Afirmações repetidas/identidade ambígua continuam bloqueadas.

## Limites preservados

- Até três buscas web, seis tentativas cumulativas de leitura em 45 segundos e três documentos na comparação. Falhas e redirecionamentos não são “reembolsados” no orçamento.
- Conteúdo do site é dado não confiável, nunca instrução para o modelo. Não se usaram snippets, títulos, conhecimento memorizado de IA ou concordância de modelos como prova de verdade.
- Veredito documental ainda exige evidência aceita de duas famílias distintas. Publicações copiadas/creditadas à mesma agência não são duas confirmações.
- Guarda final de entidades, evento, datas, valores, negação e unidades continua aplicada às citações escolhidas pelo modelo. JSON ou citação fora do contrato não produz conclusão.
- Não foi instalado outro provedor, contratado plano, ativado pagamento ou aumentado gasto Hive. Não houve alteração de banco de produção, segredos ou configuração remota.

## Testes reais pela interface

Ambiente isolado: frontend `127.0.0.1:5179`, backend `127.0.0.1:8033`, banco SQLite descartável. Nenhum backend/local do usuário em outras portas foi modificado. Chaves privadas foram importadas por lista permitida, sem configurações de banco/autenticação de produção.

| Pedido | Conteúdo | Resultado | Famílias utilizáveis na seleção |
| --- | --- | --- | --- |
| R1 | OMS caracterizou COVID-19 como pandemia em 11/03/2020 | Inconclusivo | 1 |
| R2 | DART/NASA colidiu intencionalmente com Dimorphos em 26/09/2022 | Inconclusivo | 0 |
| R3 | Elizabeth II morreu em 08/09/2022 | Inconclusivo | 0 |
| R4 | Controle adulterado: Elizabeth II morreu em 09/09/2022 | Inconclusivo | 0 |
| R5 | Mesmo controle DART, após melhoria da busca/recuperação | Inconclusivo | 1 |
| R6 | OMS classificou COVID-19 como pandemia, sem data adicional | Inconclusivo | 1 |

São **seis pedidos e cinco entradas distintas**, executados durante o desenvolvimento, não uma amostra independente. Os dois textos sobre a OMS também não são controles independentes entre si. Nenhuma taxa geral de acerto pode ser inferida. Cobertura conclusiva observada: **0/6**; precisão entre conclusivos: **não definida, pois não houve conclusivos**. A melhora de seleção da DART, de zero para uma família, não equivale a um veredito correto nem à validação da versão final para todas as notícias.

Os pedidos responderam HTTP 200 e renderizaram relatório. Isso valida transporte/fluxo, não utilidade factual. Tempos observados: aproximadamente 11–20 segundos. As evidências locais preservam os resultados que falharam; não foram trocadas por respostas esperadas.

### Por que permaneceram inconclusivos

- As páginas recuperadas nem sempre contêm a data inteira ligada ao evento e à pessoa na mesma sentença. Referências como “ela”, “hoje (8)” ou a data em outro parágrafo ainda perdem elegibilidade. O sistema não deve reconstruir essas relações pela URL ou data de publicação.
- Certas consultas retornaram várias páginas da mesma família ou páginas de assuntos adjacentes, por exemplo coroação em vez de falecimento. A recuperação melhorou, mas sua qualidade ainda precisa ser demonstrada.
- Algumas páginas não puderam ser lidas; uma página da OMS excedeu o limite de contexto inicial, com navegação misturada. O reconhecimento de região principal e a limpeza de cabeçalhos globais foram acrescentados após esse achado; ainda precisam de replay real.
- No controle final sem data, uma página governamental foi elegível, mas não houve segunda família utilizável. O OpenRouter respondeu à extração. A comparação não foi chamada porque a seleção não atingiu duas famílias. **Isso não valida nem invalida o funcionamento do modelo de comparação.**

### Uso de serviços nesta rodada

O registro de transporte continuou o orçamento anterior sem apagar contadores. Variação desta rodada:

| Serviço | Novas tentativas |
| --- | ---: |
| OpenRouter gratuito, extração | 6 |
| Google Fact Check | 6 |
| Serper, notícias e busca web | 24 |
| Leitura HTTPS pública | 26 |
| Gemini | 0 |
| Hive, Sightengine, AssemblyAI e HF | 0 |

Os 26 envios HTTPS de leitura não são 26 fontes independentes: incluem redirecionamentos e tentativas. Algumas falhas ocorrem antes do envio HTTP. O teto local Serper desta rodada foi atingido; não se iniciou outra rodada automática nem se compraram créditos. O saldo Hive não foi utilizado. Gemini/mídia, produção e disponibilidade contínua não foram revalidados aqui.

## Testes automatizados e reprodução

Controles sem rede: identificação de siglas, identidade incorreta, datas completas/anos/ISO, possibilidade, futuro, unidades, transições de taxas invertidas, valores/dias diferentes, cabeçalhos, página alternativa da mesma família, negação e artigos com cobertura parcial. As fontes dessas unidades são inventadas; não são notícias reais nem estimativa de acurácia.

Resultados locais finais: **763 testes backend**, zero falhas/skips/chamadas reais; **20 arquivos de teste frontend** passaram; build Vite concluído. O runner backend usa bancos descartáveis e bloqueia transportes HTTP. PostgreSQL e produção não foram exercidos nesta rodada.

No diretório `backend`, executar `python -B scripts/run_offline_tests.py` em ambiente com dependências, FFmpeg/ffprobe e Poppler. No diretório `frontend`, executar `npm test` e `npm run build`. O `.env` de produção não deve ser utilizado pelos testes offline.

## Trabalho ainda necessário para fechar a checagem

1. Tratar relações entre sentenças do mesmo parágrafo, com IDs/limites explícitos e contexto integral. Exigir testes contra empréstimo da data do funeral, morte de parentes, outra taxa, outro sujeito e qualificadores de negação. Não remover guardas para “fazer passar” os controles.
2. Revalidar extração em páginas reais da OMS/NASA e recuperar fontes independentes para as entradas históricas que falharam. Sem URLs de resposta ou fixtures injetadas no resultado de produção.
3. Exercitar a comparação estruturada OpenRouter/Gemini em corpos reais elegíveis e comprovar citações/decisão na interface, incluindo notícias falsas. As seis extrações OpenRouter desta rodada não cobrem essa fronteira.
4. Reservar corpus independente e separado do desenvolvimento, com verdadeiros, falsos e casos que exigem abstenção. Publicar cobertura, precisão dos conclusivos e erros por tipo; não anunciar “100%” com esta bateria.
5. Somente depois: revisar configuração de produção, publicar e repetir smoke tests com a conta autorizada. Nenhuma correção local prova que Railway/Vercel estejam usando esta revisão.
