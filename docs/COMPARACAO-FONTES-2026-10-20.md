# Comparação completa das fontes — 20/10/2026

## Resultado real, sem excluir inconclusivos

**5/12 acertos (41,7%), 7/12 inconclusivos (58,3%), nenhuma conclusão errada observada. A meta de 80% não foi atingida.** São os mesmos doze controles públicos de desenvolvimento, não uma avaliação cega ou representativa. [Dados sanitizados](validation-source-review-2026-10-20.json).

A rodada anterior terminou com 4/12 acertos. Houve ganho líquido de um caso, mas também regressões: Elizabeth com data falsa, IBGE e Webb perderam cobertura nesta descoberta. Não selecionar apenas ganhos nem apresentar 5/5 conclusões corretas como 100% global. Uma amostra tão pequena não garante ausência de falsos vereditos.

## O que mudou antes desta medição

- A comparação agora exige que o modelo examine **cada afirmação contra cada documento selecionado**, declarando evidência ou insuficiência explicitamente. Uma resposta que omite documentos não passa como comparação completa.
- IDs de fonte e de trecho continuam pertencendo ao servidor. Citações inventadas, referências trocadas, pares duplicados e omissões são rejeitados. Até três fontes; nenhum voto novo por concordância entre IAs.
- Resposta completa dizendo que faltam evidências não dispara outra tentativa para procurar uma opinião mais favorável. Falhas de transporte podem usar a alternativa dentro do mesmo prazo total de 60 segundos e no máximo dois fornecedores.
- Relatório, histórico, PDF e WhatsApp usam “Verificada como verdadeira nas fontes consultadas” ou “Verificada como falsa nas fontes consultadas”, em lugar de “corroborada”. Chaves internas permanecem compatíveis. A frase atribui a conclusão às fontes, não certifica verdade universal.
- Busca de lançamento passou a priorizar a missão numerada correta, antes do ano alegado, e a procurar também relatos editoriais em inglês. Abreviações de horário seguidas de zona e data não dividem indevidamente a frase literal.
- Leitura esportiva aceita uma construção delimitada de relato no presente histórico, mantendo vencedor, competição, edição, adversário e complemento explícitos. Não consulta tabela de campeões nem descarta qualificadores desconhecidos.

Protocolo de comparação: `claim_source_review_v2`; envelope externo preservado como `source_corroboration_v1`. Política factual `2026-10-18.1` inalterada. “Revisão completa” mede cobertura do protocolo, não acerto semântico garantido.

## Método congelado

Manifesto: `backend/tests/fixtures/validation/text-quality-2026-10-17.json`, SHA-256 `47397f9ffa4022db414d2b85614efd70bdbfe3db4510b221d3d67bcb16625e04`. Seis afirmações verdadeiras e seis falsas. Um envio ordinário por caso, sem inserir rótulos esperados ou URLs de referência no pedido. Todas as doze análises encerradas; nenhum erro terminal do pipeline.

Identificação do código avaliado: `401bd58d21619c80ac46848dc2401749be326629ef7d4898c41b07d9d69b27d7`, calculada sobre arquivos da aplicação e verificada antes de cada caso. A correção esportiva posterior descrita abaixo **não pertence a esse código medido**.

Gemini primário e multimodal configurados como `gemini-3.1-flash-lite`, sem rotação automática de modelos. OpenRouter restrito a `openrouter/free`. Pesquisa existente habilitada; sem contratar APIs, usar grounding pago, trocar chaves após quota ou realizar chamadas Hive. O perfil Lite foi configurado somente no ambiente descartável: esta revisão não altera silenciosamente o modelo padrão do deploy. A mudança de modelo e a variabilidade web impedem atribuir a diferença de acerto apenas ao novo protocolo.

Limites fixos da rodada: Gemini 36, OpenRouter 16, Fact Check 24, busca 72 e leituras públicas 180 envios de transporte. Reservas/falhas contam; diário persistente não reiniciado. Uma sondagem sintética Lite anterior confirmou o formato estruturado, mas não entra na precisão dos doze controles.

## Casos e diagnóstico

| Controle | Resultado | Acerto | Falha restante quando inconclusivo |
| --- | --- | --- | --- |
| Elizabeth II — data correta | Verdadeira nas fontes | Sim | — |
| Elizabeth II — data falsa | Inconclusivo | Não | Apenas uma família documental utilizável |
| DART — impacto intencional | Inconclusivo | Não | Cobertura incompleta do evento e data nos corpos lidos |
| OMS — declaração de pandemia | Verdadeira nas fontes | Sim | — |
| IBGE — PIB de 2024 | Inconclusivo | Não | Uma família utilizável; outros períodos ocuparam leituras |
| Copom — redução alegada | Inconclusivo | Não | Páginas sem corpo utilizável; páginas oficiais dependentes de JavaScript |
| Copernicus — abaixo da referência | Falsa nas fontes | Sim | — |
| Lei nº 3.353 — negação do artigo | Falsa nas fontes | Sim | — |
| James Webb — lançamento | Inconclusivo | Não | Uma família utilizável, descoberta insuficiente da segunda |
| Constituição — promulgação | Verdadeira nas fontes | Sim | — |
| Brasil — campeão de 2014 | Inconclusivo | Não | Uma família; páginas de moedas comemorativas desperdiçaram leituras |
| Artemis I — data falsa | Inconclusivo | Não | Uma família; outros corpos não ligaram missão e data de forma utilizável |

