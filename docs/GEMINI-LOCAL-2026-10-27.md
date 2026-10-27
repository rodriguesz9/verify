# Gemini e ambiente local — 27/10/2026

O Railway está desligado. A configuração desta etapa pertence ao backend local; não é necessário editar variáveis no Railway nem publicar o projeto para testar o ambiente preparado aqui.

**Resultado desta etapa:** ambiente revisado iniciado em `http://127.0.0.1:5176`, com banco SQLite próprio. Gemini 3.7 retornou HTTP 503; **3.5 Flash-Lite respondeu ao texto e à imagem**, com transcrição integral da imagem ainda diferente da referência. Modelo local atualizado para 3.5. [Três resultados sanitizados](validation-gemini-local-2026-10-27.json).

## O problema encontrado nas duas cópias

O container `verify-backend` que já estava aberto usa o código de:

```text
/mnt/externo/IMPORTANTES/mostra/verify/backend
```

Essa é uma cópia anterior, com alterações locais que precisam ser preservadas. Seu cliente Gemini ainda fixa o tempo de transporte em **15 segundos** e não lê `GEMINI_REQUEST_TIMEOUT_SECONDS`. Também não contém a configuração `SOURCE_CROSSCHECK_PRIMARY_PROVIDER` nem o serviço atual de comparação de fontes. Portanto, adicionar essas variáveis ao `.env` dessa cópia não ativa as melhorias recentes.

Nesse fluxo antigo, o resultado Gemini inconclusivo encerra a combinação antes de aproveitar uma possível recuperação por OpenRouter. Além disso, o OpenRouter recebe o texto sem os mesmos corpos das fontes usados na comparação atual. O cliente antigo também contém uma lista de modelos que não garante uso exclusivamente gratuito. Esse ambiente não deve ser usado para novas chamadas de validação.

A cópia revisada está em:

```text
/home/robert/.codex/visualizations/2026/09/11/01a090c3-831e-7912-9ac6-4e1045889773/verify-reviewed
```

Ela contém os prazos configuráveis, proteção contra rajadas, pausa após limite de solicitações e comparação de trechos recuperados com recuperação entre os dois provedores quando ocorre falha técnica. Uma revisão completa que considera as fontes insuficientes continua inconclusiva; o sistema não repete um julgamento válido até obter a resposta desejada.

Existe ainda outro projeto Docker, `verifai-backend`, montado de `/home/robert/Downloads/v0.3/verifai-project/backend`. Ele não faz parte desta preparação e deve permanecer intacto.

## Onde configurar agora

Use o arquivo privado da **cópia revisada**:

```text
/home/robert/.codex/visualizations/2026/09/11/01a090c3-831e-7912-9ac6-4e1045889773/verify-reviewed/backend/.env
```

As opções relevantes, sem mostrar nenhuma chave, são:

```dotenv
SOURCE_CROSSCHECK_PRIMARY_PROVIDER=openrouter
GEMINI_REQUEST_TIMEOUT_SECONDS=90
GEMINI_MODEL_NAME=gemini-3.5-flash-lite
GEMINI_MEDIA_MODEL_NAME=gemini-3.5-flash-lite
```

`SOURCE_CROSSCHECK_PRIMARY_PROVIDER` escolhe o primeiro provedor da **comparação das fontes**. Não transforma uma resposta de IA em fonte independente e não muda automaticamente todo OCR, áudio ou detector de mídia para OpenRouter.

O prazo de 90 segundos permite mais tempo nas chamadas que usam a configuração geral. Outras etapas têm seus próprios limites, compartilhados com o prazo total da análise. Aumentar a espera pode recuperar uma resposta lenta; não corrige uma resposta HTTP 503 já recebida, uma chave inválida ou uma cota esgotada.

O modelo `gemini-3.7-flash` do servidor antigo foi testado e retornou 503 em 1,258 segundo. O perfil revisado passou a usar `gemini-3.5-flash-lite`, que respondeu nesta janela. Não foi habilitada rotação automática; nenhum modelo pago foi incluído.

As chaves ficam somente no `.env` privado, nunca no README, no Git, em capturas ou no frontend. Foram selecionadas somente as quatro credenciais de Gemini, OpenRouter, Google Fact Check e Serper, sem importar o arquivo privado inteiro, o banco ou os segredos do outro ambiente. Segredos de sessão locais são independentes. O arquivo tem permissão 600 e é ignorado pelo Git. Hive e outros detectores pagos não foram configurados nesse perfil de diagnóstico.

## Ambiente separado para a versão revisada

O iniciador `scripts/local-dev.sh` prepara containers próprios usando `docker-compose.local.yml`, o código revisado, esse arquivo privado e configurações locais explícitas. O banco SQLite é próprio desse ambiente; não reutiliza o PostgreSQL dos containers antigos. As portas são publicadas apenas em `127.0.0.1`; o frontend força a API relativa local, mesmo que um `.env` antigo do frontend ainda cite Railway.

Endereços iniciados e conferidos:

| Serviço | Endereço local |
| --- | --- |
| Aplicação | `http://127.0.0.1:5176` |
| Backend | `http://127.0.0.1:8016` |

Execute os comandos na raiz de `verify-reviewed`:

```bash
sh scripts/local-dev.sh up
sh scripts/local-dev.sh status
sh scripts/local-dev.sh down
```

`up` cria ou recria os serviços com a configuração atual; `status` informa o estado; `down` encerra somente esse ambiente. Recriar é necessário depois de alterar o `.env`, pois o Docker injeta o ambiente ao criar o container. Apenas reiniciar o processo ou executar `docker compose restart` pode conservar os valores antigos. A recriação não deve apagar o volume do banco; não usar `down -v`.

