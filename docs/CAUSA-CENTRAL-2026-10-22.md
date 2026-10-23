# Inconclusivos: correções centrais e validação

Revisão iniciada em 22/10 e auditada em 23/10/2026. Não confirma publicação nem precisão de imagem, áudio ou vídeo. A medição abaixo usa a política documental `2026-10-22.2`; reforços posteriores usam `2026-10-23.1` e são separados.

## Diagnóstico comprovado

O problema não se reduz a uma chave ausente ou a um timeout. Há três etapas distintas: recuperar uma página pertinente, extrair uma passagem utilizável e comparar essa passagem com a afirmação inteira. Uma resposta HTTP 200 não garante nenhuma das duas últimas etapas.

| Falha encontrada | Efeito | Correção |
| --- | --- | --- |
| Crédito fotográfico da Reuters tratado como autoria textual | G1 e Agência Brasil se tornavam uma única família; a comparação nem começava | Procedência visual estruturada, limitada e validada separadamente; autoria textual e créditos de republicação continuam preservados |
| Assuntos desconhecidos enviados a um filtro fixo de instituições | Leituras limitadas gastas com páginas vazias ou de outro assunto | Busca aberta quando nenhuma instituição é explicitamente identificada; o plano da IA não pode inventar uma instituição para o usuário |
| Diversidade de famílias antes da pertinência/readabilidade | Página de outra família, mas irrelevante, ultrapassava artigo útil | Diversidade dentro das faixas de qualidade da fila; títulos/URLs continuam sendo pistas, nunca prova |
| Gemini consumia a maior parte dos 90 segundos e sobrava pouco ao OpenRouter | A API alternativa podia encerrar antes de terminar uma matriz de fontes | Comparação até 180 s compartilhados; até 90 s por provedor, com divisão equilibrada quando resta menos tempo |
| Timeout HTTP por operação no OpenRouter | Um fallback explícito podia ganhar um segundo prazo inteiro | Prazo único envolvendo cliente e tentativas; cancelamento propagado, sem repetição após 402/429 |
| Declaração legal já delimitada ainda dependia de modelo remoto | Indisponibilidade do modelo impedia uma comparação literal possível | Parser completo de diploma, artigo, objeto ordenado, negação externa e qualificador fechado; matriz literal antes do modelo |

Replay dos mesmos documentos de Elizabeth II: **uma → duas famílias elegíveis**, sem buscar páginas adicionais. O seletor permaneceu idempotente. Isso é uma prova causal da recuperação da evidência, não uma nova porcentagem de precisão.

Na investigação de versões anteriores, páginas sem ano no corpo ou com data divergente não foram corrigidas artificialmente, nem tiveram legendas promovidas a prova. Isso explica diferenças de cobertura entre recuperações; não altera o resultado da Constituição na rodada congelada abaixo, que foi correto.

## Espera sem travamento indefinido

- Pipeline textual compartilha orçamento de até 330 s para trabalho remoto; o tempo já gasto na extração reduz o disponível à comparação.
- Etapa paralela de consultas tem até 110 s. Resultados terminados são mantidos; consultas pendentes são canceladas e aguardadas antes da montagem do relatório.
- Busca/leitura conserva 105 s e os limites de páginas existentes. Planejamento continua dentro desse prazo, com reserva para ler páginas reais.
- Comparação padrão: `SOURCE_CROSSCHECK_TIMEOUT_SECONDS=180`, permitido 10–180. Cada chamada recebe no máximo 90 s, sem ultrapassar o restante da análise.
- Interface continua aguardando até seis minutos. O orçamento é cooperativo com os clientes de rede; não promete resposta de um fornecedor indisponível nem interrompe à força processamento síncrono do sistema.
- Uma comparação válida que informa evidência insuficiente não é reenviada a outra IA para obter uma conclusão desejada. Falha de transporte pode usar a alternativa; opinião ou concordância das IAs não são votos de fonte.

`GEMINI_REQUEST_TIMEOUT_SECONDS` permanece 10–90 para chamadas comuns. A comparação usa um prazo específico por chamada, dentro dos limites acima. `OPENROUTER_MODEL=openrouter/free` e preços máximos zero continuam bloqueando modelos pagos. O limite de provedor não é aumentado nem contornado por esta mudança.

