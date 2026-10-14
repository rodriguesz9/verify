# Verify: validação local de APIs e pendências — 14/10/2026

Horário de Brasília. O titular autorizou APIs/créditos gratuitos e até US$ 0,03 do saldo Hive existente para duas imagens e um áudio curto. Não houve contratação, recarga, cartão, renovação Railway, alteração de variáveis remotas ou acesso ao banco de produção. O titular escolheu **validar APIs agora e deixar a interface pendente**. Publicação Git e testes automatizados não homologam produção nem precisão universal.

## Conclusão executiva

**Ainda não está pronto para afirmar que todas as verificações dão vereditos corretos.** Os detectores de imagem, transcrição alternativa e OCR local responderam aos controles. A descoberta automática de evidências continua insuficiente nos controles históricos. Gemini Lite respondeu à inspeção de imagens, mas retornou HTTP 503 na comparação textual e na transcrição. OpenRouter gratuito e AssemblyAI assumiram os caminhos alternativos.

Um controle separado do componente de comparação, com os dois corpos públicos reais já capturados, refutou corretamente a data falsa de Elizabeth II. Isso não equivale a uma checagem automática bem-sucedida: a busca normal não selecionou esses dois corpos nos ensaios. Não foi implementado um veredito fixo, nem fornecidas fontes especiais à rota de produção para forçar o resultado.

## O que mudou

- Extração DOM separa corpo, título, subtítulo, autoria, legenda e contexto. `articleBody` precisa ser visível, não JSON-LD. Cabeçalhos não se tornam prova.
- Espaços reais de markup inline são preservados: `16` não vira `1 6`, nem `no` vira `n o`.
- Tabelas sem interpretação de colunas ficam contextuais; controles de vídeo/áudio não são narrativa. Isso evita juntar metadados e fallback do player a uma data factual.
- Datas nominais claras de falecimento são admitidas; data de funeral, anúncio, publicação ou morte de outra pessoa não é emprestada.
- Aliases documentais pequenos preservam identidade e ação: Apolo/Apollo, lançamento/launches, Lua/Moon, pisou/walked. Pouso de nave não comprova caminhada humana.
- Referência a pessoas em outra parte não transforma caminhada de robô em caminhada humana.
- **Correção encontrada no ensaio real:** “as provas ... não são poucas” não nega a caminhada. Negação de quantidade não pode sustentar “o homem nunca pisou na Lua”. Agora esse trecho ambíguo é excluído, não reinterpretado automaticamente como o oposto.
- Fontes elegíveis são avaliadas após leitura, não pelo número de URLs. Auditoria expõe URLs selecionadas e motivos limitados de exclusão, sem publicar corpos inteiros.
- Corpos e falhas são reutilizados no mesmo pedido; até seis tentativas cumulativas, sem repetir falhas. Recuperação incompleta preserva somente a primeira leitura concluída, com aviso.
- Gemini é o comparador primário; OpenRouter gratuito é alternativa de indisponibilidade. Extração auxiliar e comparação não contam como duas fontes independentes.
- Credencial ausente, negada, inválida, quota, timeout e indisponibilidade têm estados distintos nos detectores.

## Resultados reais observados

