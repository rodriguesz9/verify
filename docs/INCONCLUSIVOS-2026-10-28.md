# Inconclusivos: recuperação e leitura contextual — 28/10/2026

**Registro da etapa anterior à nova rodada real.** A medição posterior de 28/10 terminou em **5/12 acertos (41,7%)**; consultar [resultado completo e reparos seguintes](MEDICAO-E-CORRECOES-2026-10-28.md). Os valores e limites abaixo descrevem a etapa offline que precedeu essa execução.

Esta revisão corrige caminhos de descoberta e comparação local. **Ainda não demonstra aumento da precisão real:** a última rodada completa continua com **7/12 acertos (58,3%), cinco inconclusivos e nenhuma conclusão errada observada**, conforme o [registro de 27/10](MELHORIAS-E-TESTES-2026-10-27.md). Os doze controles já são conhecidos e não constituem avaliação independente.

## Causa encontrada

Os cinco inconclusivos daquela rodada pararam **antes da comparação das fontes pelas IAs**. Gemini respondeu às oito chamadas de planejamento; OpenRouter respondeu às cinco comparações solicitadas, todas HTTP 200. Nenhuma dessas cinco comparações corresponde aos cinco casos que ficaram sem evidência utilizável suficiente.

As dez tentativas de leitura de cada caso inconclusivo já tinham terminado. Aumentar o prazo não recupera um texto bloqueado por HTTP 401/403, uma data ausente ou uma segunda fonte independente. O trabalho desta etapa se concentra nesses obstáculos, mantendo os prazos existentes.

| Controle conhecido | Obstáculo encontrado nas páginas capturadas | Próxima recuperação necessária |
| --- | --- | --- |
| Artemis | Uma família elegível; previsões e página geral competiam com relato do lançamento concluído. Uma página de vídeo contém link explícito ao artigo textual original. | Ler relatos concluídos e o artigo explicitamente referenciado, sem contar dois textos da BBC como duas famílias. |
| Copernicus | A expressão “warmer than” não era reconhecida como direção numérica. A definição literal do período de referência e a medição aparecem em frases separadas. | Vincular definição e medida somente com prova contextual delimitada; obter outra fonte utilizável. |
| Rainha, data falsa | Uma família elegível. BBC usa dia da semana sem dia numérico; outros textos separam identidade, morte e data. | Buscar relato que ligue a data completa ao falecimento. A publicação sozinha não fornece a data do fato. |
| Copa | G1 fornece uma relação completa; Brasil Escola intercala outra edição antes da declaração do campeão. | Recuperar outro relato completo da mesma edição. Páginas do mesmo grupo continuam uma família. |
| DART | Os textos distribuem identidade, intenção e data por trechos sem vínculo completo. Há também finalidade sobre possíveis riscos futuros ao lado de impacto já concluído. | Separar o alcance da finalidade e buscar relato com os demais fatos explicitamente ligados. |

## Correções nesta revisão

### Ordem de descoberta de lançamentos

Para uma afirmação que identifica uma missão numerada e uma data, relatos de lançamento concluído ganham prioridade sobre página geral, preparativos e previsão. Um ano falso na entrada não favorece a previsão daquele ano sobre o relato do evento concluído em outro ano.

A identidade da missão permanece antes da fase do evento na ordenação, inclusive com nomes curtos. Perguntas, lançamentos negados, previsões e misturas de missões não viram relatos concluídos. Formatos que o leitor não aceita continuam depois dos documentos legíveis. Isso muda a ordem de leitura; título e endereço não geram voto factual.

### Referência explícita de mídia para artigo

Um aviso como “Este vídeo foi publicado em [endereço]” pode fornecer um caminho de leitura para o artigo textual do mesmo grupo editorial. A regra exige aviso delimitado, uma única âncora, endereço visível consistente, título visível único e destino público legível. Links de navegação, publicidade, conteúdo oculto, outro grupo, pesquisa, login e páginas de mídia não recebem essa permissão.

O título serve somente para descobrir o assunto do destino. O artigo ainda precisa ser recuperado e passar pelas mesmas verificações de corpo. O caminho usa o limite compartilhado de duas referências e de dez tentativas de leitura; referências já seguidas não iniciam uma cadeia de navegação. A página de vídeo e seu artigo continuam pertencendo à mesma família editorial.

### Comparações numéricas

O leitor reconhece “warmer/colder/higher/lower than”, além de “above/below/acima/abaixo”, mantendo valor, unidade, direção e período de referência ligados à mesma medida. A referência da próxima medida não completa a anterior.

