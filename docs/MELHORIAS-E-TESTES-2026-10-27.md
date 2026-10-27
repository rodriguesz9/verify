# Melhorias, medição e limites — 27/10/2026

**Rodada real: 7/12 corretos (58,3%), cinco inconclusivos e nenhuma conclusão errada observada.** Foram doze submissões pelo formulário, com doze relatórios observados no navegador, e zero submissões pelo runner HTTP. Os doze POSTs retornaram 200. Sucesso HTTP não é acerto factual.

São os mesmos doze textos de desenvolvimento já conhecidos, não um teste cego ou uma amostra representativa. Inconclusivos e erros permanecem no denominador. O resultado melhorou em relação aos **5/12 (41,7%) de 25/10**, mas não demonstra 80% gerais, precisão de mídia nem funcionamento em produção.

## Revisão medida e verificações locais

A medição pertence ao código `a658ef0`, congelado antes dos envios, com SHA-256 `b67b886d23d793e48418ca013b75ad22cd961b1d5a4974373af9dc5c68bdda4d`. A compilação frontend, os doze textos, o instrumento e os limites também foram congelados. A conferência `verify_freeze` passou depois dos doze resultados terminais e antes da correção posterior de datas descrita abaixo.

Antes dessa correção posterior, **1.651 testes backend e 205 testes frontend passaram; o build frontend foi concluído**. Esses controles automatizados verificam mecanismos e regressões, não medem a precisão factual da aplicação. Não houve deploy nesta etapa.

A revisão medida incorpora o trabalho já documentado de separação entre cabeçalhos e corpo, vínculo literal de sigla à definição no corpo, contrato completo de comparação das fontes e diagnóstico de respostas das IAs. Uma falha técnica pode recorrer ao outro provedor dentro do mesmo prazo; um julgamento válido inconclusivo não recebe repetição até produzir uma conclusão. A pesquisa orientada por IA fornece consultas e referências limitadas, enquanto a decisão continua exigindo trechos, contexto e cobertura validados no servidor.

## Resultado dos doze controles

[Resultados, coberturas, hashes e contadores sanitizados](validation-quality-2026-10-27.json). Rótulos esperados e referências da fixture não foram passados à aplicação. Cada texto teve uma única tentativa.

| Controle conhecido | Esperado | Resultado em 27/10 | Resultado em 25/10 |
| --- | --- | --- | --- |
| OMS, classificação da pandemia | Verdadeira | Verdadeira no registro original | Verdadeira |
| Brasil campeão da Copa de 2014 | Falsa | Inconclusivo | Inconclusivo |
| Copernicus, temperatura abaixo da referência | Falsa | Inconclusivo | Inconclusivo |
| Copom, redução da Selic alegada | Falsa | Falsa no registro original | Falsa |
| Lei Áurea, negação do artigo 1º | Falsa | Falsa no registro original | Falsa |
| Webb, data do lançamento | Verdadeira | Verdadeira nas fontes | Inconclusivo |
| Artemis I, ano do lançamento | Falsa | Inconclusivo | Inconclusivo |
| Elizabeth II, data verdadeira | Verdadeira | Verdadeira nas fontes | Inconclusivo |
| PIB, divulgação do IBGE | Verdadeira | Verdadeira nas fontes | Verdadeira |
| Elizabeth II, data falsa | Falsa | Inconclusivo | Falsa |
| DART, impacto intencional | Verdadeira | Inconclusivo | Inconclusivo |
| Constituição, promulgação | Verdadeira | Verdadeira nas fontes | Inconclusivo |

Webb, Elizabeth II com a data verdadeira e Constituição ganharam conclusões corretas. Elizabeth II com a data falsa perdeu a refutação e ficou inconclusiva. Oito resultados não mudaram; saldo de dois acertos adicionais. Entre os seis textos esperados verdadeiros, houve 5/6 acertos; entre os seis falsos, 2/6. Não retirar os cinco inconclusivos para anunciar “100% dos conclusivos” como acerto geral.