| Controle | Resultado observado | Limite da conclusão |
| --- | --- | --- |
| Elizabeth II morreu em 8/9/2022 | Duas tentativas da afirmação verdadeira: inconclusivas. | As páginas escolhidas não deram duas evidências completas de nome/evento/data. “Nesta tarde” e “quinta-feira” não viram data absoluta por metadata. |
| Elizabeth II morreu em 9/9/2022 | Duas tentativas do controle falso: inconclusivas. | Data falsa não aprovada, mas refutação automática não demonstrada. É alteração de data construída para teste, não uma postagem falsa coletada. |
| Apollo 11 lançada em 16/7/1969 | Duas tentativas: inconclusivas. | Primeiro ensaio revelou metadata/player unidos à narrativa e grafia Apolo; corrigidos com testes. Último ensaio teve recuperação adicional limitada pelo teto QA de buscas; não homologar como acerto. |
| O homem nunca pisou na Lua | Um ensaio: conflito, antes da correção de escopo de negação. | OpenRouter classificou um trecho afirmativo com “não são poucas” como apoio. Bug defensivo corrigido offline. Sem nova homologação real desse boato após a correção. |
| Componente: data falsa, corpos Royal/UOL previamente capturados | `success/refuted`, duas evidências, duas famílias, cobertura completa; OpenRouter gratuito respondeu após Gemini 503. | **Teste de componente com documentos reais em cache**, não descoberta automática, navegação ou checagem pela interface. |
| Foto NASA de planta | Hive/Sightengine com sinais baixos; Gemini visual respondeu. Origem inconclusiva. | Procedência pública NASA é conhecida para o controle; sinais baixos e EXIF não certificam captura autêntica. OCR Gemini retornou um fragmento curto, não texto útil para checagem. |
| Planta conhecida gerada por IA | `AI_Generated`; Hive aproximadamente 0,999999968 e Sightengine 0,99; Gemini visual respondeu. | Um controle positivo de imagem, não benchmark de precisão. As pontuações são sinais, não porcentagens de certeza. |
| Impresso com negação/valor/data | Tesseract leu “Nao pague”, R$ 123,45 e 03/10/2026; texto disponível para conferência. | Leitura não comprova verdade ou origem. O acento foi alterado; comparar sempre com o original. |
| eSpeak sintético de cinco segundos | Hive respondeu com sinal aproximadamente 0,990827. AssemblyAI transcreveu; origem inconclusiva. | Um detector não comprova clonagem. Transcrição alterou palavras (“pixu da gente”); não homologada como transcrição fiel. |
| Mesmo áudio, perfil Gemini | Gemini retornou 503; AssemblyAI assumiu e retornou a mesma transcrição. | Fallback funcional, não sucesso de ASR Gemini. Nenhuma nova chamada paga Hive. |
| Vídeo sintético silencioso de três segundos | Três quadros Sightengine responderam com sinal IA 0,99. Origem inconclusiva. | Hive bloqueado pelo limite QA já consumido. Um provedor em três quadros não são três provedores; não homologa deepfake temporal ou vídeo humano. |
| PDF da imagem IA | PDF/200, `no-store`, duas páginas renderizadas e inspecionadas. | Sem nova chamada de análise; salvamento/abertura pela interface não testados nesta rodada. |

Os controles de Queen/Apollo são afirmações factuais curtas, não aprovação de artigos completos. O boato da Lua é uma formulação normalizada de uma alegação documentada; não um arquivo literal da postagem original. Nenhum resultado inconclusivo foi contabilizado como classificação correta.

## APIs: funcionamento e acesso

| Serviço | Estado nesta rodada | O que fazer |
| --- | --- | --- |
| Google Fact Check | Sete consultas HTTP 200; sem checagens utilizáveis para esses controles. | Não tratar ausência de ClaimReview como falsidade. Melhorar a recuperação documental complementar. |
| Serper | 22 chamadas HTTP 200; notícias e links retornaram, mas vários corpos não eram utilizáveis. | Avaliar relevância de corpo e diversificação de fontes; não votar por título/snippet. Teto QA foi atingido, sem seguir enviando. |
| OpenRouter | Nove chamadas HTTP 200; extração e comparação gratuita efetivamente exercidas. | Manter `openrouter/free` ou variante `:free` e preço máximo zero. Resposta do modelo ainda pode conter relação incorreta; guardas/eval são necessárias. |
| Gemini Lite | Oito chamadas: cinco HTTP 200 de mídia e três HTTP 503 (comparações/ASR). | Manter modelo explícito, timeout/fallback e acompanhar a disponibilidade; chave presente não resolve 503. Não alternar contas para contornar quota. |
| Hive v3 | Três chamadas HTTP 200: duas imagens e cinco segundos de áudio. | Secret Key v3, modalidades opt-in e limites; não confundir Access Key ID com Secret Key. Nenhum reenvio pago. |
| Sightengine | Seis chamadas HTTP 200: duas imagens, impresso e três quadros. | Acesso de imagem está funcionando nesses controles; `ai_speech` continua desativado e depende da autorização do plano/modelo. |
| AssemblyAI | Dois uploads, duas tarefas e seis consultas, HTTP 200. | Retomada/fallback exercidos, mas transcrição real ainda exige conferência e corpus humano. |
| Hugging Face | Desativado por decisão de custo; não chamado. | Não habilitar endpoint pago sem autorização. Chave sozinha não fornece inferência hospedada. |
| SerpAPI/Lens, TinEye, Wayback, C2PA confiável | Não homologados nesta bateria. | Não representam teste real de busca reversa, assinatura ou procedência. Recursos sem acesso continuam explicitamente indisponíveis. |

## Configuração na retomada Railway

Não copie indiscriminadamente o `.env` local. Preserve referência Railway do banco, segredos de autenticação/HMAC fortes e estáveis, CORS da Vercel e configurações de cookies de produção. Chaves ficam somente no backend. O [guia de retomada](REATIVAR-RAILWAY-2026-10-13.md) contém a lista completa e os controles após renovação.