## Segurança e significado dos vereditos

Créditos de fotos só são excluídos do cálculo de dependência quando vierem de uma unidade visual explícita e o fragmento for validado no corpo. Não são removidos da evidência/contexto. Metadado ausente, inválido ou incompatível mantém o comportamento conservador anterior. “Por Reuters”, “Segundo a Reuters” e crédito textual misto continuam indicando dependência.

O novo parser legal não interpreta consequências sociais, validade atual da norma ou a situação real descrita. Só compara o que o artigo identificado declara. Condições, exceções, dupla negação, objeto diferente, outro diploma e qualificadores omitidos não recebem uma relação literal. A prova de publicação original, as guardas de contexto e a decisão final continuam obrigatórias.

Não foram adicionadas tabelas de respostas históricas nem referências dos rótulos à recuperação. Nenhuma ausência de evidência passa a significar falsidade. Documentos conflitantes continuam impedindo uma conclusão global simples.

## Validação

Código avaliado: `21aa4191d33067a1e9dc83a5952a5025f4b85c6582a2495bfb42f4ace6c2a668` — impressão SHA-256 dos caminhos e bytes de `backend/app` e `frontend/src`, sem segredos.

- **1.318 testes backend passaram**, sem rede, sem `.env`, zero skips e zero chamadas HTTP inesperadas.
- **22 arquivos de teste frontend passaram; build concluído.**
- Rodada real conhecida: **7/12 corretos (58,3%), cinco inconclusivos, nenhuma conclusão errada observada e nenhum erro de execução**. Inconclusivos permanecem no denominador. [Dados sanitizados](validation-central-2026-10-22.json).
- Uma submissão foi feita pelo formulário, com carregamento/relatório/screenshot observados. Onze foram feitas por HTTP comum; não são onze testes visuais. Os doze retornaram HTTP 200.
- Rodadas anteriores ficam preservadas: última válida 4/12 (33,3%); anterior 8/12 (66,7%). Os oito casos novos anteriormente avaliados já são controles conhecidos e não serão chamados de inéditos novamente.

Plano real desta rodada: uma tentativa por controle, código/entradas/harness congelados, até 30 Gemini, 8 OpenRouter, 20 Fact Check, 70 buscas e 120 leituras públicas. As 40 reservas OpenRouter anteriores foram preservadas; máximo conservador após esta rodada é 48, sem reset do diário anterior. Nenhuma chamada paga Hive, mídia ou banco de produção.

