# Correções e diagnóstico de produção — 8 de outubro de 2026

Registro complementar da revisão candidata, horário de Brasília. **O Railway está online.** Isso foi confirmado pelo conector da conta, não inferido da presença de chaves. Os problemas observados estão em etapas diferentes: validação da entrada, gravação de métricas no banco, disponibilidade de modelos e configuração específica de detectores. Este registro não confirma promoção do candidato nem homologação de todas as modalidades.

## 1. Qual código estava publicado?

| Ambiente | Evidência obtida nesta rodada | Limite da conclusão |
| --- | --- | --- |
| Railway, serviço `verify`, ambiente `production` | Backend e PostgreSQL online no conector; deployment `b34a1f5e`, de 04/10, baseado em `master`, SHA `5db970d…` | Processo online não significa que toda rota ou API esteja funcionando |
| Vercel | Deployment pronto, também identificado com SHA `5db970d…` | Não contém automaticamente as mudanças feitas na branch candidata |
| Candidato GitHub | Commit anterior `7c6b676`, branch `entrega/banca-2026-10-08`; os três jobs de CI passaram | CI testa regressões/build, não respostas reais de todos os fornecedores nem promoção a produção |
| Correções desta rodada | Revisão local em andamento sobre a branch candidata | Não declarar commit/push, aplicação de variáveis ou implantação antes de confirmar a operação e o SHA |

A observação anterior de timeout DNS ao consultar `/health` deste ambiente permanece histórica. **Ela não era prova de que o Railway estivesse fora do ar**; a confirmação posterior pelo conector elimina essa interpretação.

## 2. Por que aparece “Não foi possível concluir a checagem”?

### Texto: três respostas HTTP 422

Logs de 08/10 registraram três respostas `422` em `/api/check-text`. Esse código identifica rejeição de entrada pela validação da API, antes de concluir a checagem. **Não temos o corpo desses pedidos nem o detalhe da resposta:** não atribuir a causa a limite de 5.000 caracteres, modelo, quota ou chave sem reproduzir a entrada exata.

Controle concluído no candidato: texto curto pela interface retornou HTTP 200. Uma entrada de 5.001 caracteres ficou bloqueada antes do envio, com orientação explícita e sem corte silencioso. O frontend agora explica respostas 422 em linguagem simples. Isso não identifica retrospectivamente o campo dos três pedidos públicos recusados; para reproduzi-los, ainda seria necessária a entrada exata. Um erro de entrada não deve ser apresentado como veredito do conteúdo.

### Link: HTTP 500 na persistência PostgreSQL

Outro log de `/api/check-url` apresentou `DataError`: o banco esperava data/hora no argumento de consulta 7 e recebeu uma string. Há evidência de erro de persistência; isso **não comprova falha do Google Fact Check, do Gemini ou de todas as checagens de texto**.

Correção candidata: `services/metric_dates.py` normaliza datas absolutas para `datetime` UTC antes de gravar métricas. Datas relativas de busca, como “2 hours ago”, valores inválidos e ausência de data tornam-se `None`, sem inventar uma data absoluta. O texto de origem pode permanecer no relatório como recebido; não é uma data validada da afirmação.

Regressões incluem formatos absolutos, fuso horário, objetos `date`/`datetime` e valores relativos/inválidos. **A nova regressão de persistência passou em PostgreSQL descartável real.** Falta validar o mesmo caminho depois de publicar o SHA corrigido; não tocar diretamente em registros de produção para simular sucesso.

## 3. Gemini: o que foi testado agora?

Três chamadas diagnósticas reais nesta rodada, sem reenvio automático:

| Modelo e controle | Resposta observada | O que permite afirmar |
| --- | --- | --- |
| `gemini-3.8-flash`, texto | Timeout ao atingir 60 s | Essa chamada não produziu análise utilizável; sucesso do controle mínimo anterior em 07/10 não garante disponibilidade atual |
| `gemini-3.8-flash`, leitura de imagem | HTTP 503, aproximadamente 41,8 s | O fornecedor informou indisponibilidade; esperar indefinidamente ou criar outra chave no mesmo projeto não resolve isso por definição |
| `gemini-3.1-flash-lite`, leitura da mesma referência | HTTP 200, aproximadamente 2,376 s | O texto retornado correspondeu exatamente à referência de 88 caracteres, inclusive negação, valor e data |

Isso mostra que **há um caminho de leitura de imagem funcional com outro modelo**, não que o Gemini deixou de aceitar imagens nem que todos os modelos estão quebrados. Também não prova que toda falha anterior seja exclusivamente código ou quota.

Depois dos três diagnósticos, houve **três chamadas Gemini adicionais pela interface**, em servidor isolado configurado com o modelo Lite:

- Texto: `/api/check-text` e chamada Gemini retornaram HTTP 200.
- Planta gerada por IA conhecida: `/api/upload` retornou HTTP 200; as duas chamadas Gemini de leitura/inspeção também retornaram HTTP 200.
- O DOM mostrou inspeção visual com estado “Respondeu” e leitura com estado “Sem texto”. A imagem de planta não forneceu texto legível para checagem; esse estado não é erro de autenticação nem afirmação de falsidade.
- O relatório da imagem permaneceu **inconclusivo**, corretamente: só havia LLM auxiliar, com detectores decisivos não habilitados nesse servidor. Não converter inspeção visual em detector homologado de IA ou verdade.