Sinais, incerteza numérica, limites, aproximações e extremos de intervalo não são convertidos silenciosamente em valores positivos exatos. Uma comparação precisa de uma quantidade interpretável; `−1,60`, `±1,60`, `até 1,60` e `1,20 a 1,60` não equivalem ao escalar positivo `1,60`.

### Evento concluído e finalidade futura

Uma finalidade delimitada sobre desviar objetos que poderiam ameaçar a Terra não torna automaticamente incerto um impacto já afirmado como concluído. O prefixo precisa passar sozinho pelas mesmas verificações de sujeito, ação, data, quantidade, negação e contexto. A citação integral permanece disponível para a comparação pelo modelo.

A exceção não completa data ou identidade ausente. Hipótese sobre a própria ocorrência, ficção, planejamento, correção e instruções continuam bloqueados. Condições introduzidas por “se/caso/if/unless”, inclusive no meio ou no final da frase, não viram afirmações categóricas. Uma condição encerrada em outro período não governa indefinidamente o fato seguinte.

## Validação e limites

**1.707 testes backend passaram, sem falhas ou testes ignorados:** 52 controles novos desde `4f63f87`. A revisão inclui casos adversos de hipótese, negação, sujeito, data, unidade, sinal, intervalo, aproximação, referência editorial, limites e recursão. A suíte do frontend não foi repetida nesta etapa, que não alterou seus arquivos; os 205 testes e build da etapa anterior continuam históricos. [Resumo sanitizado e hashes](validation-inconclusive-offline-2026-10-28.json).

Foram usados testes locais sintéticos e uma reprodução da seleção com os corpos públicos já capturados. Nenhuma chave foi lida por essa reprodução; nenhum provedor, buscador ou página pública foi chamado. Os limites encerrados da rodada anterior não foram reiniciados.

A reprodução compara o código de referência `4f63f87` com esta revisão, usando os mesmos documentos e HTML. **Ela não descobre páginas novas, não executa os modelos e não calcula nova precisão factual.** A ordenação e o seguimento de referências precisam de nova rodada real para medir seu efeito na recuperação.

Há uma lacuna conhecida nessa reprodução: o registro estruturado oficial do Copom usado na rodada real não está representado pelo conjunto de corpos HTML. Seu controle fica sem família nesse recorte, embora tenha sido corretamente refutado na execução completa. Não se interpreta essa diferença como regressão nem se fabrica o registro ausente.

Os cinco casos ainda não ganham famílias elegíveis apenas com os corpos atualmente salvos. As correções tratam erros demonstráveis; não autorizam transformar falta de evidência em “verdadeiro” ou “falso”. A meta de 80% e a revalidação de autenticidade de imagem, voz e vídeo continuam pendentes.

A descoberta mudou em uma página capturada: a versão anterior não selecionava a referência da BBC de vídeo para artigo; a nova versão seleciona `https://www.bbc.com/portuguese/internacional-63647280` a partir do aviso literal em `https://www.bbc.com/portuguese/media-63647283`. Esse artigo não foi buscado nesta etapa. Portanto, há recuperação do caminho de leitura demonstrada, sem novo fato ou veredito inferido do destino.

## Próximas etapas

1. Medir a descoberta após as mudanças, com código congelado, uma tentativa por controle e contagem explícita de chamadas.
2. Separar fonte inacessível, falta de família independente e vínculo textual incompleto no diagnóstico de cada inconclusivo.
3. Projetar vínculo auditável de definições locais de medidas, preservando contexto completo, definição única e rejeição de conflitos.
4. Avaliar novos controles ainda não usados no desenvolvimento; reportar separadamente acertos, erros conclusivos, inconclusivos e falhas de execução.
5. Revalidar mídia sob autorização e saldo próprios. Não somar controles textuais e de mídia para anunciar uma precisão geral.

Ambiente revisado reiniciado com o mesmo banco e volumes: aplicação local em `http://127.0.0.1:5176`, backend em `http://127.0.0.1:8016`. `/health` e `/ready` retornaram HTTP 200, banco pronto; `/`, `/app` e `/login` entregaram o documento com HTTP 200. A tela de checagem foi observada no navegador, sem submeter análise. Os hashes dos cinco arquivos de implementação no contêiner coincidem com os testados. Railway permanece fora desta validação; envio ao GitHub não comprova deploy.
