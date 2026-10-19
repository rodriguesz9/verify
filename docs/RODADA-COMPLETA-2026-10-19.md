# Rodada textual completa — continuação de 18–19/10/2026

## Resultado e limites

**Rodada encerrada: 4/12 corretos (33,3%), 8/12 inconclusivos (66,7%), nenhuma conclusão errada e nenhum erro terminal do pipeline. A meta de 80% não foi atingida.** Houve falhas de fornecedores; ausência de erro terminal não significa que todas as APIs responderam sem problemas. Este documento separa resultados recebidos, observação da interface e testes automatizados. Não declara precisão de imagem, áudio ou vídeo. [Resumo sanitizado por controle](validation-full-text-2026-10-19.json).

A retomada em 19/10 preservou as duas análises iniciadas em 18/10, o código congelado, os registros e o orçamento cumulativo da mesma rodada. As contagens não foram reiniciadas para obter mais chamadas ou um resultado melhor. A rodada textual completa anterior teve **5/12 corretos (41,7%) e 7/12 inconclusivos**, descrita em [qualidade da checagem](QUALIDADE-CHECAGEM-2026-10-17.md). A diferença observada foi de **−8,3 pontos percentuais**. Não somar resultados históricos aos desta rodada nem atribuir a diferença somente ao ajuste de ranking: recuperação web, disponibilidade e respostas dos modelos também podem variar.

## Revisão em avaliação

Base: [recuperação de fontes de 18/10](RECUPERACAO-FONTES-2026-10-18.md), seguida de ajuste genérico na prioridade de leitura por mês/ano explícitos. Candidatos do período solicitado vêm antes dos de período desconhecido e dos explicitamente diferentes, quando a alegação permite identificar um período sem ambiguidade.

O ajuste atua somente na ordem de descoberta. Não transforma data de URL, título ou resultado de busca em evidência, não descarta automaticamente outros períodos e não altera a alegação. Casos ambíguos não recebem mês/ano inventados. Nove controles offline adicionais cobrem datas em português/inglês, caminhos numéricos, ambiguidades, data de divulgação distinta do evento e ausência de filtragem factual pela prioridade.

Índice exato do código, registrado no manifesto técnico da rodada: `513e4adb3d9f61d897db245931ade208127406307c923b34e174a47f8c75ea33`, preservado entre o primeiro e o último envio deste conjunto. Política factual `2026-10-18.1`. Perfil usado: Gemini `gemini-3.8-flash` como comparação primária, OpenRouter `openrouter/free` como alternativa gratuita e prazo de chamada configurado em 60 segundos. Correções posteriores exigem outra identificação de versão e não podem substituir silenciosamente os resultados abaixo.

## Protocolo e limites

- Mesmo manifesto predefinido de doze textos públicos: [`text-quality-2026-10-17.json`](../backend/tests/fixtures/validation/text-quality-2026-10-17.json).
- SHA-256 do manifesto: `47397f9ffa4022db414d2b85614efd70bdbfe3db4510b221d3d67bcb16625e04`.
- Seis afirmações esperadas como sustentadas e seis como refutadas; oito controles históricos e quatro adicionais. São exemplos usados no desenvolvimento, **não um corpus independente, cego ou representativo**.
- Um envio por controle nesta rodada, sem repetir até obter o resultado desejado. O fato de o navegador não exibir uma resposta já concluída não autoriza reenviar a análise como se fosse nova amostra.
- Ambiente local, banco descartável e credenciais selecionadas de provedores. Não importa banco, sessões ou autenticação de produção. Registros públicos e sanitizados devem manter separadas as fronteiras navegador → API → fornecedores → relatório.
- OpenRouter restrito a modelos gratuitos. Hive desabilitado nesta rodada: **zero imagens, zero segundos de áudio e zero trabalhos**. Nenhuma chamada paga habilitada para este conjunto.
- Preservados os tetos de transporte e o diário cumulativo da rodada. Resposta de erro, bloqueio ou quota deve aparecer como falha/cobertura, nunca como evidência de falsidade ou sucesso do fornecedor.

