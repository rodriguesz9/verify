# Continuação de 23/10: recuperação, modelos e mídia

Esta revisão melhora falhas identificadas, sem substituir evidência por opinião de IA. Não promete 80% de precisão geral nem resultados sempre conclusivos. A rodada anterior de 22/10 continua preservada em [causas centrais](CAUSA-CENTRAL-2026-10-22.md).

## Publicação solicitada primeiro

Antes das novas alterações, o commit já testado `142c4d0` foi enviado com sucesso à branch `entrega/banca-2026-10-08` de `rodriguesz9/verify`. Isso não representa mesclagem na `master` nem confirma implantação no Railway/Vercel.

## Correções desta continuação

| Ponto | Causa confirmada | Mudança e limites |
| --- | --- | --- |
| Recuperação interrompida após timeout | Um timeout de consulta impedia pesquisas diferentes, referências já descobertas e planejamento posterior, mesmo restando prazo e leituras | Timeout permanece registrado; somente consultas diferentes já previstas podem continuar. Os mesmos limites de cinco buscas/dez leituras/105 s permanecem. Quota, configuração, credencial e erro não classificado continuam interrompendo a pesquisa |
| Fontes internacionais mal priorizadas | A consulta primária traduzida usava locale português; títulos ingleses não compartilhavam palavras com a alegação portuguesa | Perfil inglês aplicado à consulta primária internacional explicitamente reconhecida; ranking usa apenas aliases linguísticos existentes. Nomes desconhecidos e numerados são preservados; slugs são delimitados, não uma palavra única |
| Alternativo configurado sem tempo útil | Um transporte travado podia consumir o prazo inteiro do cliente antes do modelo alternativo explícito | Duas tentativas explicitamente configuradas dividem o mesmo prazo restante. Falha rápida libera o tempo não gasto. Sem alternativo configurado, a tentativa conserva o prazo inteiro. Nenhum novo modelo ou chave foi configurado |
| Resultado experimental mascarava detector válido | A seleção da cabeça facial dedicada do Hive ocorria antes de avaliar sua elegibilidade | Elegibilidade verificada antes de escolher cabeça dedicada/base. Hive continua uma família, não dois votos. Resultados experimentais continuam disponíveis para inspeção, sem decidir o veredito |
| Escopo temporal de áudio perdido | Conversão v3 descartava `time`/`end_time`; coordenadas só eram limitadas a 120 s, não à duração validada do arquivo | Preservação de intervalos e score local de cada observação, com duração validada no caminho de requisição. Coordenadas impossíveis são omitidas, não recortadas ou ampliadas. Sem tempos, não se inventa cobertura integral |
| Raiz editorial utilitária | Um único cartão de contato marcado como artigo era escolhido em vez da prosa principal | Fallback estrutural estreito reconhece cartão utilitário e bloco principal único; contexto, títulos e qualificadores permanecem. Coleções de notícias e estruturas ambíguas não entram nesse fallback |
| Ficção em português não reconhecida | Rótulos como “exemplo hipotético” e “texto fictício” não eram abrangidos pelas guardas existentes | Veto de contexto explicitamente não factual antes das comparações tipadas/oficiais e do caminho genérico. Rótulo anterior/no trecho ou declaração posterior explícita sobre este texto/evento; outro cenário hipotético e “não é hipotético” não invalidam registro real. Não transformar desmentido fictício em refutação real |
| Apresentação de sinais sem percentual | O título informava um sinal útil, mas o quadro adjacente repetia “Não determinado” | Relatórios com sinais versionados convidam a ler “Veja os sinais e os limites”; não mostram índice legado como probabilidade nem mudam o resultado armazenado |

Um resultado válido que diz “insuficiente” não provoca procura de outro modelo para obter resposta desejada. Resposta incompleta/inválida, cancelamento externo, quota e erros de autenticação/permissão/pagamento não autorizam rotação de modelos no cliente. Tentativas de transporte continuam contabilizadas, mesmo com erro ou cancelamento.

As datas, valores, negações e qualificadores da entrada original continuam intactos nas etapas de decisão. Títulos, snippets, idioma da busca e dados de publicação isolados não se tornam votos factuais. Em DART, a falta de um corpo que vincule missão, alvo, intencionalidade e data completa não é corrigida removendo uma dessas exigências.

## Verificação automatizada

- Suíte final: 1.397 testes backend passaram, sem rede, sem `.env`, zero skips e zero transportes HTTP inesperados.
- 22 arquivos de testes frontend passaram; build concluído.
- A medição textual usou SHA-256 `d47bc65a1a8ccd4346f735652f5048aeb8cb2a5a77fcf345bd233bec254f364c`. Mídias e diagnóstico OpenRouter usaram `677c555256541416797111f2e7b01b04542546d4ebb833f2135019b188e7b4af`, após corrigir a raiz editorial. Ambos abrangem 128 arquivos de `backend/app` e `frontend/src`. Guardas de ficção e rótulo público são posteriores, sem herdar uma taxa de precisão medida.
- Código final dos testes offline e build: SHA-256 `4945e00d5e36bcc8053f3e4f1ce3e46d31b8dc7fc2b41b33bf3d5bc6a3884684`, 128 arquivos. Política factual `2026-10-23.2`; política de mídia `2026-10-23.1`. Não confundir com as duas versões medidas acima.
- Os testes de resiliência simulam primário travado, falha rápida, prazo total, cancelamento e erros terminais. Não são uma medição da disponibilidade real dos fornecedores.
- Os controles de mídia verificam seleção de heads elegíveis, família única, flags experimentais e tempos inválidos/ausentes/fora da duração. Não medem precisão estatística de deepfake.

