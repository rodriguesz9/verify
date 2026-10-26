# Checagem real de Gemini e OpenRouter — 26/10

[Oito resultados e contadores sanitizados](validation-ai-contract-2026-10-26.json). Revisão da aplicação testada: `a7796363ee1ee53ad4f396aff87cf957b08bab21`. Janela de 26/10, encerrada às 17h25 no fuso de São Paulo.

## Resultado dos serviços

| Controle com API real | Gemini 3.1 Flash-Lite | OpenRouter gratuito |
| --- | --- | --- |
| Extração de trecho literal | HTTP 503 | Passou; trecho exato |
| Comparação de apoio com duas fontes de teste | HTTP 503 | Resposta inválida; descartada |
| Comparação de refutação com duas fontes de teste | HTTP 503 | Passou; dois pares revisados e duas evidências |
| OCR de imagem de teste conhecida | HTTP 503 | Passou; texto exato, incluindo negação, valor e data |

**Gemini: zero de quatro controles concluídos; quatro HTTP 503. OpenRouter: três de quatro controles concluídos; quatro HTTP 200.** Transporte bem-sucedido não garante contrato válido: a resposta de apoio OpenRouter foi rejeitada antes de virar evidência. A causa exata de formato/schema desse caso permanece desconhecida, pois a resposta bruta não foi retida.

Na imagem, Gemini devolveu 503 após **58,902 segundos**, antes do prazo permitido de 120 segundos. A falha não foi classificada como timeout local. Os outros três 503 chegaram em menos de três segundos cada. Esses resultados não estabelecem chave inválida, uma causa interna específica no Google ou indisponibilidade geral para todos os clientes/modelos.

## O que foi medido

São controles de funcionamento com **clientes reais da aplicação**: extração, geração estruturada, decodificação estrita, avaliação dos trechos e OCR. As duas comparações usam os mesmos corpos sintéticos já verificados offline, com duas famílias distintas e dois pares obrigatórios. Os documentos foram fornecidos diretamente ao teste; suas URLs de exemplo não foram consultadas.

A imagem é uma referência sintética de 1.100 × 340 pixels, SHA-256 `7ffa0355f5dcd0137aa1cf4925b27048710ba90581f3a58ebe44028fae676da5`. Ler seu texto não detecta se uma foto, voz ou vídeo foi gerado por IA.

Não houve busca de notícias, leitura de páginas públicas, Hive, outros detectores, interface, banco de produção ou deploy. As etapas de provedor ficaram isoladas para medir cada serviço; a recuperação entre Gemini e OpenRouter foi validada offline, **não como uma nova execução integrada real nesta janela**.

## Limites e preservação da rodada

Autorização humana separada: **até quatro chamadas Gemini e quatro OpenRouter**, usando apenas acesso gratuito, sem buscas, Hive, recarga ou contratação. Foram utilizados exatamente os oito envios. Não houve repetição do mesmo caso, rotação de modelo, reposição de falha ou reinício de orçamento.

O código, os casos, a imagem e o instrumento foram congelados antes dos envios. Os 102 arquivos permaneceram iguais ao terminar; os 99 arquivos backend congelados foram conferidos contra o commit testado. Manifesto SHA-256 `12fd80f1fbdfeaac9655b806066290eccc96859539fa6d6b9d3e933e43a72a02`.

O transporte só permitiu POST HTTPS aos dois endpoints previstos. OpenRouter usou `openrouter/free`, com preços máximos de prompt, conclusão, requisição e imagem iguais a zero. Cada tentativa foi persistida antes da rede; uma marca exclusiva impede executar a janela outra vez. O arquivo privado foi filtrado para somente duas chaves antes da interpretação; banco, autenticação e outras credenciais não foram importados. Nenhuma resposta bruta, cabeçalho ou chave foi salva.

As janelas anteriores permanecem intactas. A contagem conservadora acumulada OpenRouter passou de 49 para **53**, pelo acréscimo destes quatro envios. Os contadores de outros serviços nesta janela são zero.

## Ajuste posterior de compatibilidade

Depois de encerrar e preservar esses resultados, a leitura passou a aceitar um único envelope completo de JSON em Markdown, formato que alguns endpoints retornam. O limite original de 30.000 caracteres é conferido antes da remoção do envelope. Toda a validação de fontes, IDs, pares, citações e evidências permanece; texto explicativo, vários objetos/blocos, resposta truncada e campo inventado continuam inválidos.

Os diagnósticos da comparação também distinguem JSON inválido de schema inválido. Essa alteração foi verificada com controles simulados dos dois provedores. **Não se pode atribuir a falha real anterior ao Markdown, nem contar essa correção posterior como revalidada nas APIs.** O limite de oito envios terminou e não foi reiniciado.

**1.616 testes backend passaram**, sem rede, credenciais privadas ou skips, incluindo onze novos controles de formato. Foram aceitos envelopes completos equivalentes dos dois provedores; prosa adicional, múltiplos blocos, IDs inventados, pares ausentes, citações alteradas e saída interrompida por limite de tokens continuaram rejeitados. Resultado válido insuficiente continua sem nova tentativa.

## Como usar o serviço que respondeu

Enquanto Gemini retornar 503, a configuração existente `SOURCE_CROSSCHECK_PRIMARY_PROVIDER=openrouter` permite iniciar a **comparação de fontes** pelo OpenRouter. Precisa ser aplicada no ambiente do backend e requer reinício/redeploy desse processo. Mantém Gemini como alternativa, dentro do mesmo prazo e das mesmas regras. Não exige nova chave, contratação ou mudança no frontend.

Essa configuração só escolhe a ordem da comparação; não troca automaticamente o provedor de transcrição nem torna todos os detectores de mídia disponíveis. A recuperação de fontes legíveis e independentes continua sendo uma necessidade separada.

## Precisão factual

Três controles aprovados no OpenRouter não equivalem a 75% de precisão geral de notícias. Esta janela pequena e sintética mede contrato e funcionamento dos serviços. **A última medição factual continua 5/12 corretos (41,7%)**, com sete inconclusivos, em controles de desenvolvimento conhecidos. Não há uma nova taxa de 80% demonstrada por esta checagem.