Na primeira instalação em outra máquina, use `sh scripts/local-dev.sh up --build` para construir as dependências. Nesta máquina foram reutilizadas imagens locais já presentes e verificadas. As alterações de código entram pelo volume da cópia revisada. O iniciador suporta Compose atual e `docker-compose` antigo; neste último, evita o erro `ContainerConfig` removendo somente os dois containers desse projeto antes de recriá-los. Os volumes nomeados permanecem. Os projetos `verify` e `verifai-project` não são parados, substituídos ou apagados.

Preparar ou iniciar os serviços não comprova que uma análise remota funciona. Uma checagem de saúde local também não consome uma geração de IA nem valida a disponibilidade de Gemini/OpenRouter.

## O que os testes anteriores dizem sobre Gemini

Na [rodada encerrada em 26/10](CHECAGEM-REAL-IAS-2026-10-26.md), o instrumento fixou explicitamente **Gemini 3.1 Flash-Lite**. As quatro chamadas receberam HTTP 503. A chamada de OCR retornou esse erro após 58,902 segundos, antes do prazo de 120 segundos; não foi timeout local.

O servidor antigo, por outro lado, estava configurado com **Gemini 3.7 Flash**. A rodada de 3.1 não mede a disponibilidade do 3.7 e não prova indisponibilidade de todos os modelos Gemini. O gráfico de 28 dias do AI Studio agrega erros e períodos; sozinho, não identifica a causa específica das quatro falhas recentes.

O registro permite afirmar que houve resposta HTTP 503 do endpoint testado. Não permite afirmar chave inválida, falha geral do Google ou que aumentar o tempo resolveu o serviço. Na rodada anterior, OpenRouter concluiu três dos quatro controles de contrato, com uma resposta de comparação descartada por não atender ao contrato.

## Nova checagem autorizada em 27/10

Autorização humana adicional: **até três chamadas gratuitas Gemini**, sem OpenRouter, buscas ou detectores pagos. Foram feitos exatamente três envios físicos. O cliente real da aplicação e a imagem de controle foram congelados antes dos envios; 82 arquivos permaneceram iguais. Modelo explícito, nenhuma alternativa automática e prazo de 90 segundos por chamada. A seleção da alternativa atual para o terceiro controle era prevista no instrumento, sem repetir o caso textual que falhou. Uma recusa de quota/autorização interromperia a janela.

| Controle | Modelo | HTTP | Tempo | Resultado |
| --- | --- | --- | --- | --- |
| Trecho literal com negação/data | 3.7 Flash | 503 | 1,258 s | Indisponível; nenhuma conclusão aceita |
| Mesmo trecho literal | 3.5 Flash-Lite | 200 | 26,593 s | Frase exata, controle aprovado |
| OCR de imagem conhecida | 3.5 Flash-Lite | 200 | 26,390 s | JSON válido; negação, valor e data preservados; transcrição integral diferente da referência |

O controle estrito de OCR **não passou**. Não foi guardada a resposta bruta, portanto não se pode atribuir a diferença a acentos, quebras de linha ou outro detalhe específico. A aplicação mantém conferência do texto antes de usá-lo para checagem factual. OCR lê texto da imagem; não prova autenticidade da imagem.

Este resultado confirma uma alternativa Gemini funcional em dois controles pequenos, não recuperação geral do serviço, precisão factual ou funcionamento de todas as modalidades. O modelo 3.8 constava como opção condicional do instrumento, mas não foi chamado, pois o 3.5 respondeu ao segundo controle. Os três envios foram consumidos; não há reinício de orçamento. A contagem OpenRouter anterior permanece 53, sem novos envios nesta etapa.

A documentação Google lista [3.5 Flash-Lite como modelo multimodal estável](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) e informa [tokens de entrada/saída gratuitos no nível gratuito](https://ai.google.dev/gemini-api/docs/pricing). Não foi habilitado faturamento, pesquisa paga ou contratação. Os [limites Google pertencem ao projeto](https://ai.google.dev/gemini-api/docs/rate-limits), mesmo quando várias chaves são usadas.

## Validação local e limites restantes

Foram repetidos **1.616 testes backend e 205 frontend**, todos aprovados, sem rede, credenciais privadas ou testes ignorados. A sintaxe do iniciador e a configuração Compose foram verificadas. A aplicação abriu no navegador em `/` e `/app`; backend e banco responderam a `/health` e `/ready`. Essa navegação não enviou análise. Os testes simulados e de saúde não são uma nova medição de precisão factual nem validam por si só serviços remotos.

A autorização anterior de até quatro envios Gemini e quatro OpenRouter foi integralmente consumida e permanece preservada, assim como a nova janela de três envios acima. Nenhuma foi reiniciada. Não houve análise de notícias, comparação real de fontes, submissão de mídia na interface, áudio, vídeo ou detector de autenticidade nesta etapa.

Não houve nova porcentagem de acerto factual nesta preparação. A última medição factual registrada continua **5/12 corretos (41,7%)**, com sete inconclusivos. Os controles pequenos de extração, formato e OCR não devem ser apresentados como precisão geral de notícias ou de detecção de mídia.

Próxima validação remota: medir comparação de fontes e checagem factual com o modelo que respondeu, em janela própria autorizada; investigar OCR estrito e depois retomar áudio/vídeo. Nenhum deploy Railway/Vercel foi realizado nesta etapa.
