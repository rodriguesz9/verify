# Ativar Hugging Face, Hive e Gemini

Revisão: 3 de outubro de 2026. O diagnóstico abaixo cruza os nomes das variáveis do Railway com o código atual. **Valores mascarados não permitem validar credenciais, autorização, crédito ou precisão.** Nenhuma chave deve ser publicada no GitHub, no chat ou nas variáveis `VITE_*`.

Sem orçamento para novos planos? Comece pelo [guia de configuração sem novas contratações](APIS-SEM-CUSTO.md). Não hospedar endpoint dedicado Hugging Face nem comprar detectores apenas para preencher variáveis.

## Situação observada

| Serviço | Configuração observada no Railway | Conclusão permitida |
| --- | --- | --- |
| Hugging Face | `HUGGINGFACE_API_TOKEN` presente; `HUGGINGFACE_IMAGE_API_URL` ausente | Detector de imagem não configurado completamente; token sozinho não hospeda um modelo. |
| Hive imagem | `HIVE_API_KEY` legada presente; `HIVE_IMAGE_API_KEY` ausente | O código pode usar a chave legada, mas o projeto/modelo e a autorização precisam ser validados. |
| Hive Deepfake | `HIVE_DEEPFAKE_API_KEY` ausente | Camada facial não habilitada. Por segurança, não reutiliza automaticamente a chave legada. |
| Hive áudio | `HIVE_AUDIO_API_KEY` ausente | Não há configuração específica de áudio confirmada. O fallback legado não comprova acesso ao detector correto. |
| Gemini | `GEMINI_API_KEY` presente | Integração existe; funcionamento real, modelo e quota não foram confirmados nesta revisão visual. |
| OpenRouter | `OPENROUTER_API_KEY` presente | Integração legada existe, mas **não é chamada pelo pipeline principal de veredito**. Não participa de uma votação para decidir verdade/falsidade. |

O teste real registrado em `audit-providers-2026-10-02.json` é histórico: apontou falhas Hive/Hugging Face/Gemini. Não foi repetido nesta etapa; não descreve necessariamente o estado atual. Testes locais e respostas simuladas não comprovam que fornecedores externos estejam operacionais.

## 1. Hugging Face: token + modelo hospedado + classe correta