```dotenv
GEMINI_MODEL_NAME=gemini-3.1-flash-lite
GEMINI_MEDIA_MODEL_NAME=gemini-3.1-flash-lite
GEMINI_REQUEST_TIMEOUT_SECONDS=60
SOURCE_CROSSCHECK_ENABLED=true
SOURCE_CROSSCHECK_PRIMARY_PROVIDER=gemini
SOURCE_CROSSCHECK_TIMEOUT_SECONDS=60
SOURCE_CROSSCHECK_SEARCH_LIMIT=3
OPENROUTER_ENABLED=true
OPENROUTER_MODEL=openrouter/free
AUDIO_TRANSCRIPTION_PROVIDER=assemblyai
LOCAL_OCR_ENABLED=true
HUGGINGFACE_ENABLED=false
SIGHTENGINE_AUDIO_ENABLED=false
HIVE_API_VERSION=v3
HIVE_V3_MEDIA_TYPES=image,audio
VIDEO_MAX_FRAMES=3
```

`SEARCH_LIMIT` permite 1/2/3. A primeira consulta é literal; se os corpos não bastarem, o plano pode separar fontes oficiais e explicações editoriais em até duas consultas neutras. Afirmação original, valores, data e negação permanecem intactos no julgamento. Quota/erro interrompem o plano. Tudo dentro dos mesmos 45 segundos e seis tentativas de páginas; até três documentos comparados, prazo compartilhado de até 60 segundos para modelos.

Hive continua pago. Os limites de **produção** precisam ser decididos conforme o saldo; não são os limites da bateria QA e não são um teto financeiro global em réplicas/reinícios. A QA reservou exatamente duas imagens/um áudio/cinco segundos antes de enviar, com diário persistente e sem reset. Pela [tabela pública Hive](https://thehive.ai/pricing), a estimativa nominal é aproximadamente US$ 0,02589; **não foi conferida a fatura da conta**. Não houve autorização de novos gastos após essa reserva.

## Evidências e reprodução segura

- Backend: **721 testes offline passaram**, sem rede/chaves/banco produtivo. Frontend: **181 testes passaram**, build de produção concluído. Isso é regressão funcional, não precisão de IA. CI remoto é verificado após o push; PostgreSQL é repetição da suíte com três controles de integração, não outros 721 testes distintos.
- `scripts/validation_ui_server.py`: banco/autenticação descartáveis, allowlist de chaves, limite persistente por provedor, Hive com opt-in pago explícito, lock e reservas sincronizadas antes da rede. Falhas não são reembolsadas/resetadas.
- `scripts/validation_api_probe.py`: um controle público fixo por execução, porta local 8027, sem retry. Marcador de tentativa antes de POST, sem sobrepor registros, tokens assinados somente em memória. Cabeçalhos/objetos raw/credenciais não são publicados.
- Diagnóstico de fontes opt-in fica limitado aos quatro textos públicos exatos e aos dois documentos oficiais/editoriais fixos. Outros textos não são gravados. URLs com query/fragmento/credenciais não são retidas no diagnóstico v2; registro antigo é preservado, não reinterpretado.
- Corpos completos, PDFs de diagnóstico e registros detalhados ficam na pasta local da rodada, fora do repositório. Não foram publicados `.env`, cookies, tokens de PDF/conferência, IDs remotos de tarefas ou artigos integrais. O [resumo sanitizado](validation-api-summary-2026-10-14.json) não contém esses dados.

## O que falta para concluir

1. **P0: recuperação automática.** Medir quais URLs foram omitidas/bloqueadas e recuperar corpos biográficos/factuais em famílias distintas; não fixar respostas/fontes apenas para os controles conhecidos. Comparar relevância e cobertura com conjunto separado de notícias.
2. **P0: NLI/negação.** Revalidar o boato da Lua após correção; incluir negação de quantidade, fala atribuída, ironia, citação, mudança de valor/data/pessoa e textos mistos. Não declarar precisão por esses testes unitários.
3. **P0: disponibilidade Gemini.** Comparação/ASR ainda falharam com 503. Verificar operação no momento da apresentação, sem assumir que visão funcionando homologa todas as modalidades.
4. **P0: interface e produção.** Reconectar o navegador com autorização, testar texto/link/upload/conferência/PDF em celular e desktop e repetir após renovar Railway, confirmando commit/variáveis/banco/CORS. Pendentes por escolha do titular e hospedagem expirada.
5. **P1: corpus independente.** Gravações humanas próprias/autorizadas em português, vídeos reais com/sem voz e manipulações autorizadas; origens rotuladas e hash. Não substituir isso por eSpeak ou vídeo de imagem repetida.
6. **P1: apresentação.** Mostrar resultados efetivamente validados e limitações. Não prometer que notícias automáticas já estão homologadas, nem apresentar teste de componente/cache como checagem comum pela interface. [Roteiro existente](ROTEIRO-BANCA.md).

Critério de encerramento: recuperação/conferência/decisão por afirmação demonstradas em corpus separado, pendências de acesso explicitadas, testes pela interface e produção concluídos. Não há promessa técnica válida de 100% de acerto universal.
