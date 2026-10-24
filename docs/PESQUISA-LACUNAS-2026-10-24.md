# Pesquisa direcionada às lacunas — segunda revisão de 24/10

Versão após `ede5759`. Código congelado antes da avaliação: SHA-256 `26b80e10a8772d9bfd5aceda4fda8c5f2c6b710052d4f6e7f6d62ef5799b01b2`. A rodada anterior permanece em [9/12, 75%](VINCULOS-E-REVISAO-2026-10-24.md); não é garantia de acerto geral.

## Causas verificadas e mudanças

As falhas DART/Copa/Artemis da rodada anterior ocorreram antes da comparação final: não havia duas famílias de documentos com trechos elegíveis cobrindo os detalhes alegados. Chaves ativas e mais espera não acrescentam detalhes ausentes no corpo.

- O planejador de pesquisa agora recebe pistas lexicais delimitadas sobre o trecho próximo: precisão de data ausente, intenção explícita ausente, nomes e quantidades ausentes. As contagens agregadas de rejeições genéricas antes escondiam essa distinção. As pistas apenas orientam busca; presença de palavras não comprova relação semântica e não muda nenhum veredito.
- O fallback de descoberta de missão numerada preserva identidade e qualificadores, mas pesquisa a data do lançamento sem repetir a data disputada. Inclui grafias numérica/romana equivalentes, geradas do número validado, sem catálogo de missões ou respostas. Casos não reconhecidos mantêm o fallback integral anterior. Não altera afirmação original, duas consultas máximas ou exigência de evidência.
- Métricas offline passam a expor acerto com todos os casos no denominador, contagem de conclusões erradas e abstenções. A precisão apenas dos resultados conclusivos continua separada e não pode ser apresentada como acerto geral.

Nenhum parser novo foi adicionado só para fazer os três exemplos passarem. O parser de lançamento já compreendia a frase completa NASA. A página da missão não foi promovida a registro decisivo único. Legenda, data de publicação, título ou informação de outro evento continuam sem preencher datas faltantes.

## Verificação antes da medição

1.448 testes backend passaram sem rede, credenciais ou skips; 18 testes novos nesta revisão. 22 arquivos de testes frontend e build passaram. Revisão independente não encontrou regressão acionável nas mudanças de pesquisa e métricas. Os 22 controles sintéticos do instrumento de avaliação passaram; não são porcentagens de acerto.

## Protocolo de avaliação real

Vinte textos, uma tentativa por texto: os mesmos doze controles conhecidos e oito novos de legislação, educação, ciência, saúde, direitos humanos e esporte. Ordem fixada antes dos envios: seed 20261024, blocos intercalados de três conhecidos e dois novos. Acertos dos grupos de 12/8 permanecem separados; inconclusivos e erros não são retirados dos denominadores.

Fontes primárias dos oito novos foram conferidas após congelar código e antes de enviar análises. Rótulos pré-declarados em arquivo separado, SHA-256 `cb4305e7a122f6432c41c778ad864a02ce9d12da0dad4c5073ad73ea5e8383ef`; não entram no pipeline. Leituras humanas de referência não fornecem links, páginas ou rótulos à pesquisa da aplicação.

Tetos pré-declarados para a rodada inteira: Gemini 25, OpenRouter gratuito 2, Fact Check 20, busca 110, leituras públicas 200. Todos os detectores de mídia: zero. Sem recarga, contratação, plugins pagos ou rotação de modelo/chave. OpenRouter conservador começa em 46 e não pode ultrapassar 48; reservas antigas, inclusive a sem envio, permanecem. Nenhuma quota é expandida depois do congelamento.

Espera por requisição Gemini até 90 s, comparação compartilhada até 180 s dentro do orçamento textual existente. O teste local não altera configuração de produção nem comprova deploy.

## Resultado final — piora preservada

[Dados sanitizados completos](validation-research-gaps-2026-10-24.json), [oito textos novos e referências primárias](validation-new-text-controls-2026-10-24.json). Todos os vinte casos terminaram, uma tentativa cada, quatro submissões pelo formulário observadas e dezesseis por HTTP comum. Não são vinte testes visuais. O registrador confirmou vinte POST200; um OPTIONS200 adicional foi apenas preflight, não um caso de precisão.

| Grupo | Corretos | Inconclusivos | Conclusões erradas | Acerto com todos os casos |
| --- | ---: | ---: | ---: | ---: |
| Doze conhecidos | 6 | 6 | 0 | 50% |
| Oito novos | 0 | 8 | 0 | 0% |
| Mistura de desenvolvimento, não precisão geral | 6 | 14 | 0 | 30% |