A busca pública, os corpos disponíveis, a configuração e os modelos variaram entre as rodadas. Não houve teste A/B com a mesma recuperação congelada; o efeito causal de cada mudança de código não foi isolado.

### Por que cinco casos ficaram inconclusivos

Todos os cinco pararam **antes da comparação pelas IAs**, por falta de famílias com trechos elegíveis. Cada um utilizou dez tentativas cumulativas de leitura, incluindo falhas. Mais espera por uma resposta do modelo não resolveria esse bloqueio anterior.

| Caso | Famílias elegíveis | Causa observada |
| --- | ---: | --- |
| Copa de 2014 | 1 | Duas páginas G1 pertencem à mesma família. O hub GE e a retrospectiva EBC não dão a relação completa de campeão; a construção indireta do Brasil Escola não passou pelo vínculo esportivo delimitado. Cinco leituras ficaram bloqueadas ou indisponíveis. |
| Copernicus | 0 | O relatório original foi lido e contém “1.60°C warmer than”. O cabeçalho traz `10th January 2025`, mas a data estruturada da publicação ficou ausente. A relação completa entre relatório, data, referência e direção não passou pelas guardas. Seis leituras ficaram bloqueadas ou indisponíveis. |
| Artemis I | 1 | A página NASA da missão I dá 16 de novembro de 2022. Outras páginas recuperadas tratam de hub, outras missões, tentativas futuras ou não ligam missão e data integralmente no corpo. Duas leituras ficaram bloqueadas ou indisponíveis. |
| Elizabeth II, data falsa | 1 | G1 foi elegível. Outros corpos usam datas relativas ou indiretas e contextos com mais de uma pessoa; não chegou uma segunda família elegível à comparação. Seis leituras ficaram bloqueadas ou indisponíveis. |
| DART | 0 | A CNN explicita impacto intencional em setembro de 2022 sem o dia; o Guardian separa 26 de setembro do trecho explícito de intenção e Dimorphos; G1 e BBC não preservaram todos os vínculos exigidos nos trechos delimitados. Cinco leituras ficaram bloqueadas ou indisponíveis. |

Os contadores de rejeição no JSON representam janelas candidatas e direções de comparação, não números de fontes independentes nem uma revisão semântica exaustiva. `blocked_or_unavailable` pode incluir bloqueio local de segurança, além de indisponibilidade remota; não significa que toda tentativa recebeu erro HTTP do site.

### Evidência visual preservada

O histórico das ferramentas do operador registra as doze submissões e a observação dos relatórios. Os hashes dos doze JPEGs estão no JSON. O campo instrumental `ui_observation_required`, isoladamente, não comprova teste visual. As capturas abaixo exemplificam as duas formas de conclusão e não substituem o vínculo entre entrada, registro e observação do navegador.

![Constituição: verdadeira nas fontes consultadas](evidencias-2026-10-27/constituicao-verdadeira.jpg)

![Copom: falsa no registro original](evidencias-2026-10-27/copom-falsa.jpg)

## Respostas das IAs e consumo autorizado

Gemini usou `gemini-3.5-flash-lite`, com prazo geral de 90 s. A comparação usou OpenRouter primeiro, `openrouter/free`, preços máximos zero, até 120 s por provedor dentro de 240 s compartilhados. O modelo gratuito informado nas cinco comparações aceitas foi `nvidia/nemotron-3.5-super-vl:free`. Não houve rotação de chave ou modelo configurado, contratação, recarga ou uso de detector pago.

**OpenRouter respondeu cinco HTTP 200, com cinco comparações completas aceitas**, cobrindo todos os dez pares afirmação/documento esperados. **Gemini respondeu oito HTTP 200**, com planejamento de pesquisa aceito. Copom e Lei Áurea concluíram por regras tipadas locais, sem comparação por modelo. Nenhum dos cinco inconclusivos foi causado por resposta inválida ou indisponibilidade desses modelos nesta rodada. Responder corretamente ao contrato não é prova de conhecimento factual geral.

