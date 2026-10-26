# Recuperação entre as IAs — 26/10

Revisão posterior a `c289e2c`. Não é prova de implantação nem uma nova medição factual.

## Problema confirmado

Na comparação de fontes, JSON malformado, limite de tokens ou revisão incompleta da primeira IA encerravam a operação antes de usar a segunda. A alternativa existia para falhas de transporte, mas não para essas falhas técnicas de saída. Uma resposta HTTP 200 inválida podia, portanto, impedir uma comparação que o outro serviço conseguiria concluir.

Agora uma saída tecnicamente inválida pode usar o outro provedor previsto, uma vez por etapa. O segundo recebe **o mesmo pedido original**, com as mesmas afirmações, fontes, citações e contrato de resposta. A saída defeituosa é descartada integralmente e não é enviada como sugestão ao outro modelo. Não se completam campos ausentes nem se juntam pedaços de respostas diferentes.

Isso difere de um resultado válido com evidência insuficiente: uma revisão completa que não encontra prova continua final. Não se repete um julgamento para obter uma conclusão desejada. Bloqueios explícitos de conteúdo, incompatibilidade com a política de custo, configuração inválida e entrada fora dos limites também não acionam essa recuperação técnica.

## Prazo e limites

As duas etapas compartilham o prazo existente de comparação, até 240 segundos, até 120 por provedor e limitadas ao restante da análise textual. Cancelamento continua aguardando o encerramento do trabalho; não há requisições destacadas em segundo plano.

A chamada de comparação Gemini pode produzir até **4.096 tokens**, alinhada à OpenRouter e ao teto que o cliente já permitia. As demais chamadas conservam seus limites. Isso dá espaço para a matriz completa de afirmações/fontes e para o processamento interno do modelo; não demonstra que o limite anterior causou a falha remota observada.

Não foram alterados chaves, modelos, preços máximos zero do OpenRouter, limites de requisições, pause de quota, prazo global, assinatura ou cobrança. As alternativas explícitas de modelo e a única recuperação Gemini 503 já existentes continuam limitadas; duas etapas de provedor não significam necessariamente apenas dois envios HTTP físicos. Cada tentativa continua contando antes do envio.

## Compatibilidade Gemini

O cliente aceitava texto sem `finishReason`. A [referência oficial](https://ai.google.dev/api/generate-content) informa que a ausência desse campo significa que a geração ainda não terminou. O cliente agora exige conclusão `STOP`, rejeita trechos truncados e ignora o texto interno de raciocínio como fonte de conteúdo visível.

Para Gemini 3 e posteriores, o cliente deixa o modelo usar sua configuração padrão de amostragem. A [documentação de diagnóstico](https://ai.google.dev/gemini-api/docs/troubleshooting) recomenda os padrões nos modelos Gemini 3 anteriores e remover os parâmetros personalizados em 3.6+, onde são ignorados e poderão causar erro em uma revisão futura. Modelos anteriores preservam a temperatura solicitada; uma configuração inválida continua sendo rejeitada antes de qualquer envio. Modelo, formato de schema e chaves permanecem os mesmos.

Esses ajustes corrigem contrato e compatibilidade do código. **Não consertam a disponibilidade do servidor Google:** o 503 anterior foi uma falha remota. A recuperação limitada e o provedor alternativo reduzem seu impacto quando o outro serviço entrega uma resposta válida, sem garantir disponibilidade contínua.

## Diagnósticos de texto, OCR e áudio

Gemini agora identifica respostas vazias, não concluídas, truncadas, malformadas e bloqueadas com categorias fixas. Mensagens brutas, raciocínio, cabeçalhos e credenciais não entram nos diagnósticos.

Extração de texto conserva esses motivos na cobertura da análise. OCR separa a falha Gemini da falha OpenRouter, inclusive quando os dois serviços falham por causas diferentes. Áudio conserva os motivos de cada tentativa de transcrição. Falha técnica continua podendo usar a alternativa existente; bloqueio explícito ou excesso de tamanho não causam reenvio direto da mesma tarefa a outro serviço.

Essa proteção tem escopo de tarefa: não desativa globalmente a busca literal ou uma comparação independente com fontes. Nenhum detector de mídia foi ativado ou chamado por essas mudanças.

## Avaliação

Os controles usam transportes simulados e corpos de teste. Exercitam recuperação nos dois sentidos, duas falhas sem evidência parcial, resposta válida inconclusiva sem nova tentativa, preservação de contrato/prazo/cancelamento, bloqueios e diagnósticos privados separados.

**1.605 testes backend passaram**, sem rede, credenciais privadas ou skips. São 42 controles novos sobre os 1.563 anteriores: dezessete de contrato/configuração Gemini, dez de recuperação entre provedores, catorze de diagnósticos na leitura e um de bloqueio explícito OpenRouter. Controles antigos de saída incompleta foram atualizados para exigir a alternativa limitada e zero evidências quando ela também falha; o controle de insuficiência válida continua exigindo nenhuma repetição.

A última medição factual continua **5/12 corretos (41,7%)**; testes de código não a substituem. A checagem curta foi autorizada e concluída: [resultados reais](CHECAGEM-REAL-IAS-2026-10-26.md). Usou exatamente quatro chamadas Gemini e quatro OpenRouter, sem buscas, Hive ou modelos pagos, preservando as janelas anteriores. Gemini retornou quatro HTTP 503; OpenRouter passou em três dos quatro controles. Isso mede funcionamento/contrato, sem atualizar a precisão geral de notícias, fotos, áudio ou vídeo.