Total desta rodada: **seis chamadas Gemini reais**, sem confundir os três diagnósticos com os três pedidos da interface. Não extrapolar esses controles para transcrição de voz, identidade, perícia de manipulação ou precisão em qualquer imagem. Não houve envio ao Hugging Face.

O template candidato passou a indicar `gemini-3.1-flash-lite` tanto em `GEMINI_MODEL_NAME` quanto em `GEMINI_MEDIA_MODEL_NAME`, com base nos controles de texto, leitura e inspeção auxiliar que responderam. Isso **não muda automaticamente as variáveis do Railway** nem homologa fala/precisão; o SHA/configuração publicados devem ser conferidos depois da aprovação de promoção.

### Interpretar os limites do painel

RPM limita pedidos por minuto; TPM, tokens por minuto; RPD, pedidos por dia. O painel enviado mostra **máximos observados em 28 dias em comparação com limites**, não necessariamente a cota restante neste instante. Valores como `8 / 5` e `27 / 20` indicam que houve picos acima daqueles limites; não identificam sozinhos a causa de um pedido específico de hoje.

As cotas são compartilhadas pelo projeto/modelo. Mais chaves do mesmo projeto não criam nova franquia. Não usar rotação de modelos/chaves para contornar um bloqueio do fornecedor. Modelos com limites zero não são contingência utilizável só por aparecerem na lista.

A revisão inclui admissão local de rajadas por processo/modelo e pausa após `429`. São guardas do aplicativo, não leitura do saldo global do Google: reinícios, réplicas e outros clientes do mesmo projeto continuam fora desse contador. O deadline de 60 s permanece limitado; falha reduz cobertura e não se transforma em “verdadeiro” ou “falso”.

## 4. Hive: autorização atual e configuração necessária

O usuário autorizou uso do **saldo existente**, informou aproximadamente US$ 0,94 e considera recarga futura. Isso não autoriza fazer recarga, cadastrar cartão, ativar cobrança automática nem assumir que o saldo foi conferido no fornecedor.

O diagnóstico limitado de **duas imagens foi concluído com resposta real HTTP 200** em 08/10, aproximadamente 10:03 UTC (07:03 em Brasília), sem áudio/reenvio automático:

| Controle com procedência conhecida | Resposta | Sinal de geração por IA retornado | Sinal facial retornado |
| --- | --- | --- | --- |
| Foto publicada pela NASA | HTTP 200, 1.515 ms | `0.0002034269780552065` | `0` |
| Planta gerada por IA para validação | HTTP 200, 2.430 ms | `0.9999999677581336` | `0` |

**Comprovado:** transporte/autenticação/parsing do cliente v3 para esses dois controles de imagem. Os sinais diferenciaram estes exemplos, mas **duas imagens não medem acurácia**, não homologam face-swap/voz e não provam que um sinal facial zero certifique autenticidade. O probe não foi executado pela interface da aplicação.

Máximo nominal autorizado desses dois pedidos: **US$ 0,012**. Saldo e fatura não foram consultados; não apresentar a estimativa como débito comprovado ou saldo restante. Nenhuma recarga/cobrança automática foi feita.

Para ativar a revisão v3, além da chave privada correta:

```dotenv
HIVE_API_VERSION=v3
HIVE_V3_MEDIA_TYPES=image,audio
HIVE_V3_IMAGE_REQUEST_LIMIT=20
HIVE_V3_AUDIO_SECONDS_LIMIT=60
VIDEO_MAX_FRAMES=3
```

`HIVE_V3_API_KEY` recebe a **Secret Key v3**, não Access Key ID. Não colocar a chave no documento, Git, frontend ou print. `image` inclui quadros de vídeo; imagem/facial compartilham uma chamada e **um fornecedor**, não dois votos independentes.

Os limites novos têm padrão zero: mesmo com chave/modalidades, sem reserva positiva não há envio v3. Os números acima são exemplo conservador de configuração, não declaração de que já foram aplicados no Railway. O limite de áudio é **60 segundos acumulados por processo**, com duração validada arredondada para cima, não 60 segundos por arquivo. Falhas, timeout e cancelamento não devolvem reserva; não provam que a API não processou/cobrou.

**Não são teto financeiro global:** reinícios renovam contadores e réplicas não os compartilham. Conferir Usage/Billing no Hive, manter recarga automática desativada e ensaiar poucos arquivos autorizados. Preços/versão/acesso devem ser conferidos antes da apresentação. [Guia de ativação e estimativas](ATIVACAO-HIVE-VOZ-2026-10-08.md).

## 5. Sightengine, Hugging Face e leitura de imagens