Notícia relacionada, título, snippet, data de publicação e concordância entre modelos não substituem trechos probatórios com contexto. Manter essas guardas pode produzir abstenções; removê-las para atingir uma meta produziria uma medição enganosa.

### Fronteiras realmente exercitadas

Os nove primeiros controles foram submetidos pelo formulário real da aplicação local. Há registro de nove análises concluídas pelo backend. **Somente seis relatórios foram efetivamente observados na interface:** Elizabeth II com data correta, DART, OMS, IBGE, Copom e Copernicus.

Os resultados de Elizabeth II com data falsa, Lei nº 3.353 e James Webb foram recebidos/capturados no backend, mas seus relatórios não foram observados na tela. A primeira aba foi encerrada antes dessa observação; depois, duas chamadas de controle do navegador excederam 300 segundos cada. Esse timeout da ferramenta não é prova de timeout da aplicação nem de falha dos fornecedores: as respostas já concluídas foram preservadas, sem reenviar os controles.

Constituição, Copa de 2014 e Artemis I foram concluídos por pedidos HTTP locais ordinários ao mesmo endpoint, com o mesmo pipeline, código congelado e diário cumulativo. Isso exercita API → fornecedores → relatório, **não** o formulário ou a renderização desses três casos. Há doze análises factuais encerradas, mas não doze testes completos pela interface.

O observador de fronteiras HTTP foi reinicializado no reinício do harness e sobrescreveu suas duas primeiras entradas. Restaram dez eventos HTTP 200 com `Cache-Control: no-store` nesse arquivo. O diário persistente de orçamento dos fornecedores e os doze relatórios por controle foram preservados. Não afirmar que o observador contém doze eventos ou que os dez HTTP 200 demonstram acerto factual. Essa limitação de instrumentação não foi corrigida no meio da amostra congelada.

## Resultados por controle

Todos os controles têm resposta final capturada. `unverified` é resultado inconclusivo. `supported` e `refuted` são comparados literalmente ao esperado; resultado HTTP e renderização da tela não substituem essa comparação.

| Controle | Esperado | Resultado factual recebido | Observação da interface |
| --- | --- | --- | --- |
| Elizabeth II — 8/9/2022 | Sustentado | Inconclusivo (`unverified`) | Relatório observado em 18/10 |
| Elizabeth II — 9/9/2022 | Refutado | Refutado (`refuted`) | API concluiu em 18/10; aba encerrada antes da observação do relatório |
| DART — impacto intencional em 26/9/2022 | Sustentado | Inconclusivo (`unverified`) | Relatório observado em 19/10 |
| OMS — pandemia em 11/3/2020 | Sustentado | Inconclusivo (`unverified`) | Relatório observado em 19/10 |
| IBGE — PIB de 2024, divulgação de 7/3/2025 | Sustentado | Sustentado (`supported`) | Relatório observado em 19/10 |
| Copom — redução em 18/9/2024 | Refutado | Inconclusivo (`unverified`) | Relatório observado em 19/10 |
| Copernicus — 2024 abaixo da referência histórica | Refutado | Inconclusivo (`unverified`) | Relatório observado em 19/10 |
| Lei nº 3.353 — negação do artigo 1º | Refutado | Refutado (`refuted`) | Submissão pela interface e resposta API concluída; relatório não observado na tela |
| James Webb — lançamento em 25/12/2021 | Sustentado | Sustentado (`supported`) | Submissão pela interface e resposta API concluída; relatório não observado na tela |
| Constituição — promulgação em 5/10/1988 | Sustentado | Inconclusivo (`unverified`) | HTTP local concluído em 50,578 s; interface não validada |
| Brasil — campeão masculino de 2014 | Refutado | Inconclusivo (`unverified`) | HTTP local concluído em 75,960 s; interface não validada |
| Artemis I — lançamento em 16/11/2021 | Refutado | Inconclusivo (`unverified`) | HTTP local concluído em 56,484 s; interface não validada |