Nenhum erro de execução HTTP foi observado. Falhas remotas dos modelos foram tratadas como cobertura insuficiente/inconclusiva, não como vereditos. A cobertura conclusiva dos conhecidos foi 50%; dizer “100% dos conclusivos estavam certos” esconderia metade das entradas e não substitui o acerto de 50%. Nos conhecidos, houve apoio correto a 1/6 afirmações verdadeiras e refutação correta de 5/6 falsas. Entre os novos, 0/4 verdadeiras e 0/4 falsas receberam conclusão correta.

Os 75% anteriores não se mantiveram. Copa passou a ser refutada por G1 e BBC, com regra tipada e duas famílias. OMS, Elizabeth II verdadeira, Webb, DART e Artemis ficaram sem cobertura documental suficiente; IBGE reuniu duas famílias, mas a comparação falhou nos dois provedores. Os resultados ruins não foram repetidos nem removidos. Pesquisa pública e respostas remotas variam, portanto esta única rodada não permite atribuir toda a piora à mudança de código; tampouco permite chamar esta revisão de ganho comprovado de precisão.

Treze dos quatorze inconclusivos ocorreram antes da comparação final. Regras conservadoras de identidade/relação e seleção de trechos ainda bloqueiam os novos temas, mesmo quando páginas são lidas. Em ECA/LDB, a identidade da norma e artigo não é reconhecida suficientemente no trecho selecionado; não foi promovida automaticamente a partir de um título. As contagens de rejeição são diagnósticos delimitados, não prova de que toda exclusão é correta.

### Transporte e modelos

Usadas 276 reservas: Fact Check20, busca108, leituras públicas126, Gemini20, OpenRouter2. Nenhuma chamada de mídia. Todos os tetos foram respeitados; OpenRouter conservador final48/48.

- Gemini: 17 HTTP200, dois503 e um transporte incompleto. O modelo configurado foi `gemini-3.1-flash-lite`; resposta200 não implica veredito factual correto.
- OpenRouter: uma resposta200 no planejamento, modelo observado `liquid/lfm-2.5-2.6b:free`; uma404 na comparação. Não foi homologado como comparador remoto nesta rodada. Corpo bruto de erro não foi preservado; não se pode afirmar que404 prove incompatibilidade de schema ou chave inválida.
- Fact Check e busca: todos os envios retornaram200. Busca sem checagem correspondente não comprova falsidade.
- Leituras públicas: 104 respostas200, oito redirecionamentos, quatro401, três403, uma404, uma504 e cinco transportes incompletos. Redirecionamento não é automaticamente falha final.

Mediana do tempo da análise: 20,002 s nos conhecidos; 34,038 s nos novos. Percentil95 por posto mais próximo: 33,457 s e55,696 s, respectivamente. A maior parte das abstenções não esgotou o prazo global; ampliar espera não resolve ausência de vínculo documental.

### Diagnóstico OMS

Na rodada anterior, a pesquisa recuperou o discurso formal de11/3 e o modelo validou o registro original. Nesta, cinco consultas retornaram páginas gerais, cronologias, PDFs e outros períodos, sem recuperar aquele discurso. Foram lidas seis páginas, com quatro falhas de leitura e zero timeout de leitura. A página geral WHO/Europe foi elegível, mas não constitui o mesmo registro formal nem duas fontes. O planejador selecionar PDF sem suporte de leitura também é um problema a tratar.

### Próxima melhoria deve atacar o mecanismo central

1. Recuperação orientada às capacidades reais do leitor: formatos suportados explícitos, preferência por corpos estáticos completos, referências primárias de períodos pertinentes. PDF só deve fornecer evidência após implementação de extração limitada, segura e com procedência por página; não basta aceitar seu endereço.
2. Vínculo genérico entre documento legal, artigo e texto da norma, preservando exceções, vigência, negações e escopo. Não cadastrar respostas ECA/LDB ou aceitar qualquer página oficial como verdadeira.
3. Comparação semântica com referências literais e todos os qualificadores, investigando falsos negativos do filtro antes da IA. Não substituir a barreira por opinião livre do modelo nem por concordância entre duas IAs.
4. Diagnóstico sanitizado da falha404 OpenRouter e validação de capacidade da rota gratuita, em nova janela de uso; sem retirar preço máximo zero, alternar chave ou reiniciar orçamento esgotado.
5. Avaliação separada em novos assuntos após cada mudança material, com acerto por classe, abstenção e erro visíveis. Os oito novos desta rodada agora também são conhecidos e não podem voltar a ser apresentados como holdout independente.

## Limites

Conjunto pequeno escolhido por julgamento, não amostra representativa nem avaliação geral cega. Recuperação pública pode variar entre rodadas, então mudança observada não prova ganho causal exclusivo do código. Mídias não são revalidadas nesta rodada; não há garantia de 80% nem de vereditos sempre corretos.
