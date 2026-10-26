# Queda de acertos: diagnóstico controlado — 26/10

## As IAs responderam na última medição?

Não todas de forma utilizável. Na [rodada real de 25/10](RECUPERACAO-E-TESTES-2026-10-25.md), Gemini teve onze respostas HTTP 200 e duas 503. OpenRouter teve uma resposta HTTP 200 rejeitada como inválida. Esses contadores incluem tarefas diferentes; não significam onze vereditos completos. Seis dos sete inconclusivos pararam antes da comparação por falta de corpos elegíveis. Constituição chegou à comparação, mas os modelos falharam.

Receber a requisição, produzir texto e concluir uma revisão válida são etapas distintas. Concordância entre IAs ou conhecimento próprio de um modelo não substituem as fontes consultadas. O sistema usa o provedor alternativo quando ocorre uma falha prevista, sem solicitar outro julgamento apenas porque o primeiro foi inconclusivo.

## Comparação com entradas fixas

[Registro sanitizado do replay anterior à correção de siglas](diagnostic-controlled-replay-2026-10-26.json). Foram usados 36 conjuntos salvos de documentos públicos, doze de cada rodada: 75%, 50% e 41,7%. Cada conjunto recebeu as mesmas quatro versões históricas da preparação de evidências e a versão-base `94681e6`.

**Para a mesma entrada, a saída completa da preparação foi idêntica nas cinco versões.** A comparação cobre seleção de trechos, exclusões, passagens e documentos selecionados. As funções centrais de leitura, vínculos e decisão também foram comparadas; não apareceu regressão desses filtros nesse intervalo.

Os registros antigos não conservaram data de publicação e créditos estruturados. Esses campos foram reconstruídos com o leitor-base a partir do mesmo HTML salvo, após conferir título, sentenças, papéis e truncamento: zero diferenças e zero arquivos ausentes. A prova especial de comunicado oficial do Copom não foi retida nessa projeção; seu caminho completo não foi reproduzido.

| Caso | Famílias elegíveis no primeiro conjunto | No segundo | No último |
| --- | --- | --- | --- |
| Elizabeth, data verdadeira | EBC + Globo | Globo | Globo |
| Webb | Globo + UOL | UOL | UOL |
| Copernicus | Copernicus | Copernicus | nenhuma |
| Copa | nenhuma | BBC + Globo | Globo |
| OMS | OMS | OMS | CNN + OMS |
| DART | nenhuma | nenhuma | nenhuma |
| Constituição | duas | duas | duas |

Isso separa comportamento dos filtros de variação nos documentos recebidos. **Não elimina a possibilidade de regressão na recuperação/ordenação:** títulos completos da busca e a seleção final exata não foram capturados. Elegibilidade documental também não é o resultado completo: Fact Check e registros institucionais podem fornecer outras evidências.

## Correções

### Cabeçalho não contamina o primeiro parágrafo

Uma página salva da CNN inseria nome da jornalista e texto de um botão antes da definição do telescópio, na mesma sentença do corpo. A causa estava na estrutura HTML: o cabeçalho do artigo era percorrido como texto corrido. A correção identifica um cabeçalho semântico com título e uma região de prosa posterior, conserva suas divisões e o mantém como contexto. Não depende de nomes de jornalistas, frases de botões ou seletores de um site específico.

Títulos, subtítulos, autoria e créditos permanecem visíveis à análise. Uma indicação como “É falso que:” continua controlando o parágrafo seguinte. Cabeçalho que envolve o próprio corpo explicitamente marcado não recebe essa classificação por suposição.

### Sigla definida no próprio corpo

A página define o nome completo de um instrumento e depois usa sua sigla no trecho que descreve o evento. A antiga janela de até três sentenças perdia essa ligação. Agora uma definição literal no corpo pode resolver a sigla inicial de uma sentença posterior, até 24 sentenças de distância e 3.600 caracteres de contexto total. Todo o texto intermediário e os títulos próximos são mantidos; não se monta uma citação com frases distantes.

Somente o sujeito completo da afirmação recebe uma leitura interna com a sigla. A citação original, datas, ações e demais qualificadores ficam intactos. Definições em título/legenda, nome subordinado a “réplica”/“desenho”/“dono”, redefinições e siglas conflitantes são rejeitadas. O servidor revalida a definição após a revisão do modelo; o modelo ainda precisa revisar todas as fontes e a política de independência permanece.