## Porcentagens finais

A porcentagem principal usa `acertos exatos ÷ 12 × 100`. **Inconclusivos e erros permanecem no denominador.**

| Métrica | Contagem | Percentual |
| --- | --- | --- |
| Acertos exatos, incluindo inconclusivos no denominador | 4/12 | 33,3% |
| Inconclusivos | 8/12 | 66,7% |
| Conclusões erradas observadas | 0/12 | 0% |
| Erros terminais do pipeline | 0/12 | 0% |
| Cobertura conclusiva | 4/12 | 33,3% |
| Acertos nas afirmações verdadeiras | 2/6 | 33,3% |
| Acertos nas afirmações falsas | 2/6 | 33,3% |

As quatro conclusões estavam corretas: **4/4, ou 100% entre respostas conclusivas**. Esse denominador exclui oito abstenções; **não é 100% de acerto global** nem garantia de ausência de falsos vereditos em notícias novas. Amostras pequenas e conhecidas pelo desenvolvimento não demonstram a meta de 80% na população de notícias.

Tempo mediano de execução capturado no pipeline: **42,691 s**, com intervalo de 22,447 a 85,118 s. Não inclui toda a fronteira HTTP nem mede tempo até renderização no navegador, não é meta de latência de produção e não inclui os timeouts posteriores da ferramenta de controle da interface.

Não calcular porcentagens novas de imagem, voz ou vídeo a partir desta rodada textual, de testes unitários ou de chamadas antigas a detectores.

## O que melhorou e o que ainda falhou

Em relação aos mesmos controles da rodada completa anterior, **IBGE e Webb passaram de inconclusivos para sustentados**. Elizabeth II com a data correta, OMS e Copernicus passaram de conclusivos corretos para inconclusivos. Elizabeth II com a data falsa e a negação da Lei nº 3.353 permaneceram refutadas. Os quatro demais controles continuaram inconclusivos. Assim, os dois ganhos não compensaram as três perdas; não há melhora global demonstrada por esta rodada.

A revisão dos registros separou dois problemas, sem alterar nem reenviar os controles:

- **Comparação incompleta:** em Elizabeth II com data correta, OMS e Constituição, a comparação assistida omitiu avaliações necessárias. Chamada recebida com sucesso não significa que todas as citações tenham sido avaliadas. As omissões não foram preenchidas por suposição nem por voto de outro modelo.
- **Recuperação insuficiente:** DART, Copom, Copa de 2014 e Artemis I ainda não reuniram corpos elegíveis com as relações/qualificadores exigidos. Buscar páginas relacionadas ou receber snippets não bastou para formar evidência utilizável.

No controle do Copernicus, o modelo produziu uma relação de sustentação incompatível com a diferença literal entre **“acima” e “abaixo”**. A guarda rejeitou essa avaliação; o resultado ficou inconclusivo em vez de aprovar a alegação falsa. Esse bloqueio funcionou como proteção, mas não recuperou a refutação correta que se deseja entregar.

Houve também resposta Gemini HTTP 503 e uso de alternativa OpenRouter gratuita. O fallback que responde não garante completude ou correção de suas avaliações. **Zero erros terminais do pipeline não equivale a zero erros de fornecedores**; o relatório pode ser entregue normalmente com cobertura degradada.

### Transporte efetivamente registrado

| Serviço | Reservas cumulativas | Resultado de transporte |
| --- | --- | --- |
| Gemini | 16 | 4 HTTP 200, 9 HTTP 503, 3 incompletas |
| OpenRouter gratuito | 24 | 24 HTTP 200 |
| Google Fact Check | 12 | 12 HTTP 200 |
| Busca Serper | 55 | 55 HTTP 200 |
| Páginas públicas | 87 | 68 HTTP 200, 11 redirecionamentos, 6 HTTP 403, 2 incompletas |
| Hive | 0 | Nenhum envio |