| Serviço | Reservas/envios contabilizados | Teto da janela | Transporte observado |
| --- | ---: | ---: | --- |
| Fact Check | 12 | 12 | 12 respostas 200 |
| Serper/notícias e busca web | 60 | 60 | 60 respostas 200 |
| Leituras públicas | 72 | 120 | 57 respostas 200, cinco 403, três 401, cinco redirecionamentos e dois transportes incompletos |
| Gemini | 8 | 16 | 8 respostas 200 |
| OpenRouter | 5 | 12 | 5 respostas 200 |
| AssemblyAI, Sightengine, HF e Hive | 0 | 0 | Não chamados |

A reserva conservadora OpenRouter era 53 antes desta autorização. Foram usadas cinco adicionais: **58 cumulativas, abaixo do teto autorizado de 65**. Falhas e envios ambíguos continuam cobrados. A janela não se renova por reinício, mudança de data ou existência de saldo não utilizado.

O teto Serper de 60 foi alcançado. A última consulta assistida da Constituição registra `error` com esse teto já atingido, compatível com bloqueio local; o registro da busca não preserva a exceção exata. Não há um envio remoto adicional no contador. A Constituição já reuniu três famílias elegíveis e concluiu corretamente. Essa limitação da avaliação permanece registrada, mesmo sem impedir a conclusão final.

A mediana foi **26,438 s**; o percentil 95 por posto mais próximo foi **40,220 s**. Nenhum caso se aproximou do prazo textual global de 420 s.

### Retomada sem replay

O servidor foi retomado depois que os primeiros nove casos já estavam concluídos. Esses nove registros foram preservados; somente os três casos ainda não reservados foram enviados depois. Não houve reenvio de caso iniciado nem reposição de orçamento.

Foi uma avaliação congelada em duas sessões de servidor. Os doze registros mantêm o mesmo hash de código e da fixture; as sequências de reserva de cada provedor são únicas, sem lacunas e começam em 1, preservando os totais acumulados. A conferência final do congelamento passou antes de qualquer correção posterior. O servidor da rodada foi encerrado ao concluir os doze controles.

## OCR sintético local, separado da checagem factual

Cinco controles sintéticos locais de OCR passaram: **impresso-base, afirmativo, números e datas tiveram texto exato; o controle sem texto retornou `no_text` corretamente**. Não são reconstruídos aqui textos de entrada, tempos ou datas que não foram fornecidos no registro desses controles.

Esse resultado verifica apenas a fidelidade de leitura nesses cinco exemplos. Não comprova autenticidade da imagem, precisão geral de OCR, qualidade das IAs de visão nem operação de detectores remotos. Imagens, áudios e vídeos reais não foram revalidados por esta rodada textual.

## Correção posterior à medição: data ordinal em inglês

Depois de concluir os doze casos e conferir o congelamento, foi implementada uma correção em `source_attribution.py` para reconhecer datas ordinais inglesas em ordem dia/mês e mês/dia, como `10th January 2025`, e marcar a linha como contexto. A abreviação `Sept.` é preservada em um único bloco de contexto, sem ser dividida em duas frases. A mudança **não infere `publication_date`** a partir dessa linha e não transforma cabeçalho em evidência factual.

Foram adicionados quatro controles automatizados; **1.655 testes backend passaram após a correção**. Os 1.651 testes anteriores pertencem à revisão medida; os 205 testes frontend e o build anteriores permanecem válidos para o frontend inalterado. A correção é posterior, não altera os doze resultados preservados e **não tem nova precisão factual real medida**.

Continuam abertas as lacunas de recuperação e de vínculo semântico mostradas pelos cinco inconclusivos. Não houve nova rodada, repetição até acerto, medição de mídia remota ou homologação de 80% após essa correção.
