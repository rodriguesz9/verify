# Verificações inconclusivas — diagnóstico e correções de 10/10/2026

## 1. Reclamação e versão examinada

Foram relatados resultados inconclusivos em notícias, link educacional, foto publicada, imagem gerada por IA, voz robótica e vídeo. Os conteúdos exatos e os relatórios desses casos não foram fornecidos. Não é possível atribuir os registros do servidor a uma pessoa específica nem medir acertos nesses exemplos sem os arquivos.

No início desta rodada, `git fetch origin` confirmou HEAD/remoto `4332d7ccf4bcc991dc1840bdfbb52e80267fb88b`, sem commits novos. Railway servia a implantação `62d892f0-51ab-46ad-bbb9-3f9c2760ff22` (SUCCESS) e Vercel `dpl_FmSVsJ7QFYxjL23pp7Dzh178669M` (READY), ambas nesse SHA. O checkout original estava modificado e foi preservado; a revisão foi feita no checkout de entrega.

Os logs de 09/10 entre 17:55 e 18:45 em Brasília mostram respostas 200 de texto/upload, além de rejeições 400/422 de links. HTTP 200 não informa se o resultado foi conclusivo, nem se corresponde ao teste relatado. Não foram copiados telefones, chaves, cookies, tokens assinados ou conteúdo privado para este registro.

## 2. Reprodução anterior à correção

Pela interface pública, foi enviada uma frase curta sobre Elizabeth II, data e local de falecimento. OpenRouter e Serper responderam; Google Fact Check respondeu sem checagens. Resultado: inconclusivo, com notícias relacionadas apresentadas como contexto. Neste controle, a causa não foi indisponibilidade de Gemini/Railway: o texto não tinha duas avaliações editoriais válidas da mesma afirmação literal.

Uma notícia histórica correta pode nunca ter sido objeto de um ClaimReview. Wikipedia, Brasil Escola ou uma referência oficial não se tornam avaliações editoriais apenas por aparecer na busca. A política anterior confundia, na apresentação, ausência de checagem publicada com outros motivos de abstenção.

## 3. Correções de recuperação textual

- A seleção anterior priorizava texto completo e os primeiros fragmentos; títulos, autoria e chamadas podiam consumir os cinco lugares antes de uma frase selecionada pela extração.
- `build_fact_check_queries` prioriza frases literais selecionadas pela extração e reserva a entrada integral quando houver pelo menos duas vagas. Pistas inventadas/paráfrases não viram afirmações verificadas.
- Uma pista parcial seleciona a frase envolvente completa: não retira “não”, valores, datas ou qualificadores. Pista repetida em contextos diferentes preserva os contextos.
- Dr., Dra., Sr., Sra., Prof. e Profa. não separam título e nome na segmentação. Números/datas permanecem literais.
- `provider_coverage.google_fact_check.query_plan` registra limite, métodos, consultas selecionadas/omitidas e presença da entrada integral, sem repetir o conteúdo do usuário no audit. Consulta planejada não é afirmação confirmada; ausência de consulta separada não implica ausência da frase na busca integral.
- A política textual passa a `2026-10-10.1` pela mudança de segmentação; famílias editoriais, ratings, duas fontes distintas e comparação exata conservadora continuam iguais.

## 4. Referências gerais sem inventar confirmação

Uma busca web Serper adicional procura páginas candidatas. Até três páginas, incluindo a submetida quando houver, são lidas com o mecanismo existente de DNS/IP público validado, TLS, redirects e tamanho/tempo limitados. Sem nova API, chave ou contratação.

O campo `source_attribution` declara `decision_role=source_attribution_only`. Um match exige a frase completa no corpo efetivamente recuperado, com igualdade normalizada conservadora. Snippet, título de busca, descrição, ocultação explícita reconhecida pelo extrator e preâmbulo negativo não substituem a frase da fonte. O extrator estático não resolve integralmente visibilidade por CSS de classes/folhas externas ou JavaScript; a referência é atribuição no corpo recuperado, não prova de visibilidade no navegador nem verdade. Preservam-se URL final, trecho, frase comparada, papel da fonte e horário UTC de leitura.

Limites: uma busca extra por análise; consulta literal de 20–500 caracteres sem corte silencioso; três páginas de até 2 MiB, três redirects/8 s cada; etapa inteira de até 20 s; oito frases candidatas, até três matches; HTML estático de até 50 mil caracteres por página. O fragmento no ponto de corte não pode produzir match. Consome quota da conta Serper existente; não adiciona crédito/cartão. Falha de leitura e serviço ausente são observáveis. `coverage.max_source_bytes` registra o teto usado.