- **Sightengine:** o menu “AI Music Detection” detecta música, não voz falada. O modelo de voz é `ai_speech`, com acesso restrito a empresas/parceiros segundo a documentação consultada. Solicitar teste acadêmico sem contratação e habilitar `SIGHTENGINE_AUDIO_ENABLED=true` somente após confirmar permissão/créditos. Chave de imagem não libera voz automaticamente.
- **Hugging Face:** o usuário não deseja uso pago. `HUGGINGFACE_ENABLED=false` é o padrão da revisão e impede envio mesmo com chave/endpoint. Não contratar endpoint nem comprar créditos para preencher esse card. Resultados históricos experimentais não participam do veredito.
- **OCR:** é somente a leitura de palavras em um print/imagem para checar o conteúdo: por exemplo, preservar “Não pague”, R$ 123,45 e uma data. Não detecta sozinho IA, montagem ou mentira. Tesseract local continua disponível sem chave; a interface permite conferir/corrigir a leitura antes de uma checagem textual separada.

## 6. Interface pública: resultado, explicação e ação

O grid de fornecedores da imagem enviada deixou de aparecer aberto no candidato. Nomes de modelos/APIs, códigos HTTP, variáveis de configuração e pontuações de detectores ficam em **“Detalhes técnicos” fechados por padrão**, para auditoria voluntária.

O público vê:

1. Resultado e explicação em linguagem simples.
2. O que ficou inconclusivo ou incompleto, sem mascarar falhas como autenticidade.
3. Trechos observados, fontes recuperadas e diferença entre verdade da mensagem e produção da mídia.
4. “Leitura do texto na imagem” em vez da sigla OCR; negações, valores e datas preservados.
5. Próximo passo seguro: conferir o original/fonte independente e confirmar pedidos financeiros por canal conhecido.

Transcrição pendente mantém aviso próprio; resultado de áudio desconhecido não recebe aparência verde de confirmação. Detalhes técnicos não alteram o registro original nem introduzem porcentagem calibrada de verdade. JSON técnico copiável continua sem tokens de exportação/conferência.

Modo Fácil e visualização mobile de **375 px** foram conferidos na interface isolada sem rolagem horizontal excedente. Isso não substitui ensaio da revisão publicada, em outros tamanhos/zoom/teclado. A etapa de conferência também usa rótulo público simples, sem “OCR por Tesseract”; limites contam caracteres Unicode sem cortar silenciosamente o conteúdo.

## 7. Testes concluídos e checkpoints

| Verificação | Última execução concluída informada neste checkpoint | Alcance |
| --- | --- | --- |
| Backend offline SQLite final | **482 testes**, 9,614 s, aprovados | Sem chamadas externas; inclui os controles de segurança do probe e guarda de leitura excessiva; não disponibilidade ou precisão reais |
| Modo PostgreSQL descartável final | **482 testes**, 10,428 s, aprovados, com `--postgres-test-url` explícito | **Quatro** testes são integração real PostgreSQL; os demais continuam SQLite/mocks. Não são 482 integrações de banco nem 964 casos distintos ao somar as duas execuções |
| Frontend final | **155 testes**, 698,83 ms, aprovados | UI/contratos/regressões sem fornecedores reais |
| Build frontend final | **1.977 módulos**, aproximadamente 3,92 s | Compilação, não deployment |
| CI do commit anterior `7c6b676` | Três jobs `SUCCESS` | Não inclui automaticamente alterações feitas depois desse commit |
| Probe Hive: segurança | 13 controles integrados na suíte final aprovada | Mocks/guardas sem cobrança; separados das duas chamadas reais descritas acima |

Contagens anteriores — 424/142, 150 na etapa exclusivamente visual e checkpoint 468/154 — continuam históricas. Não somar execuções, tratar mocks como chamadas reais ou converter testes aprovados em percentual de vereditos certos. A aprovação remota de CI citada é do commit anterior, não comprovação automática de CI/deployment destas correções finais.

## 8. Próximo aceite antes da banca

1. Identificar o SHA candidato com as suítes finais aprovadas e registrar também falhas/limitações dos controles reais; o resultado local não substitui CI remoto nem ensaio da publicação.
2. Confirmar autorização de promoção/publicação e dos exemplos de limites de vinte imagens/sessenta segundos de áudio por processo. A aprovação foi solicitada, mas ainda não recebida neste checkpoint: **não promover nem implantar enquanto pendente**. Preservar mudanças do repositório original.
3. Conferir variáveis efetivas do backend, saldo/acesso e ferramentas da imagem final sem expor segredos.
4. Pela interface publicada desse SHA: texto curto, texto com negação, link público autorizado, print de leitura, foto publicada e imagem de IA com procedência conhecida.
5. Validar histórico no PostgreSQL e exportação do **mesmo** relatório; salvar/abrir o PDF no navegador.
6. Ensaiar Modo Fácil/mobile/zoom/teclado. Fala humana/vídeos autorizados e avaliação independente continuam necessários para homologar essas modalidades.

Não prometer “100% certo”. Falha de API ou evidência insuficiente deve produzir inconclusivo/limitação, não um rótulo inventado para a apresentação. Ver [roteiro da banca](ROTEIRO-BANCA.md), [status detalhado](STATUS-VERIFICACOES-2026-10-08.md) e [gates até 11/10](ENTREGA-ATE-11-OUTUBRO.md).