## Nova rodada real

Plano congelado antes de iniciar provedores: os mesmos doze controles textuais conhecidos, uma tentativa por entrada, sem rótulos ou referências esperadas enviados ao pipeline. Limites: Gemini 30, OpenRouter 6, Fact Check 20, busca 70 e páginas públicas 120; mídia desabilitada nessa rodada textual. As 42 reservas conservadoras anteriores OpenRouter foram preservadas; máximo cumulativo 48, sem reiniciar diários na mudança de data.

Uma submissão falsa de Elizabeth II foi feita pelo formulário: carregamento, relatório final e screenshot observados. O resultado identificou a data falsa e exibiu as citações G1/BBC, com vínculo explícito das expressões relativas ao calendário. Os onze controles restantes são HTTP comum, não onze testes visuais.

Resultado: **6/12 corretos (50%), seis inconclusivos, zero conclusões erradas observadas e zero erros de execução**. Todos os doze registros e entradas corresponderam ao congelamento. Os inconclusivos continuam no denominador. [Dados sanitizados](validation-resilience-2026-10-23.json).

| Controle | Resultado |
| --- | --- |
| Elizabeth II, data verdadeira | Inconclusivo; somente uma família elegível |
| Elizabeth II, data falsa | Refutada corretamente; duas famílias, observado na UI |
| DART | Inconclusivo; nenhum trecho elegível reúne todos os detalhes |
| OMS | Inconclusivo; nenhum documento elegível após leitura/guardas |
| IBGE | Confirmado corretamente |
| Copom, afirmação falsa | Refutada corretamente |
| Copernicus, afirmação falsa | Refutada corretamente |
| Artigo legal, afirmação falsa | Refutada corretamente |
| Webb | Inconclusivo; somente uma família elegível |
| Constituição | Confirmada corretamente |
| Copa, afirmação falsa | Inconclusivo; nenhum documento elegível nesta recuperação |
| Artemis, afirmação falsa | Inconclusivo; somente uma família elegível |

Foram 166 reservas: Gemini 13 (todas HTTP 200), Fact Check 12 (todas 200), busca 66 (todas 200), páginas 75 (61×200, cinco redirecionamentos, quatro 401, três 403, dois incompletos). OpenRouter não foi solicitado; não ficou indisponível. Nesta rodada a comparação não começou nos seis inconclusivos por falta de famílias, não por timeout dos modelos. Os limites foram respeitados e o acumulado conservador OpenRouter permaneceu em 42.

Frente aos 7/12 anteriores, ganhou a data falsa de Elizabeth e perdeu a verdadeira e Webb. O resultado menor não foi apagado nem substituído por um replay. A nova raiz de artigo descrita abaixo é posterior e não está medida nesses 50%.

## Falha do leitor encontrada após a rodada

Uma página WHO/Europe continha prosa com o fato, mas o seletor escolheu o único elemento `<article>` — um cartão lateral “Media contacts”. Os parágrafos verdadeiros ficaram fora da raiz, classificados como contexto. O novo fallback exige cartão de contato explícito, único landmark principal e único bloco substancial de prosa. Não apaga navegação, títulos ou qualificadores, nem junta cartões de notícias.

Na releitura offline da mesma captura, passou de uma sentença BODY do cartão para doze sentenças BODY de prosa. Isso **não resolveu sozinho o veredito OMS**: a sentença conservou duas datas e uma referência indireta ao evento; as guardas ainda não aceitaram uma família elegível. Não remover a data de janeiro nem completar o vínculo por conhecimento do modelo. Onze testes estruturais cobrem essa mudança. A revisão adversarial posterior encontrou os rótulos de ficção em português não abrangidos; a nova guarda também protege o caminho tipado e os registros oficiais.

## Diagnóstico real do OpenRouter gratuito

O OpenRouter **respondeu HTTP 200 em 13,527 s**, mas sua matriz revisou apenas um dos dois pares afirmação/fonte exigidos. O resultado permanece `invalid_response`/`insufficient`, sem evidências aceitas. Portanto, a chave permitiu a chamada; o problema observado foi a resposta incompleta, não falta de tempo ou indisponibilidade de transporte. [Registro sanitizado](validation-openrouter-2026-10-23.json).

Foi uma chamada `openrouter/free`, preço máximo zero, sem alternativo e com Gemini/rede de outros fornecedores bloqueados. As duas páginas já capturadas foram reprocessadas offline para preservar publicação e procedência; a pré-validação exigiu duas famílias antes de ler a chave. Isso testa comparação de corpos capturados, **não recuperação ponta a ponta nem nova precisão**.