Na interface, **“Trecho localizado em uma fonte”** significa somente que a página publica aquele trecho. Não significa verdade, autoria, endosso, fonte independente ou certificação de artigo inteiro. Uma página enviada não pode confirmar a si mesma de maneira independente. Verdade/refutação, afirmações mistas e conflitos editoriais preservam prioridade sobre esse diagnóstico.

Correspondência literal limita recall: sinônimos, formatação, paráfrases e páginas comprimidas/protegidas/JavaScript podem ficar sem match. Uma ampliação semântica futura exige relação verificável que preserve sujeito, negação, valores e datas; similaridade ou concordância de LLM não são suficientes.

## 5. Mídia: mostrar o sinal, não criar certeza

O campo aditivo `media_signal.version=1` distingue:

| Estado | Interpretação pública |
| --- | --- |
| `consensus_ai` | Indícios de geração por IA em consultas independentes elegíveis |
| `consensus_manipulation` | Indícios de possível manipulação |
| `isolated_ai` | Sinal de possível IA/voz sintética; confirmação pendente |
| `isolated_manipulation` | Sinal de possível alteração; confirmação pendente |
| `disagreement` | Detectores em desacordo |
| `no_high_signal` | Sem indícios fortes nas consultas feitas; não prova autenticidade |
| `unavailable` | Nenhuma observação utilizável da origem; não prova falsidade |

O diagnóstico exige resposta explicitamente bem-sucedida, disponibilidade verdadeira, score válido e camada elegível. Hive imagem/facial conta uma família, não dois votos; HF experimental não conta. Resultados armazenados, índices, campos de confiança e limiares não foram alterados. `POLICY_VERSION` da decisão de mídia permanece `2026-10-03.2`.

No perfil atual, só o Hive está habilitado como detector acústico. Um sinal alto isolado agora aparece claramente como **possível voz sintética**, sem certificar voz humana, identidade ou clonagem. Não se ativou Sightengine voz restrito/enterprise, nem um endpoint pago HF para fabricar consenso.

Vídeo usa diagnósticos por quadro/tempo, não médias de fornecedores em tempos diferentes. A amostra visual e `audio_analysis.media_signal` são independentes; uma voz sintética não torna a imagem um deepfake. Resumo, explicação e mensagem de compartilhamento inconclusivos também diferenciam essas situações. OCR/transcrição leem conteúdo; não autenticam a origem da mídia.

## 6. Interface e exportação

- Cabeçalhos distintos para sinais isolados, divergência, ausência de sinal forte e indisponibilidade; índice principal permanece “Não determinado” quando não há medição adequada.
- Texto/link não exibem um card irrelevante de origem de mídia.
- Fontes com trecho literal e plano de busca separados das checagens factuais.
- Nomes de provedores, variáveis e scores brutos continuam nos detalhes fechados; avisos públicos usam linguagem simples.
- Áudio/vídeo preservam conferência humana da leitura e os estados pendentes de transcrição, sem reenvio automático.
- O snapshot assinado preserva novos campos. O PDF já reutiliza resumo original; o layout de exportação ainda não tem uma seção própria para todos os novos cards de atribuição/diagnóstico. Não declarar equivalência visual total sem implementar e ensaiar essa parte.

## 7. Regressão local e fronteiras da validação

Suíte offline final após os ajustes de tamanho e orçamento de saída OpenRouter: **554 testes backend**, 10,462 s, zero falhas/skips/tentativas HTTP inesperadas, contêiner sem rede/credenciais e SQLite descartável. **169 testes frontend**, zero falhas/skips; build Vite concluído com 1.977 módulos na revisão `8aca4c7`, sem mudança posterior no frontend nestes ajustes. Estes são testes de contrato/regra/fluxo, não 723 casos independentes de precisão de detector.

A revisão cruzada corrigiu mais três pontos: uma resposta exclusivamente facial não pode sugerir que a geração por IA foi consultada; um sinal acústico não certifica toda a gravação; o diagnóstico de origem não deve apagar o aviso financeiro do resumo/compartilhamento. Os três ganharam controles de regressão.

Novos controles incluem negação/data divergente, snippet sem corpo, conteúdo oculto, limites de fontes, erro de busca, prefixos de pessoa, pista parcial, Hive isolado, conflito, scores inválidos, quadros em tempos distintos e separação de faixa de áudio. A primeira execução encontrou duas diferenças de redação em assertions novas; a execução final passou após ajuste textual, sem mudança decisória.

### Publicação confirmada e primeiro controle real