O limite gratuito e a disponibilidade são próprios de cada conta/provedor: [OpenRouter](https://openrouter.ai/pricing), [Gemini](https://ai.google.dev/gemini-api/docs/rate-limits). Aumentar a espera não resolve por si só HTTP 503, quota esgotada ou falta de uma passagem adequada.

Foram registradas 153 tentativas dentro dos limites: 12 Gemini (dez HTTP 200, um 503, um incompleto), dois OpenRouter (ambos incompletos), 12 Fact Check, 59 buscas e 68 tentativas de página. Não houve HTTP 429 externo nessa rodada. Os diários não foram reiniciados: OpenRouter ficou em 42 reservas conservadoras acumuladas, não 48 consumidas. Cinco conclusões usaram comparação por modelo; duas, comparação literal. HTTP 200 não equivale automaticamente a uma comparação utilizável.

### Onde ainda faltou

| Controle | Resultado | Diagnóstico registrado |
| --- | --- | --- |
| Elizabeth II, data falsa | Inconclusivo | Duas famílias elegíveis, mas Gemini indisponível e OpenRouter terminou sem resposta no prazo |
| DART | Inconclusivo | Sete páginas lidas; nenhum trecho elegível cobre integralmente evento, data e intencionalidade |
| OMS | Inconclusivo | Duas páginas lidas e quatro falhas; somente uma família elegível |
| Copa de 2014 | Inconclusivo | Uma família elegível; relação completa em outra redação do corpo ainda não reconhecida pelo parser |
| Artemis I | Inconclusivo | Uma família elegível; corpo em voz ativa e data relativa não reconhecidos pelo leitor de lançamento passivo |

Ganhos frente aos 4/12: Elizabeth verdadeira, lei, Webb e Constituição. Regressão: Copa. Saldo de três acertos a mais, ainda abaixo da meta. Contagens de candidatos rejeitados são diagnósticos limitados, não número de fontes nem demonstração de uma causa exclusiva.

### Reforços posteriores à medição

A revisão independente encontrou colisão entre crédito visual e autoria: o mesmo fragmento podia aparecer numa foto e numa linha “Texto e Foto”. A remoção global apagava as duas ocorrências. Agora fragmentos repetidos falham de modo conservador: não são excluídos da dependência editorial. Um crédito visual não pode apagar a autoria de uma agência.

O veto inclui unidades visuais com prefixo misto, como “Texto e Foto”. Na avaliação final, a família já preparada a partir do corpo completo é preservada: não se faz uma segunda classificação com o crédito fotográfico do contexto local, que reintroduziria a falha original.

Também foi corrigida uma regressão do parser legal: redação não reconhecida não é automaticamente uma relação inválida. “Declara-se” ganhou uma equivalência fechada; outros estilos sem condição explícita mantêm a comparação comum por modelo. Condições, exceções e objetos divergentes continuam bloqueados.

O leitor de competição passou a aceitar um relato português completo de gol, autoria nominal e conquista da Copa por um gentílico identificado. A relação exige torneio e edição no próprio corpo. O mapa contém somente equivalências linguísticas entre gentílicos e países, nunca vencedores por ano; caudas desconhecidas, categorias diferentes e ficção são recusadas.

O leitor de lançamento passou a reconhecer uma agência que **lançou** uma missão numerada, seguida de objeto explícito e data relativa completa. Dia, mês quando presente e dia da semana devem concordar com a publicação explícita. A identidade I/1 é revalidada, sem inferir missão a partir de um foguete. Só afirmações de missão/data recebem essa leitura; agência, horário, local e outros detalhes alegados não podem desaparecer. Complementos nominais são inteiramente delimitados, não cortados.

A leitura interna datada não substitui a citação original. Cabeçalho fictício, simulação, hipótese e negação adjacente impedem a conclusão; “não tripulada” é tratado apenas como o qualificador fechado de tripulação, não como negação do lançamento. Âncoras adulteradas, data futura e data existente apenas em legenda continuam sem voto.

Esses reforços têm controles offline próprios e **não estão incluídos nos 58,3%**. Não se reutiliza a medição anterior como se tivesse avaliado código posterior.

Replay integral sem rede dos documentos já capturados confirmou as duas correções de leitura: Copa, sete corpos → duas famílias (`globo` e `bbc`); Artemis, sete corpos → duas famílias (`nasa` e `uol`). Ambos produziram refutação literal com duas evidências, cobertura completa e nenhuma chamada Gemini/OpenRouter. No segundo, o corpo original da Folha foi preservado, com data de publicação e identidade da missão revalidadas. É diagnóstico offline posterior, não uma nova rodada real nem uma porcentagem adicional.

Os metadados internos de tempo também foram separados da cobertura pública: orçamento de execução não é um fornecedor indisponível. Eles não podem criar o aviso genérico de etapa falha; timeouts e indisponibilidades reais das APIs continuam visíveis.

Revisão final: SHA-256 `249b93992305c54ad003fffdd3571d5b6de4ac392cd49c9ce925fffb5e6c9791`, 128 arquivos da aplicação; **1.345 testes backend passaram**, zero skips/HTTP inesperado; 22 arquivos frontend e build passaram. Os diários e os corpos públicos da rodada anterior foram mantidos intactos; não houve reenvio de APIs após esses reforços.

## Para retomar no Railway

Quando publicar esta revisão, ajustar **somente a variável não secreta** `SOURCE_CROSSCHECK_TIMEOUT_SECONDS=180` se desejar o novo padrão; um valor antigo explícito de 90 continuará valendo. Manter as chaves apenas no backend. Não copiar o banco, as credenciais descartáveis ou as opções do harness QA para produção.

Esta revisão não foi implantada automaticamente. Antes de declarar conclusão: medir novamente o conjunto completo, analisar erros por etapa, validar casos novos independentes e revalidar mídias com corpus autorizado e orçamento próprio. **80% gerais e 100% de vereditos corretos continuam não demonstrados.**