Nos cinco casos comparados, Gemini completou todos os pares exigidos pelo protocolo. Nos sete inconclusivos a comparação nem foi solicitada, por falta de corpos elegíveis suficientes. A principal barreira observada nesta rodada passou a ser **recuperação e correspondência documental**, não a quantidade de IAs instaladas.

Acertos nos verdadeiros: 3/6 (50%). Nos falsos: 2/6 (33,3%). Mediana capturada no pipeline: 44,841 s; mínimo 21,215 s, máximo 100,335 s. A execução teve uma grande pausa de relógio entre casos; não representa sessão contínua nem latência de produção. Não alterar timestamps para escondê-la.

## Fronteiras verificadas e falhas de fornecedores

Os doze casos foram submetidos por **HTTP local ao endpoint real**, não pelo formulário do navegador. O observador preservou doze respostas 200 JSON com `Cache-Control: no-store`. Isso confirma respostas recebidas, não doze vereditos corretos nem doze testes pela interface.

Na interface houve login, histórico e abertura do relatório real de Elizabeth com data correta. O novo título foi observado em largura móvel de 360 px, com quebra de linha sem transbordamento visual; captura local `true-label-mobile.jpg`. Não houve novas submissões de análise pela interface nesta rodada. Não extrapolar essa observação para todas as telas ou leitores assistivos.

Transportes efetivos:

| Serviço | Envios | Estados observados |
| --- | --- | --- |
| Gemini | 17 | 14 HTTP 200, 1 HTTP 503, 2 incompletos |
| OpenRouter gratuito | 14 | 9 HTTP 200, 1 HTTP 404, 4 incompletos |
| Google Fact Check | 12 | 12 HTTP 200 |
| Busca existente | 60 | 60 HTTP 200 |
| Leitura pública | 89 | 69 HTTP 200, 2 HTTP 401, 6 HTTP 403, 7 redirecionamentos, 5 incompletos |

HTTP 200 não garante resposta útil, JSON válido do modelo ou fonte probatória. Redirecionamentos também contam no orçamento; uma leitura lógica pode precisar de mais de um transporte. Falhas de serviços foram preservadas, não convertidas em evidência de falsidade. Hive, Sightengine, Hugging Face, OCR, transcrição, imagem, áudio e vídeo **não foram revalidados neste conjunto textual**.

## Correção posterior: descoberta esportiva

Após encerrar e preservar a rodada, foi corrigida a prioridade de descoberta para alegações esportivas estritamente reconhecidas. Relatos da competição/edição com termos de resultado vêm antes de páginas sem resultado, edições diferentes, moedas, ingressos ou categorias diferentes, mesmo quando a página acessória tem domínio oficial.

Nenhum candidato é eliminado por esse ranking. O nome do vencedor alegado não é usado para favorecer concordância; títulos com negação também podem ser lidos. Conteúdo de título/URL não vira prova, a cota de leitura não aumenta e as guardas do corpo continuam obrigatórias. Alegações ambíguas mantêm a ordem anterior. Seis testes adicionais cobrem ranking, neutralidade, idioma, categoria e ausência de voto por título.

**Essa correção posterior foi validada offline; ainda não tem nova taxa factual medida. Os 41,7% acima não a homologam.**

## Validação automatizada e próximos gates

Antes da medição: 1.043 testes backend sem rede, zero skips, 22 arquivos de teste frontend e build concluídos. Depois da correção esportiva: **1.049 testes backend passaram, zero skips; 22 arquivos de teste frontend passaram e build concluído**. Suíte backend executada em contêiner sem rede, com credenciais desligadas pelo runner. `git diff --check` sem erros. Testes sintéticos exercitam contratos e regressões; não entram no denominador de precisão.

Próximos trabalhos, sem reduzir a exigência factual para fabricar conclusões:

1. Reduzir leituras de períodos e assuntos acessórios; validar o ranking novo em outra rodada congelada, preservando todas as anteriores.
2. Recuperar corpo oficial de páginas JavaScript por mecanismos públicos documentados, sem tomar a data de publicação como data do evento. Séries de juros com vigência no dia seguinte não provam sozinhas o dia da decisão do Copom.
3. Melhorar vínculos literais do mesmo evento entre frases, com testes negativos para missão, ano, categoria e autoria diferentes.
4. Montar amostra nova independente, equilibrada por assunto e modalidade; manter inconclusivos e erros no denominador. Só essa avaliação poderá sustentar uma alegação mais ampla de 80%.
5. Revalidar mídias em rodada própria, respeitando autorização de custo e limites. Não há novo gasto Hive nesta revisão.

Revisão local. Commit não comprova push, deploy, Railway ativo ou validação em produção. Nenhum segredo, corpo de notícia completo ou token de relatório deve entrar no Git.
