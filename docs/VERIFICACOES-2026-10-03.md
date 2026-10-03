# Verificações e configuração — revisão de 3 de outubro de 2026

Esta revisão melhora a segurança das decisões, mas **não comprova precisão em produção**. Este relatório documenta a auditoria anterior à publicação: não houve commit, push, deploy ou compra de serviços durante aqueles testes. O usuário autorizou posteriormente commit/push; consulte o [guia de configuração e publicação](CONFIGURACAO-PRODUCAO.md) para o procedimento e pendências. A cópia revisada está na pasta interna `verify-reviewed`; o disco externo ficou indisponível durante a revisão e sua cópia não foi sobrescrita.

## O que mudou

O relatório separa **veracidade da afirmação** de **origem/produção da mídia**. Uma ilustração gerada por IA pode comunicar algo verdadeiro; uma gravação real pode conter uma mentira. Pontuações de detector e o índice legado do Verify não são porcentagens calibradas de verdade.

### Texto e conteúdo de links

- Gemini pode fornecer sugestões de busca, OCR e transcrição. Não decide se uma informação é verdadeira ou falsa. A concordância de dois modelos de linguagem também não decide isso.
- A política `2026-10-03.1` usa afirmações literais, não paráfrases inventadas. Preserva negação, valores, datas, acentos e pontuação interna.
- Corroborar/refutar exige duas famílias editoriais distintas da lista explícita em `claim_policy.py`, URLs HTTPS válidas, data de checagem não futura, recuperação pelo Google Fact Check e avaliação explícita de verdadeiro/falso para a mesma afirmação.
- Sites da mesma família não contam como dois votos. Avaliações mistas/ambíguas não são convertidas em falso. Discordância, contexto temporal relativo, perguntas/citações e partes sem cobertura impedem um veredito global conclusivo.
- O relatório mostra afirmações, classificações atribuídas, publicadores, datas, links e motivos para excluir checagens. Notícias relacionadas não são tratadas como confirmação.
- `False` é um rótulo novo, separado de `AI_Generated` e `Manipulated`. Padrões financeiros suspeitos continuam sendo alertas de possível golpe, não prova da identidade do remetente ou da falsidade de cada frase.

**Custo da regra conservadora:** checagens com redação diferente, apenas um publicador, falta de data ou informação inédita podem continuar inconclusivas. Isso não significa que o texto seja falso. Fontes podem errar ou ficar desatualizadas; correspondência exata não resolve todo contexto. Esta não é uma máquina universal de verdade.

### Imagem, áudio e vídeo

- Arquivos são decodificados a partir dos bytes. Nome, extensão, MIME declarado e EXIF não determinam autenticidade.
- Imagem: detectores configurados, camada facial Hive separada, OCR, metadados, C2PA e contexto. Conteúdo do OCR tem checagem factual separada.
- Áudio: transcrição Gemini com alternativa AssemblyAI, Hive de áudio e integração opt-in Sightengine `ai_speech`. Transcrição de um pedido de Pix não prova clonagem. Hive preserva segmentos; sua pontuação agregada é o máximo observado, não uma probabilidade de toda a gravação.
- Vídeo: até nove quadros por padrão, distribuídos conforme a duração (máximo configurável entre 3 e 12). A faixa de áudio é extraída e analisada em paralelo quando existe. A checagem exige concordância **no mesmo quadro**, não médias de momentos distintos.
- Corrigida a extração no final de vídeos curtos/de baixo FPS. Tempos mostrados são pontos de busca/amostragem, não uma perícia temporal quadro a quadro.
- Falha, acesso negado, quota, resposta malformada e ausência de classe válida diminuem cobertura; nunca viram sinal positivo ou pontuação zero inventada. Uma tarefa Hive parcial não fornece consenso completo.
- Dois sinais altos concordantes indicam possível IA/manipulação; ausência de sinais não certifica uma mídia humana. Limiares `.8/.2` são experimentais, não calibrados neste projeto.

