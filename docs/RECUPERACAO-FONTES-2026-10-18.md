# Prioridade, referências tardias e tentativas de leitura — 18/10/2026

## Resultado e identificação

Continuação de [recuperação contextual](RECUPERACAO-CONTEXTUAL-2026-10-18.md), sobre a base `a76b691`. Primeiro checkpoint local `4b81a97`: 985 testes backend passaram e dois diagnósticos reais pela interface foram executados com o código congelado. Ambos ficaram inconclusivos. A revisão posterior corrige o orçamento de referências descobertas durante a pesquisa por IA, com validação offline, sem repetir os diagnósticos.

**Revisão final: 988 testes backend, zero falhas/skips, em 15,030 s; 22 arquivos de teste frontend e build passaram.** São 31 métodos backend novos sobre a base de 957, não 988 amostras de notícias. Cinco resultados conclusivos anteriores e suas nove citações literais foram preservados em replay offline. SQLite descartável/Docker sem rede; PostgreSQL e produção não foram revalidados.

Índice do código final: `2215f7f7e8f0e2b3feacb3fd867db468998680582525a7a75fb998942f4405fb`, inalterado no replay. Código dos dois diagnósticos reais: `4b81a97`, índice `131345dd6b6d360706332338383818b3eed1716f41e713d9f63d609c2003f326`. Não apresentar os diagnósticos como testes reais da revisão posterior.

A última rodada **completa de 12 textos** continua em 5/12 corretos (41,7%) e 7/12 inconclusivos. Os dois controles direcionados desta etapa não formam corpus independente, não substituem a rodada completa nem comprovam 80%. [Resumo sanitizado desta continuação](validation-discovery-2026-10-18.json).

## Quatro falhas corrigidas

### 1. Ranking calculado, mas parcialmente ignorado

O coletor usava a ordem de relevância para reservar uma página por família e voltava à ordem bruta da busca para preencher as outras vagas. Assim, outro texto do período correto podia perder a vaga para textos de anos distintos.

O preenchimento agora mantém a mesma ordem calculada. Tentativas anteriores e diversidade entre famílias continuam prioritárias. Duas páginas do mesmo grupo não viram duas confirmações; data ou título de uma busca não fornece evidência. Não foram alteradas as guardas de veracidade, anos conhecidos por caso ou URLs fixas de respostas.

Controles cobrem mesma família, ano/período, anual versus trimestre, diversidade, fonte submetida, falhas e teto cumulativo. Ranking por mês explícito e identificação de ano principal versus base de comparação ainda merecem estudo; não foram declarados resolvidos.

### 2. Referências de páginas descobertas depois da primeira leitura

Antes, uma referência real encontrada na segunda leitura era armazenada, mas não seguida. O helper também podia gastar seu limite com duas URLs já tentadas, ocultando uma terceira pista nova.

Agora URLs tentadas e destinos finais conhecidos são excluídos **antes** do limite de seleção. Quando a pesquisa por IA está habilitada e ainda faltam evidências, as referências de páginas descobertas depois podem ocupar os slots restantes. O helper considera somente documentos originados nas buscas; páginas seguidas por referência não se tornam pais de outra descoberta, inclusive após redirecionamento.

Limites preservados:

- Duas pistas primárias diretas totais por pedido, não duas por onda.
- Profundidade máxima um; sem crawler recursivo.
- Até seis tentativas/45 segundos no perfil sem pesquisa IA; dez/105 segundos com pesquisa IA.
- Mesmos limites de buscas, planejamento e três documentos na comparação final.
- Leitura real continua em `public_fetch`, com validação DNS/IP/TLS, redirecionamentos e limite de bytes.
- Fonte submetida, título, legenda e callout permanecem sem voto de veracidade.

Resolver a lacuna com corpos recuperados evita chamar o planejador e executar pesquisas adicionais. Não surgem novas chamadas de IA somente para seguir um link existente.

### 3. Tentativas desapareciam no cancelamento de um lote

O cache era atualizado apenas após todo o lote terminar. Se um pedido lento provocasse cancelamento, uma resposta rápida podia desaparecer junto e as tentativas já iniciadas ficavam fora da contagem.

Cada URL agora ocupa sua reserva antes do envio; cada resposta é registrada assim que termina. Cancelamento encerra e aguarda as tarefas irmãs antes de propagar. URLs interrompidas continuam debitadas como falhas genéricas, sem afirmar um HTTP timeout que não foi observado, reembolsar ou reenviar automaticamente.

No timeout do pipeline, a cobertura informa as reservas cumulativas e a onda incompleta; somente coletas concluídas entram no relatório. Um corpo concluído isoladamente continua no cache, mas não é promovido silenciosamente a evidência após um lote interrompido. Teste integrado cancela a onda tardia real: oito reservas preservadas e nenhuma conclusão acrescentada.