As correções principais foram publicadas em `8aca4c754c31832e6a7c87d5d46e7b5fe8ecf630`. A [CI da candidata](https://github.com/rodriguesz9/verify/actions/runs/38084709246) e a [CI de master](https://github.com/rodriguesz9/verify/actions/runs/38084871274) concluíram com sucesso. Railway confirmou SUCCESS na implantação `ff91031a-abd3-4777-b150-59b04eeb2a7f`; Vercel confirmou READY em `dpl_DErTcB8SCsGw486YpCFeqjB9C9vC`, ambas nesse SHA. São verificações de publicação, não evidências de precisão factual.

O primeiro controle dessa versão pela interface, em 10/10 às 20:45 UTC, usou uma frase literal de um artigo público sobre Elizabeth II. Gemini `gemini-3.1-flash-lite` respondeu. A resposta OpenRouter veio truncada, foi descartada e não virou evidência; Gemini foi o fallback. Google Fact Check respondeu sem ClaimReviews. A busca de referências respondeu, mas duas das três páginas selecionadas excederam o teto inicial de 512 KiB: a interface mostrou ausência de correspondência, não confirmou falsidade.

Esse resultado motivou o ajuste para 2 MiB, alinhado à leitura de links já existente, sem relaxar proteção de rede ou comparação literal. Dois controles adicionais asseguram aceitação de uma página válida acima de 1 MiB e rejeição acima de 2 MiB. Publicado em `09e1a0853e6b237d9b04254309d5cd5c32c3455c`, com [CI candidata](https://github.com/rodriguesz9/verify/actions/runs/38085372131) e [CI master](https://github.com/rodriguesz9/verify/actions/runs/38085526030) aprovadas. Railway SUCCESS em `dbd28f86-8786-45d9-bfcf-5d6d4e8fbcfb` e Vercel READY em `dpl_Fb4Mh1HZvZ4AUKxuqr7HdoWY6Q3F`, ambos nesse SHA.

Às 20:56:19 UTC, o [artigo Brasil Escola de controle](https://brasilescola.uol.com.br/historia/elizabeth-ii.htm) foi submetido como link pela interface, nessa revisão. Leitura da página concluída; três de três referências selecionadas recuperadas, sem falhas/oversize, teto observado 2.097.152 bytes. Foram exibidas três correspondências literais na própria fonte submetida, não três fontes independentes. Resultado público: “Trecho localizado em uma fonte”; canonical `Suspicious/inconclusive`, sem voto de verdade. O texto do artigo foi limitado aos primeiros 5.000 caracteres, declarado na tela; uma referência tinha o corpo normalizado acima de 50 mil caracteres, também registrado. Gemini respondeu como fallback de OpenRouter truncado; Fact Check respondeu sem checagens; notícias relacionadas foram mostradas somente como contexto. Esse controle valida leitura e atribuição, não o artigo inteiro nem o link exato do colega, que não foi recebido.

### Controles de mídia pela interface publicada

Nenhum destes arquivos é a entrada exata do colega. Foram controles públicos/sintéticos previamente documentados e autorizados; uma execução por arquivo, sem repetir para obter rótulo desejado. As quatro respostas chegaram à tela de resultado (no áudio, passando primeiro pela conferência de transcrição).

| Controle e horário UTC em 10/10 | Respostas observadas | Resultado e alcance |
| --- | --- | --- |
| `demo-conversa-sintetica.wav`, 20:50:39 | AssemblyAI `universal-2`: transcrição igual à fala de controle; Hive v3: sinal acústico 0,9741; Sightengine voz desabilitado | `isolated_ai`: “Sinal de possível voz sintética”. Canonical `Suspicious/inconclusive`; um detector não confirma identidade, clonagem ou toda a faixa. |
| NASA `nasa-zinnia-iss046e009018.jpg`, 20:52:43 | Hive e Sightengine válidos, sem sinal alto; Gemini `gemini-3.1-flash-lite`: OCR e inspeção visual responderam | `no_high_signal`: “Sem indícios fortes nas consultas feitas”. Não certifica foto autêntica. OCR devolveu “A”, curto e insuficiente; nenhuma afirmação foi checada a partir dessa letra. |
| `ai-plant-windowsill.png`, 20:54:04 | Hive v3 e Sightengine com sinal alto concordante de IA; Gemini inspeção visual respondeu e OCR `no_text` | `consensus_ai`, canonical `AI_Generated/partial`: “Indícios de geração por IA”. Origem sintética conhecida do controle, sem generalizar a outros geradores. |
| `synthetic-cafe.mp4`, 20:54:54 | Hive e Sightengine responderam nos três quadros; concordância de IA no mesmo quadro em 0,3 s, 1,5 s e 2,7 s; arquivo sem áudio | `consensus_ai`, canonical `AI_Generated/partial`: “Indícios de IA em quadros amostrados”. Sequência de uma imagem sintética, não ensaio de face swap, lipsync ou vídeo gerado temporalmente. |

Voz, NASA e planta foram processadas na implantação `8aca4c7`; o vídeo após a publicação `09e1a08`, que não alterou detecção de mídia. HF permaneceu desabilitado; nenhuma assinatura/recarga foi criada. Os sinais numéricos acima são saídas brutas não calibradas, não probabilidades comprovadas de falsidade.

### Mitigação adicional do OpenRouter gratuito

A extração de pistas literais tinha um teto de saída de 768 tokens. Foi ampliado para 2.048, dentro do teto global existente, sem retry extra, modelo pago ou alteração do prazo de 25 s. Permanecem `openrouter/free`, filtro de preço zero e descarte de respostas `finish_reason=length`, mesmo que um trecho pareça JSON válido. Gemini continua como fallback; essas pistas não votam na verdade.

A [documentação oficial](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens#reasoning-tokens-and-max_tokens) explica que raciocínio e saída final podem compartilhar esse orçamento. O [router gratuito](https://openrouter.ai/docs/guides/routing/routers/free-router) escolhe modelos disponíveis conforme capacidades. O mecanismo é uma causa plausível da truncagem, não uma causa confirmada daquele pedido sem seus dados de uso/modelo. Mais orçamento reduz a restrição; não garante resposta de todo modelo nem elimina limites externos. O novo controle offline inspeciona o pedido completo e conserva preço zero, chamada única, prazo e papel auxiliar.

### Retomada e controle textual de 11/10

Em 11/10, `git fetch origin` confirmou `333fbfdad3967a87f00c9da08d1251d564761880` em HEAD, branch de entrega e master, sem commits externos novos desde a publicação. As [validações da candidata](https://github.com/rodriguesz9/verify/actions/runs/38085732950) e de [master](https://github.com/rodriguesz9/verify/actions/runs/38085895724) passaram. A inspeção confirmou Railway SUCCESS em `1b6f10cc-68ff-4cb6-babd-26cd5de09b5b` e Vercel READY em `dpl_7Px3FoL4CQrCSS9JnDEbLYeun3vM`, ambos nesse SHA. O checkout original modificado continua preservado.

Às 12:40:26 UTC (09:40:26 em Brasília), o mesmo controle literal curto sobre falecimento/data/local foi enviado pela interface nessa revisão. OpenRouter respondeu com `liquid/lfm-2.5-2.6b:free`, `status=success` e papel `search_hints_only`; Gemini não foi necessário como fallback nessa execução. Não se pode atribuir causalmente esse sucesso apenas ao aumento de tokens: o router escolheu um modelo gratuito disponível, diferente de uma seleção anterior não registrada.

Google Fact Check respondeu sem checagens. Serper retornou contexto, com seis de dez candidatos excluídos pelo filtro lexical. A busca de referências respondeu, selecionou três de cinco páginas; duas foram recuperadas sem correspondência literal, e uma excedeu o teto de 2 MiB. A tela mostrou “Sem correspondência nas fontes consultadas”, índice “Não determinado” e canonical `Suspicious/inconclusive`. Não houve confirmação nem refutação factual. O controle comprova resposta operacional, extração auxiliar e abstenção explicada; **não comprova que o problema de conclusão factual dos textos do colega esteja resolvido**. Recuperação semântica verificável, maior corpus e entradas exatas continuam pendentes; não ampliar indefinidamente o teto de leitura ou relaxar evidências só para obter uma conclusão.

## 8. Pendências reais para a entrega

1. Receber entradas exatas e relatórios do colega. Reproduzir uma vez e comparar falhas de API, orçamento, oposição de detectores e ausência de indícios; não ajustar limiares para um exemplo famoso.
2. Voz/vídeos humanos autorizados, além dos controles sintéticos. A caixa local `arquivos-para-validacao/` permanece disponível; nenhum arquivo é enviado automaticamente.
3. Matriz independente de detecção com falsos positivos, falsos negativos, abstenções e cobertura, por modalidade. Foto publicada não é certificado de pixels; texto robótico não basta para comprovar clonagem.
4. Fluxo autenticado real de conta/histórico/PDF, exportação salva/aberta, viewport mobile efetivamente aplicado e ensaio com pessoas leigas.
5. Limites financeiros compartilhados entre processos/réplicas: reservas Hive atuais reiniciam no deploy e não limitam custo global. Manter valores autorizados, sem reset deliberado ou recarga para obter o rótulo desejado.
6. Retenção/exclusão, backup-restauração e gates adicionais do [fechamento até 11/10](ENTREGA-ATE-11-OUTUBRO.md) antes de lançamento irrestrito.

Não há promessa de vereditos 100% certeiros. O ganho desta revisão é recuperação literal mais útil e uma explicação que diferencia observações reais, limitações de política e falhas de serviço.