Não há garantia de identidade, detector dedicado de lip-sync ou análise de todos os quadros. C2PA precisa de ferramenta e âncoras de confiança instaladas; marcador binário não é assinatura validada.

## Como configurar as chaves no Railway

Não cole credenciais no chat, README ou frontend. Use o projeto Railway → **serviço da API/backend** → ambiente de produção → **Variables**. Não coloque chaves em `VITE_*` ou no serviço PostgreSQL. Alterar variáveis/publicar pode reiniciar o serviço: revise o conjunto antes de aplicar.

Na consulta somente de nomes realizada nesta revisão, estavam cadastrados `GOOGLE_FACT_CHECK_KEY`, `GEMINI_API_KEY`, `HIVE_API_KEY`, as duas variáveis Sightengine, `HUGGINGFACE_API_TOKEN`, `ASSEMBLYAI_API_KEY` e `SERPERAPI_KEY`. **Valores estavam ocultos:** não confirmei se estavam preenchidos, válidos ou com saldo. Não estavam registrados os nomes específicos Hive de imagem/áudio, o opt-in de áudio Sightengine, o endpoint HF e o modelo Gemini explícito. A chave facial Hive é uma configuração nova desta revisão; sua presença atual no Railway não foi consultada.

| Prioridade / serviço | Onde obter e verificar | Variáveis da API |
| --- | --- | --- |
| Checagens factuais | [Ativar Fact Check Tools no Google Cloud](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com) → [Credenciais](https://console.cloud.google.com/apis/credentials) | `GOOGLE_FACT_CHECK_KEY` |
| OCR, transcrição e voz de demonstração | [Google AI Studio — chaves](https://aistudio.google.com/app/apikey) · [Modelos disponíveis](https://ai.google.dev/gemini-api/docs/models) | `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `GEMINI_TTS_MODEL` |
| Imagem / manipulação facial | [Sightengine — painel](https://dashboard.sightengine.com/) | `SIGHTENGINE_API_USER`, `SIGHTENGINE_API_SECRET` |
| Hive por modelo | [Hive — portal](https://portal.thehive.ai/) | `HIVE_IMAGE_API_KEY`, `HIVE_DEEPFAKE_API_KEY`, `HIVE_AUDIO_API_KEY` |
| Segundo detector de voz | [Sightengine — detecção de fala sintética](https://sightengine.com/docs/ai-generated-speech-detection) | Credenciais Sightengine + `SIGHTENGINE_AUDIO_ENABLED=true` **somente com acesso autorizado ao modelo** |
| Detector de imagem adicional | [Hugging Face — tokens](https://huggingface.co/settings/tokens) · [Endpoints](https://endpoints.huggingface.co/) | `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_IMAGE_API_URL`, `HUGGINGFACE_AI_LABEL` |
| Transcrição alternativa | [AssemblyAI — painel](https://www.assemblyai.com/dashboard/) | `ASSEMBLYAI_API_KEY` |
| Notícias relacionadas | [Serper](https://serper.dev/) | `SERPERAPI_KEY` |

Passos importantes:

1. Google Cloud: selecione o projeto, habilite Fact Check Tools API e configure uma chave restrita a essa API. A chave Gemini não é automaticamente uma configuração funcional do Fact Check. A consulta é de checagens existentes, não uma análise universal de fatos. [Guia oficial](https://developers.google.com/fact-check/tools/api).
2. Hive: crie/selecione projetos **v2** dos modelos de imagem gerada por IA, manipulação facial e áudio. Copie cada chave para sua variável correspondente. O código usa `/api/v2/task/sync`; chave de outro modelo/versão não é intercambiável. A chave legada `HIVE_API_KEY` não habilita todos os modelos. A camada facial nova não usa fallback legado, nem conta duas chamadas Hive como dois detectores independentes. [Áudio](https://docs.thehive.ai/reference/ai-generated-audio-detection-1).
3. Sightengine: valide os modelos de imagem habilitados. Detecção `ai_speech` tem acesso enterprise/parceiro; **ter chave de imagem não basta**. Sem autorização, mantenha o opt-in desligado. Não contrate um plano sem verificar acesso e preço com o fornecedor.
4. Hugging Face: token não cria hospedagem. Configure somente um endpoint oficial HTTPS de um detector de imagem realmente disponível e testado. Confirme a classe positiva exata em `HUGGINGFACE_AI_LABEL`; `not_ai_generated` não é uma classe positiva. O código não escolhe mais um modelo possivelmente indisponível por padrão. [Contrato de classificação](https://huggingface.co/docs/inference-providers/tasks/image-classification) · [Teste de endpoint](https://huggingface.co/docs/inference-endpoints/en/guides/test_endpoint).
5. Gemini: escolha modelos disponíveis na sua conta; quotas de texto/visão e TTS podem diferir. Erro 429 ou falta de modelo continua sendo indisponibilidade, sem beep apresentado como voz. AssemblyAI é alternativa de **transcrição**, não detector de clonagem. [AssemblyAI — início](https://www.assemblyai.com/docs/pre-recorded-audio/getting-started/transcribe-an-audio-file).

Nenhuma assinatura, chave nova ou alteração de variáveis de produção foi realizada pelo agente. Não é necessário contratar todos os serviços, mas um único detector não atende ao critério de concordância desta política. Verifique limites financeiros e regras de retenção antes de enviar arquivos de usuários a fornecedores.

### Diagnóstico sem expor chaves

Depois de publicar esta revisão, `GET /api/capabilities` informa presença de configuração, opt-in de áudio e disponibilidade local de FFmpeg/ffprobe/ExifTool/c2patool. Não realiza chamadas pagas e nunca devolve os valores das chaves. `operational_status: not_tested` significa exatamente que credencial, acesso e quota ainda não foram testados. `/health` é apenas liveness.

HTTP 403 → investigar autorização/chave/projeto; 429 → quota/limite; `invalid_response` → contrato/classe/modelo incompatível. Nada disso significa que o arquivo seja falso. Não publique logs com headers, cookies, chaves ou conteúdos privados.

## Verificações realizadas e pendências

- Suíte funcional isolada: decisões verdade/falso com respostas controladas, negação/datas/entidades, famílias duplicadas, divergência, falha de API, contratos Hive/HF/Sightengine, áudio e vídeo reais de controle, autenticação e segurança. As contagens finais estão no README.
- [25 controles HTTP locais finais](audit-verifications-local-2026-10-03.json): 24 respostas esperadas + invariância do áudio ao renomear. APIs externas desligadas; contas/histórico somente no banco descartável.
- Interface: testes de explicações/fontes/animação e build. No navegador, fluxo de texto → API → relatório inconclusivo sem chave, sem erros de console; tela mobile de 390 px sem transbordamento horizontal.
- [Relatório mobile registrado](report-two-axes-mobile.jpg). A imagem comprova apresentação, não veracidade do conteúdo.
- [Relatório final registrado](report-two-axes-2026-10-03.jpg), política `2026-10-03.1`, com console sem erros no fluxo local de texto.
- O teste real de provedores em [audit-providers-2026-10-02.json](audit-providers-2026-10-02.json) é anterior a esta etapa; **não foi repetido** e não valida as novas integrações. Nenhuma chamada paga foi feita nesta etapa.

Ainda necessários: confirmar chaves/modelos/entitlements e créditos, executar controles reais autorizados, testar migração do enum `FALSE` em PostgreSQL de staging, publicar e repetir fluxos em produção. Docker, gateway WhatsApp/número real, detector acústico novo e credenciais C2PA não foram certificados em produção. Formatação do PDF ainda pode ganhar a mesma apresentação detalhada dos dois eixos da interface.

### Atualização: preparação do commit/push autorizado

A suíte foi repetida: 137 testes + 66 subtestes no SQLite e no PostgreSQL 16 descartável, 15 testes frontend e build aprovados. Um controle PostgreSQL separado simulou o enum antigo, executou a atualização duas vezes e persistiu/leu `FALSE`. Isto reduz o risco da migração, mas não é teste de staging com os dados reais. Os testes de consultas corrigiram compartilhamento de conexão entre event loops e gravação de usuário antes do histórico; nenhuma alteração no pool de produção foi necessária.

O Dockerfile da raiz também instala FFmpeg/ExifTool; `.dockerignore` de ambos os contextos exclui segredos/cache/bancos, e `PORT` é respeitado nos dois comandos. A imagem da raiz compilou e confirmou ferramentas/importação da API. Em HTTP local dentro do Docker, saúde, bloqueio de URL privada, rejeição de arquivos inválidos, imagem, vídeo, áudio, lote/texto e simulador responderam como esperado; nome falso não mudou a análise do mesmo áudio. O lote atingiu o limite de requisições ao chegar ao PDF (429): isso é proteção de admissão, não conclusão da análise. Em chamada separada do próprio contêiner, o PDF retornou HTTP 200 e bytes `%PDF` válidos. Provedores externos continuaram desligados.

Antes do push, Railway ainda apontava para o commit de setembro, com quatro mudanças pendentes e valores ocultos. A conexão Vercel respondeu 403 ao consultar os deploys desse projeto. O site público carregou a versão anterior; o domínio público Railway não pôde ser resolvido deste ambiente. Não é evidência suficiente para declarar a API fora do ar nem para certificar produção. Confira os passos no [guia de configuração](CONFIGURACAO-PRODUCAO.md).

## Como medir precisão de verdade, sem esconder inconclusivos

Foi adicionado `backend/scripts/evaluate_predictions.py`. Ele **não gera rótulos nem executa modelos**: calcula métricas das predições e rótulos que você fornece. Sem conjunto real independente, não há precisão medida para divulgar.

Arquivo JSONL: um objeto por linha, com `id`, `modality` (`text/url/image/audio/video`), `dimension` (`veracity/authenticity`), `split` (`calibration/test`), `expected` (`positive/negative`), `predicted` (`positive/negative/inconclusive`) e `ground_truth_source` documentada.

```json
{"id":"controle-ficticio-001","modality":"audio","dimension":"authenticity","split":"test","expected":"positive","predicted":"inconclusive","ground_truth_source":"EXEMPLO DE FORMATO: substituir por procedência independente real"}
```

Esse exemplo **não é benchmark real**. `positive` significa afirmação refutada em veracidade ou mídia sintética/manipulada em origem. Não classifique uma imagem como falsa só porque foi gerada por IA; registre a dimensão correta. Media sem procedência confiável não recebe rótulo inventado.

```bash
PYTHONPATH=backend python backend/scripts/evaluate_predictions.py /caminho/rotulos.jsonl
```

Saída: grupos separados por modalidade/dimensão/split, matriz de confusão com abstinências, cobertura, precisão, recall efetivo, falsos positivos/negativos e taxa de inconclusivos. Ausência de denominador resulta em `null`, não precisão de 100%. Métricas não imprimem arquivos, mensagens ou fontes privadas.

Monte amostras autorizadas de captura real, imagem sintética, montagem, face-swap, voz humana, TTS/clonagem consentida e vídeo com áudio; inclua compressão WhatsApp, reedição, ruído e casos difíceis. Separe pessoas, eventos e geradores entre calibração e teste; não ajuste os limiares no conjunto de teste. Registre procedência/licença, versões e hashes; um beep ou imagem obviamente artificial serve para testar transporte/decodificação, não precisão de clonagem/deepfake.

Prioridade posterior: corpus independente e calibração antes de novos detectores; trabalho assíncrono/fila para análises longas, limites compartilhados por réplicas, retenção/exclusão e auditoria de dependências. Serviços adicionais não garantem resultados corretos por si só.