Um diagnóstico anterior desta continuação fez zero envios porque o registrador havia omitido metadados de publicação; ele permanece preservado como falha de preparação de QA, não erro do fornecedor. Sua reserva não foi devolvida. Acumulado conservador: 42 anteriores + uma reserva sem envio + uma chamada nesta preparação corrigida = 44, abaixo do teto 48. Sem zerar contadores, trocar chave ou repetir resposta incompleta.

## Mídia e limitações de conclusão

O corpus disponível contém fotos NASA com procedência editorial, imagens geradas documentadas, síntese convencional eSpeak e vídeos derivados de stills. Não há voz humana autorizada, face-swap/lip-sync independente nem conjunto representativo de câmeras, geradores e compressões. Portanto, mesmo chamadas reais bem-sucedidas não autorizam publicar uma taxa geral de acerto para voz/vídeo.

Ausência de sinal de geração por IA não comprova foto/voz/vídeo autêntico. OCR lê texto; transcrição lê fala. Nenhum dos dois certifica origem ou veracidade. A inspeção Gemini também não substitui prova de captura. Os sinais de áudio do Hive são máximos de observações, não probabilidade de que toda a gravação seja sintética; [documentação do formato temporal](https://docs.thehive.ai/reference/ai-generated-audio-detection-1).

### Quatro controles pela interface local

Uma submissão de cada arquivo, em sequência, versão congelada, relatórios finais observados no navegador. [Dados sanitizados e hashes](validation-media-2026-10-23.json).

| Controle | Resposta observada | Limite da interpretação |
| --- | --- | --- |
| Foto NASA de planta | Hive e Sightengine responderam, sem sinal forte | Não comprova autenticidade nem gera um acerto de classificação “real” |
| Planta gerada por IA | Sinais concordantes: Sightengine 0,99 e Hive 0,9999999188; título “Indícios de geração por IA” | São scores não calibrados; Gemini auxiliar retornou 503 nessa imagem, sem impedir o resultado dos detectores |
| Voz sintética, cinco segundos | Hive 0,990826918; AssemblyAI transcreveu; interface indicou possível voz sintética | Um detector acústico, sem confirmação independente ou controle de voz humana; não confirma clonagem/identidade. Trecho “pixu da gente” exige revisão, não transcrição perfeita |
| Vídeo sintético derivado de imagem, três segundos | Sightengine sinalizou IA nos três quadros: 0,3 / 1,5 / 2,7 s; arquivo corretamente identificado sem áudio | Hive desativado para vídeo nesta autorização; sem consenso entre fornecedores, inspeção temporal integral ou teste de lip-sync |

Transporte: Sightengine 5/5 HTTP 200; Hive 3/3 HTTP 200; Gemini 3×200 + 1×503; AssemblyAI cinco envios HTTP 200, incluindo um upload, um job e três consultas. Não são dezessete análises independentes nem uma taxa de acerto. Nenhuma nova consulta textual ocorreu a partir da transcrição: ficou aguardando conferência.

Autorização nova de 23/10: até US$ 0,03 do saldo Hive, duas imagens e um áudio de no máximo cinco segundos, sem recarga/contratação. Foram reservadas exatamente essas três chamadas; vídeo bloqueado, nenhuma repetição. Pelos preços consultados, custo nominal calculado US$ 0,02588889; não é fatura ou confirmação do saldo real. O limite desta rodada está consumido, não reutilizável. Backend temporário encerrado depois dos quatro resultados.

O rótulo público foi alterado depois desses controles e passou nos testes de renderização/build. A reconferência visual após a mudança ficou pendente: o navegador recusou conexão ao reabrir a interface local. Isso não invalida os quatro relatórios já observados e preservados, mas não comprova o layout final do novo rótulo.

Nenhuma nova contratação, recarga ou mudança em segredos foi feita. Nenhuma implantação desta revisão foi confirmada.

## Próxima prioridade para elevar acertos

1. Recuperar e ler fontes adicionais utilizáveis para os seis inconclusivos, sobretudo EBC/Elizabeth, Webb, DART e OMS. Busca respondendo 200 não significa que o texto necessário foi encontrado.
2. Resolver vínculos explícitos de evento/data por evidência local, preservando eventos distintos, qualificadores e datas múltiplas. Sem tabelas de respostas para os exemplos conhecidos.
3. Melhorar cumprimento da matriz completa pelos modelos, sem aceitar célula omitida como acordo ou repetir até obter a resposta desejada. O erro OpenRouter acima permanece um caso negativo documentado.
4. Congelar a próxima versão e testar casos novos previamente separados. Nos doze conhecidos, 80% exige ao menos dez acertos; alcançar isso nesses exemplos não prova generalização.
5. Completar corpus autorizado de voz humana e vídeos reais/sintéticos independentes. Os quatro controles atuais não permitem uma porcentagem geral de precisão por modalidade.