### 4. Metadado explícito de publicação era ignorado

O leitor passa a reconhecer `parsely-pub-date` no `head`, documentado como data de publicação pela [Parse.ly](https://docs.parse.ly/installation-resources/parsely-integration/metadata/metatags/). Usa o mesmo parser, preserva o dia civil declarado e rejeita valores inválidos, futuros ou conflitantes. Não dá precedência ao novo campo nem aceita atualização/criação como publicação.

Reprocessamento dos dois HTMLs NASA capturados anteriormente recuperou datas de publicação antes ausentes. DART continuou com uma família elegível: publicação não empresta dia ou ano ausente à data de impacto, nem torna uma legenda corpo probatório.

## Diagnósticos reais, sem simulação de respostas

Foram enviados uma vez, sequencialmente, dois controles públicos já usados no desenvolvimento. Ambiente local, banco descartável, allowlist de credenciais de provedores; não importou banco, cookies ou segredos de produção. Frontend real → `/api/check-text` → provedores/busca/leitura reais → relatório real. Dois HTTP 200 e `Cache-Control: no-store`; HTTP 200 não é acerto factual.

| Controle | Resultado | Leitura/cobertura observada |
| --- | --- | --- |
| Webb — data de lançamento | Inconclusivo | Dez tentativas; sete leituras concluídas e três falhas; somente UOL elegível para comparação. Nenhuma pista direta selecionada antes de esgotar as leituras. |
| DART — impacto intencional/data | Inconclusivo | Dez tentativas; oito leituras concluídas e duas falhas. Duas referências reais foram seguidas pela nova onda tardia; somente CNN passou pela seleção factual. |

“Corpo lido” não significa evidência completa. Faltaram trechos elegíveis de duas famílias, por isso a comparação factual por IA não foi iniciada. Não atribuir a abstenção a um erro dessa chamada: ela ficou `not_requested`, não timeout.

OpenRouter respondeu à extração com variantes gratuitas; Gemini 3.8 respondeu ao planejamento com duas consultas válidas em cada caso. Google Fact Check respondeu sem checagens correspondentes. A pesquisa web retornou pistas, mas notícia relacionada e título não foram promovidos a prova. Isso valida estes papéis textuais, não visão, OCR, transcrição, detectores ou precisão geral dos modelos.

Diário cumulativo exclusivo desta rodada: OpenRouter 2, Gemini 2, Google Fact Check 2, Serper 12 e transportes de leitura pública 20. Serper inclui a busca de notícias de contexto e as buscas web, não doze chamadas de comparação factual. Hive: **zero imagens, zero segundos, zero trabalhos**. Não houve nova contratação, recarga, rotação de chave ou contorno de quota/bloqueios.

### Ajuste posterior ao diagnóstico Webb

O diagnóstico mostrou que uma página portadora da referência pode chegar somente na pesquisa final, quando as dez leituras já foram gastas. O checkpoint `4b81a97` ainda tinha essa limitação.

A revisão final reserva os slots diretos restantes antes de esgotar a última leitura: oito páginas mais até duas referências, ou nove mais uma. Se não houver link útil, os slots voltam à fila existente, sem nova busca ou modelo. Se já houver cobertura suficiente, não são gastos. As duas pistas totais, profundidade um, dez tentativas e prazo único permanecem inalterados.

Três controles offline adicionais verificam referência descoberta nessa última etapa, liberação da reserva quando não há links e interrupção de leituras extras quando os corpos já bastam. **Não houve novo envio real de Webb ou DART depois desse ajuste**, nem alegação de que ele sozinho tornou os vereditos conclusivos.

## Pendências concretas

1. Repetir o manifesto textual completo uma vez com a revisão final congelada e as APIs disponíveis. Não repetir apenas até obter conclusões ou somar versões diferentes como um benchmark único.
2. Melhorar recuperação de corpos com identidade, intenção, evento e data completa; metadados/publicação não substituem esses elementos. Fontes BCB dependentes de JavaScript continuam sem corpo estático utilizável.
3. Estudar ranking por mês e período principal versus base de comparação, sem inserir respostas corretas conhecidas nas consultas.
4. Corpus novo e independente, incluindo afirmações falsas e casos fora dos exemplos de desenvolvimento. A meta de 80% permanece não comprovada.
5. Voz humana/vídeos reais autorizados, desempenho dos detectores e salvamento/abertura do PDF pela interface continuam pendentes; não foram revalidados nesta etapa.

Nenhuma variável privada nova é necessária. Não houve push/deploy ou acesso ao banco de produção. O servidor e a aba temporários foram encerrados; não copiar o harness, HTMLs brutos ou capacidades de exportação para o repositório/produção.