Os testes também revelaram um filtro de instruções que não reconhecia as formas naturais “Ignore todas as instruções anteriores” e “Ignore all previous instructions”. Ambas agora impedem que o documento produza evidências ou chamadas de comparação. Isso corrige a triagem delimitada; não é uma garantia de detectar toda instrução maliciosa possível.

### Resposta inválida do OpenRouter

O cliente distingue limite de tokens, conteúdo vazio, término anormal, conteúdo incompatível, envelope malformado, tamanho excessivo, custo inesperado e erro declarado pelo provedor. Os diagnósticos exportam categorias fixas e códigos permitidos; nunca mensagens brutas, raciocínio, credenciais ou cabeçalhos.

A documentação oficial informa que [um erro pode chegar no corpo mesmo com HTTP 200](https://openrouter.ai/docs/api/reference/errors-and-debugging). O cliente agora reconhece esse envelope, sem transformar seu código interno em status HTTP. Erros de quota no corpo também ativam a pausa local. Uma falha reconhecida pode alcançar a alternativa já prevista pelo pipeline, dentro do mesmo prazo; não há rotação adicional entre modelos OpenRouter.

Resposta truncada, incompleta ou fora do contrato continua sem voto nem pedido de um veredito alternativo. A documentação também descreve [esgotamento de tokens por raciocínio](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens); isso é uma hipótese para respostas vazias, **não uma causa comprovada da falha anterior**, cujo corpo não foi retido. Não foram alterados modelo, chave, quota, política de preço zero ou prazo.

### Registros de avaliação

A captura local de documentos públicos conserva agora data ISO de publicação e créditos visuais estruturados, com validação de formato e tamanho. Campos antigos ausentes continuam ausentes; não há migração nem datas inventadas por título/URL. Isso melhora a fidelidade de replays futuros, mas ainda não captura todo o pipeline, registros especiais ou todos os detalhes de ordenação.

## Verificação do código

**1.563 testes backend passaram**, sem rede, credenciais privadas ou skips: 48 controles novos sobre os 1.515 anteriores. São 22 controles de identidade/siglas e integração, sete de estrutura do cabeçalho, dezesseis de resposta/transporte OpenRouter e três de captura de metadados. Revisão completa simulada pode usar as duas fontes; família única, identidade ambígua, data errada, evento planejado e contexto fictício não se tornam apoio por causa da sigla. Saída parcial continua sem alternativa de julgamento; erro declarado de serviço pode usar a alternativa já prevista, dentro do mesmo prazo.

## Replay depois da correção

[Comparação sanitizada antes/depois](diagnostic-body-repair-replay-2026-10-26.json). Nova cópia congelada do código foi aplicada aos mesmos 36 conjuntos de HTML, preservando os horários originais de recuperação. O leitor e a preparação antigos foram reconstruídos de `94681e6`; hashes dos documentos, famílias e contagem de passagens da base coincidiram com o primeiro replay.

**Webb, no último conjunto: uma família elegível (UOL) passou a duas (UOL + CNN), e uma passagem passou a duas.** A nova passagem preserva o trecho real de lançamento e a definição explícita da sigla no corpo. Não há resposta histórica fixa, data inferida por legenda ou voto por título.

Nos outros 35 conjuntos, famílias e quantidade de passagens elegíveis permaneceram iguais. A separação de cabeçalhos mudou a estrutura de 22 documentos em 17 conjuntos, sem perda observada de família elegível. Os 81 arquivos Python usados foram conferidos contra a cópia congelada ao terminar. Isso demonstra recuperação de uma evidência antes descartada; **não demonstra um novo veredito remoto correto nem nova porcentagem de acerto**.

DART continua sem vínculo completo de intenção/data no material elegível; Copa, Artemis e Elizabeth ainda precisam de outra fonte independente que cubra todos os qualificadores. A recuperação do período correto limita Copernicus. Falhas remotas dos modelos continuam possíveis. Esses pontos permanecem abertos, sem converter ausência de prova em verdade ou falsidade.

## Limites

Esta etapa é offline, sem novas chamadas a APIs, consumo Hive ou implantação. A última medição factual continua **5/12 corretos (41,7%), sete inconclusivos**, em controles de desenvolvimento conhecidos. Testes de código e replays não atualizam essa porcentagem nem demonstram 80% de acerto geral. Interface e mídias não foram revalidadas nesta etapa.