Não houve HTTP 429 registrado. Uma reserva incompleta não identifica por si só um status HTTP. OpenRouter respondeu ao transporte, mas o planejamento de Artemis retornou conteúdo inválido; no clima, retornou a relação errada. Portanto, **24 HTTP 200 não significam 24 avaliações corretas**. As chamadas e falhas contam nos tetos; os contadores persistiram na retomada.

## Testes automatizados — checkpoint separado

Checkpoint local de 18/10: **997 testes backend, zero falhas/skips, em 16,070 s; 22 arquivos de teste frontend e build passaram.** Os nove testes de prioridade mensal estão incluídos nos 997, não são nove notícias adicionais.

Após encerrar a rodada, o observador HTTP do harness foi corrigido: reabre histórico válido, recusa arquivo inválido antes de ler credenciais, grava atomicamente e reserva a vaga antes de iniciar a análise. O limite de 256 entradas inclui pedidos pendentes; não trunca registros para caber outra chamada. Nove novos testes cobrem retomada, dados privados/inesperados, limites, concorrência e falha de escrita. **Suíte final: 1.006 testes backend, zero falhas/skips, em 15,433 s.** Essa correção de instrumentação não altera `backend/app`, o fingerprint factual avaliado nem as porcentagens. Também não recupera as duas entradas já perdidas; não houve nova chamada real após a correção.

Esse checkpoint valida contratos e comportamentos cobertos no ambiente de teste. Não mede precisão factual dos doze textos, não valida PostgreSQL de produção e não prova que Vercel ou Railway estejam executando esta revisão. Teste passando também não comprova que todas as APIs estejam disponíveis ou que um PDF tenha sido salvo pelo navegador.

## Próximos passos prioritários

1. **Validar completude da comparação:** identificar e registrar pares de afirmação/citação não avaliados; não confundir ausência de avaliação com falta de evidência. Uma correção deve ter testes de omissão, duplicação, IDs inválidos e limite de prazo, sem fabricar votos ou aceitar concordância entre modelos como prova.
2. **Tratar falhas e quotas gratuitas explicitamente:** diferenciar HTTP 503, quota, timeout, JSON inválido e comparação incompleta. Usar alternativa somente dentro dos limites e do prazo; não rotacionar chaves, contratar serviço ou repetir controles até conseguir uma resposta desejada.
3. **Melhorar os corpos realmente recuperados:** manter vínculos literais de evento/data, direção de taxa, edição/categoria/vencedor e ano completo. Não substituir texto do corpo por título, legenda ou data de publicação. Preservar guardas de polaridade como “acima/abaixo”.
4. **Revalidar a interface quando a conexão voltar:** o observador HTTP já foi corrigido e testado offline fora da amostra encerrada. Ainda falta observar os relatórios não renderizados e exercitar os três controles feitos somente por HTTP, numa rodada separada e identificada. Não criar outro envio nesta rodada já concluída nem contabilizar captura do backend como renderização confirmada.
5. **Criar corpus independente e balanceado:** novas afirmações verdadeiras/falsas de temas variados, anotadas antes dos envios, com fontes públicas verificáveis. Congelar outra versão e publicar todos os resultados, incluindo inconclusivos e falhas. Somente isso começa a testar generalização além dos exemplos de desenvolvimento.

Diagnósticos e correções posteriores não serão adicionados a esta mesma amostra como novas tentativas bem-sucedidas. Vozes/vídeos próprios autorizados e nova validação de mídias continuam necessários. **Projeto não homologado, meta de 80% não atingida e nenhuma garantia de vereditos 100% corretos.** Testes locais não comprovam publicação ou configuração atual de Vercel/Railway.