1. Crie um token em [Settings → Access Tokens](https://huggingface.co/settings/tokens), com acesso de inferência ao endpoint escolhido. Prefira permissões mínimas; não precisa dar acesso de escrita ao repositório.
2. Escolha um **detector de imagens geradas por IA**, compatível com a tarefa Image Classification. Ler uma página do Hub ou criar um token não coloca esse modelo em execução.
3. Confirme que há um serviço de inferência disponível para o modelo. Se necessário, configure um [Inference Endpoint](https://endpoints.huggingface.co/) dedicado. **Pode haver cobrança de hospedagem mesmo sem consultas**: confira preço, escalonamento e suspensão antes de contratar.
4. Teste pelo painel do endpoint. O contrato esperado é uma lista de objetos `label`/`score`, com pontuações finitas entre 0 e 1. O projeto envia bytes da imagem com o MIME correspondente.
5. No serviço backend do Railway, configure:

```dotenv
HUGGINGFACE_API_TOKEN=<token privado>
HUGGINGFACE_IMAGE_API_URL=<URL HTTPS do endpoint de inferência>
HUGGINGFACE_AI_LABEL=<nome exato da classe positiva de imagem gerada por IA>
```

A classe positiva depende do modelo. O padrão do código é `artificial`, mas **não use esse valor sem conferir o modelo**. Se ele retornar `ai_generated`, configure exatamente esse rótulo. Não confundir a classe negativa `not_ai_generated` com a positiva.

Aceitamos URLs oficiais HTTPS de `router.huggingface.co`, `api-inference.huggingface.co` e subdomínios de `endpoints.huggingface.cloud`, sem usuário/senha na URL. Não usar a URL da página do modelo nem uma URL de Space que não cumpra esse contrato.

Fontes: [tokens](https://huggingface.co/docs/hub/security-tokens), [tarefas suportadas](https://huggingface.co/docs/inference-endpoints/en/supported_tasks), [como testar o endpoint](https://huggingface.co/docs/inference-endpoints/guides/test_endpoint).

## 2. Hive: projetos autorizados aos modelos usados

Entre no [Portal Hive](https://portal.thehive.ai/). Em cada projeto disponível, abra **Integration & API Keys**. A aplicação usa a API **v2**, endpoint `https://api.thehive.ai/api/v2/task/sync`, autenticação `Authorization: token ...`. Chave de Playground/API v3 não deve ser presumida compatível.

Configure no Railway:

```dotenv
HIVE_IMAGE_API_KEY=<chave do projeto de detecção de imagem/vídeo gerado por IA>
HIVE_DEEPFAKE_API_KEY=<chave do projeto com detecção de manipulação facial>
HIVE_AUDIO_API_KEY=<chave do projeto de detecção de áudio gerado por IA>
```

Não copie uma chave qualquer para os três campos. Confirme o modelo habilitado e a resposta de cada projeto. Se seu projeto Hive fornecer um produto combinado de imagem/deepfake, valide com o fornecedor se a mesma chave retorna as classes esperadas para ambas as camadas antes de reutilizá-la explicitamente.

O parser procura classes exatas: `ai_generated` para geração e `yes_deepfake` para manipulação facial. Um projeto de moderação, OCR ou transcrição não substitui esses detectores. HTTP 403 pode indicar chave/projeto/acesso incorreto; não significa que o arquivo seja falso.

Detecção facial não comprova identidade. Duas chamadas Hive não contam como dois fornecedores independentes para a política de concordância do Verify.

Fontes: [autenticação Hive](https://docs.thehive.ai/reference/authentication), [imagem/vídeo](https://docs.thehive.ai/reference/ai-generated-image-and-video-detection-1), [Deepfake facial](https://docs.thehive.ai/reference/deepfake-detection-1), [áudio sintético](https://docs.thehive.ai/reference/ai-generated-audio-detection-1).

## 3. Gemini: chave, modelo disponível e quota

Crie/confira a chave no [Google AI Studio](https://aistudio.google.com/apikey). Verifique acesso à Gemini API, restrições da chave e [limites do projeto](https://ai.google.dev/gemini-api/docs/rate-limits). A documentação atual distingue chaves padrão e chaves de autorização; chaves padrão sem restrições são rejeitadas. Não restringir uma chave backend por domínio de navegador como se fosse usada no frontend.

```dotenv
GEMINI_API_KEY=<chave privada do projeto>
GEMINI_MODEL_NAME=<identificador de modelo disponível à sua conta>
GEMINI_TTS_MODEL=<modelo de geração de voz disponível à sua conta>
```

O código utiliza os padrões `gemini-3.7-flash` e `gemini-3.8-flash-tts` quando as variáveis de modelo estão ausentes. Confirme disponibilidade pelo painel/API; não invente um identificador. `GEMINI_FALLBACK_MODELS` permite alternativas de análise separadas por vírgula. A quota e o acesso ao TTS podem diferir da análise de texto/visão.

Gemini ajuda com sugestões, OCR, análise visual auxiliar e transcrição. **Não é a autoridade final sobre verdade/falsidade.** Um erro 429 é indisponibilidade/quota, não um veredito. Se a voz não puder ser gerada, não se deve apresentar um beep como narração.

Fonte: [guia oficial de chaves](https://ai.google.dev/gemini-api/docs/api-key).

## 4. OpenRouter: chave não ativa o pipeline principal

[Chaves OpenRouter](https://openrouter.ai/settings/keys), [catálogo de modelos](https://openrouter.ai/models) e [guia oficial](https://openrouter.ai/docs/quickstart).

O arquivo legado `openrouter_service.py` tem geração e rotação de modelos. O fluxo principal em `pipeline.py` atualmente **não chama** esse serviço: usa política auditável e checagens recuperadas. Portanto, cadastrar `OPENROUTER_MODEL` ou colocar créditos não faz o OpenRouter participar automaticamente da checagem.

Para acrescentá-lo futuramente, o papel deve ser definido e testado — por exemplo, auxílio na explicação com fontes — sem converter concordância entre modelos de linguagem em prova de verdade.

## 5. Como validar depois de salvar e fazer deploy

1. Confirme que o deploy Railway concluiu com a revisão esperada.
2. Abra `/api/capabilities`: presença de configuração e ferramentas. `operational_status: not_tested` **não significa funcionando**. Essa rota não chama APIs pagas.
3. Execute controles autorizados, com origem conhecida: foto real e imagem sintética; áudio humano e sintético; vídeo original e manipulado; afirmações com fontes documentadas.
4. Confira no relatório os provedores efetivamente usados, status, limitações e evidências. HTTP 200 da aplicação pode conter uma análise parcial/inconclusiva.
5. Registre falsos positivos, falsos negativos e inconclusivos por modalidade. Um exemplo correto não comprova precisão universal. Use o roteiro em [VERIFICACOES-2026-10-03.md](VERIFICACOES-2026-10-03.md).

Para áudio, a política atual depende de detectores autorizados como Hive áudio e Sightengine `ai_speech` (opt-in/entitlement próprio). AssemblyAI apenas transcreve. Vídeo usa amostragem de quadros e áudio disponível: não é perícia temporal completa. Checagem factual depende de Google Fact Check e da cobertura da afirmação, não apenas dos detectores de mídia.

Não é preciso contratar todos os fornecedores. Primeiro valide os serviços escolhidos, o contrato da resposta e os custos. Mesmo com todos ativos, **não existe garantia de vereditos 100% corretos**.
