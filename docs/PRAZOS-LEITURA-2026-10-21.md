# Vereditos, leitura e prazos — 21/10/2026

## Resultado real, sem retirar inconclusivos

Doze controles públicos conhecidos, seis verdadeiros e seis falsos, uma tentativa por entrada: **8/12 acertos (66,7%), 4/12 inconclusivos (33,3%), zero conclusões erradas e zero erros terminais observados**. Verdadeiros: 4/6; falsos: 4/6. Mediana de processamento: 21,938 s; mínimo 9,697 s, máximo 66,342 s.

A meta de 80% **ainda não foi atingida**: seriam necessários dez acertos neste conjunto. Não é amostra cega, independente ou representativa de qualquer notícia. Precisão apenas entre os oito conclusivos não substitui acerto sobre os doze; inconclusivos permanecem no denominador.

| Controle | Esperado | Resultado |
| --- | --- | --- |
| Elizabeth II, data verdadeira | Verdadeiro | Correto |
| Elizabeth II, data falsa | Falso | Correto |
| Colisão intencional DART | Verdadeiro | Inconclusivo |
| Classificação da pandemia pela OMS | Verdadeiro | Correto |
| Divulgação anual do PIB pelo IBGE | Verdadeiro | Inconclusivo |
| Decisão falsa de Selic/Copom | Falso | Correto |
| Temperatura abaixo da média, Copernicus | Falso | Correto |
| Negação do artigo da Lei Áurea | Falso | Correto |
| Lançamento do James Webb | Verdadeiro | Correto |
| Promulgação da Constituição | Verdadeiro | Correto |
| Brasil campeão mundial de 2014 | Falso | Inconclusivo |
| Data falsa de lançamento Artemis I | Falso | Inconclusivo |

[Dados sanitizados completos](validation-waits-typed-2026-10-21.json). A rodada imediatamente anterior, também preservada, obteve [2/12 acertos, 16,7%](RECUPERACAO-PRINCIPAL-2026-10-20.md). Não se misturam resultados de versões diferentes nem se escolhe somente a melhor execução histórica.

## O que mudou

### Prazos finitos e coerentes

- Comparação final: padrão **90 segundos compartilhados** entre Gemini e uma alternativa OpenRouter, não 90 segundos para cada um. Configuração aceita 10–90; a primária recebe parte do prazo para deixar margem à alternativa.
- OpenRouter na comparação estruturada: até **4.096 tokens e 45 segundos**, sempre dentro do restante do prazo compartilhado. Auxiliares de extração/OCR continuam pedindo até 2.048 tokens e usando 25 segundos. Preço máximo zero e modelos gratuitos permanecem obrigatórios.
- Interface: até **seis minutos** em análise textual, link, lote, texto conferido e mídia. Autenticação mantém 60 segundos; PDF, 30 segundos. Não há reenvio automático de uploads/análises.
- Vídeo: extração sequencial dos quadros pode usar até **90 segundos no total**, mantendo até 15 segundos por execução FFmpeg. Cancelamento/expiração encerra e recolhe o processo; nenhum detector inicia depois de extração cancelada.
- Hive conserva 45 segundos totais/50 segundos externos; ASR conserva checkpoints e limites existentes. HTTP 503, resposta inválida e tarefa pendente continuam distintos de timeout.

Aumentar o prazo não torna um JSON inválido válido, não cria saldo, não elimina quota e não transforma um sinal isolado em prova.

### Preservar a cota para a leitura útil

Uma entrada inteira com uma única frase literal de até 500 caracteres já serve como consulta. Nesse caso, a etapa auxiliar de extração não chama Gemini/OpenRouter. A frase inteira, com negações, datas e valores, permanece intacta; não se inventam resumos ou alegações.

Cobertura registra `not_requested` com motivo `literal_single_sentence_no_extra_extraction`, não falha de configuração. Entradas múltiplas/longas mantêm a extração anterior. Esse auxílio não produz veredito nem substitui a comparação das fontes.

### Comparação direta delimitada, sem opinião de modelo

Construções completas de comunicado formal do Copom, lançamento de missão numerada e título de competição podem ter seus trechos comparados por regras literais delimitadas. **Não há tabela de respostas dos testes nem nomes/datas de controle embutidos.**

O servidor percorre todas as afirmações, fontes e passagens selecionadas, testa apoio e contradição e aplica novamente as mesmas guardas de contexto, identidade, data, valor, procedência e janela. Leitura desconhecida que ainda poderia ser admissível volta ao comparador de modelos para a matriz inteira; não é ignorada para obter conclusão. Conflito dentro de uma fonte permanece conflito.

A matriz usa o mesmo contrato JSON estrito e os mesmos IDs de citações do servidor. Só depois de decodificada recebe cobertura `literal_typed_rules_v1`. Gemini/OpenRouter ficam honestamente `not_requested` nessa etapa. As regras não dispensam famílias independentes nem ampliam o caso já delimitado de registro institucional original.

Nesta rodada, o Copom foi refutado nesse caminho a partir do comunicado original. Os outros sete acertos vieram da comparação assistida de documentos: um por Gemini Lite e seis pelo fallback explícito Gemini 3.8. Dois modelos concordarem não é critério factual.

## Perfil real e fronteiras observadas

Código congelado SHA-256: `87dc81c080b689b89437c93cc1c4d169369073bcb7a20120493cb3895c757170`, 127 arquivos de aplicação. Manifesto de entradas: `47397f9ffa4022db414d2b85614efd70bdbfe3db4510b221d3d67bcb16625e04`.

Gemini primário `gemini-3.1-flash-lite`, alternativa explicitamente configurada `gemini-3.8-flash` para indisponibilidade, dentro do mesmo prazo. OpenRouter `openrouter/free`; máximo dez novos envios, preservando trinta anteriores conhecidos conservadoramente. Uma chamada OpenRouter foi reservada, sem resposta completa; não foi contada como sucesso. Não houve HTTP 402/429 na rodada. Nenhum grounding/plugin pago foi habilitado.

Uma notícia (Elizabeth II verdadeira) foi submetida pelo **formulário**, com relatório final observado; os onze controles seguintes foram submissões HTTP ordinárias. Todos os doze pedidos responderam HTTP 200, JSON, `no-store`. Isso não equivale a doze testes pelo formulário, nem a homologação de links, mídia, PDF ou produção.

Transportes: Gemini 21 tentativas (12 HTTP 200, oito 503, uma incompleta); OpenRouter uma incompleta; Fact Check 12 HTTP 200; buscas 53 HTTP 200; leitura pública 79 tentativas. HTTP 200 do modelo não significa automaticamente citação válida; o decoder e as guardas continuam obrigatórios.

**1.177 testes backend passaram, zero skips, sem rede ou credenciais. Os 22 arquivos de testes frontend e a compilação passaram.** Regressões automatizadas não entram na taxa de acerto factual.

## Configuração para aplicar depois dos testes

No backend local privado ou Railway, manter as chaves existentes e usar, se desejar o perfil desta rodada:

```dotenv
SOURCE_CROSSCHECK_ENABLED=true
SOURCE_CROSSCHECK_PRIMARY_PROVIDER=gemini
SOURCE_CROSSCHECK_TIMEOUT_SECONDS=90
GEMINI_MODEL_NAME=gemini-3.1-flash-lite
GEMINI_FALLBACK_MODELS=gemini-3.8-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=90
OPENROUTER_MODEL=openrouter/free
HUGGINGFACE_ENABLED=false
```

Não copiar banco, JWT/HMAC ou origens locais para produção. O fallback explícito não serve para contornar HTTP 429; não alterna chaves nem cria créditos. Chaves são necessárias, mas não garantem acesso, saldo, modelo disponível ou acerto. Esta revisão não alterou o `.env` privado nem implantou configuração no Railway/Vercel.

## O que falta para chegar aos 80%

1. Revalidar online a separação de legenda já corrigida: numa página real de PIB, a chamada “pode comprometer” foi fundida à notícia e bloqueou leitura como incerteza. O replay offline voltou a encontrar evidência no corpo, mas ainda não substitui uma nova rodada completa.
2. Recuperar evidência completa para DART: algumas fontes apresentam data e intenção em trechos distintos; outras não mencionam intenção. Não inferir intencionalidade só pelo nome da missão ou por uma colisão.
3. Melhorar a recuperação de trechos completos de vencedor/edição/categoria e lançamento concluído para Copa/Artemis, preservando duas famílias. Mais buscas sozinhas não resolvem frases incompletas.
4. Depois das correções, repetir o conjunto inteiro, com código congelado e uma tentativa por caso; acrescentar conjunto independente antes de alegar precisão geral.

## Mídias e orçamento separado

Nova autorização de 21/10: até US$ 0,05 do saldo Hive existente, no máximo duas imagens e um áudio de até cinco segundos. Reservas persistentes anteriores ao envio, sem recarga, assinatura ou repetição paga. Os três controles foram enviados pelo formulário, receberam HTTP 200/JSON/no-store e tiveram o relatório observado. Depois da voz, “Ver só sinais da mídia” abriu o resultado sem novo envio.

| Controle | Observado | Limite da conclusão |
| --- | --- | --- |
| Foto pública NASA de planta | Hive 0,0125% e Sightengine 0,1% de sinal de IA; sem indícios fortes | Origem continua não determinada; não certifica foto autêntica |
| Planta com geração por IA documentada | Hive aproximadamente 100% e Sightengine 99% de sinal; indícios concordantes de IA | Não comprova falsidade da informação retratada |
| Voz eSpeak conhecida, cinco segundos | Hive 99,08% de sinal; transcrição AssemblyAI disponível | Sinal isolado; não confirma clonagem, identidade ou origem; não é veredito factual |

Esses números são saídas dos detectores, **não porcentagens de acerto nem probabilidades calibradas**. A transcrição teve expressão suspeita (“pixu da gente”); fidelidade de fala, negações, valores e datas não foi homologada. Manteve-se a etapa de conferência, sem correção automática silenciosa.

Gemini conseguiu inspecionar a foto e devolver `no_text` na imagem de IA, mas OCR da foto e inspeção da imagem de IA receberam HTTP 503. Isso não foi convertido em falsidade nem sucesso. Hugging Face e Sightengine de voz permaneceram desabilitados. Vídeo não recebeu novo upload real nesta rodada; foi exercido nos testes de regressão de prazo/cancelamento. Não foram testadas pessoas reais, clonagem de identidade, lip-sync ou autenticidade de câmera.

Consumo reservado: **duas imagens e um áudio/cinco segundos**, três POST Hive, todos HTTP 200, sem reenvio. Valor efetivamente faturado e saldo não foram consultados; a estimativa baseada nas [taxas públicas do modelo Hive](https://thehive.ai/models/hive/ai-generated-and-deepfake-content-detection) é US$ 0,02589, não recibo de cobrança. [Dados sanitizados e procedência](validation-media-2026-10-21.json). Esses controles pequenos e reutilizados não integram a precisão textual nem permitem publicar precisão geral de mídia.

## Correções posteriores à medição

A apresentação passou a distinguir extração auxiliar intencionalmente dispensada de consulta ausente: somente o status/motivo exato da frase literal deixa de produzir aviso falso de cobertura perdida. Notícias não pesquisadas, serviço sem chave, timeout e outras falhas continuam avisados; nenhum veredito é alterado. O aviso de espera agora diz “A análise pode levar até seis minutos”, também adequado a imagem/voz/vídeo.

Essas alterações são posteriores ao snapshot medido acima; não constituem nova porcentagem de acerto.

O leitor HTML também passou a remover somente parágrafos de legenda identificados simultaneamente por classe exata, contêiner próprio de legenda e ancestral explícito de player/`VideoObject`. Não elimina palavras de incerteza, outros filhos do player, legendas genéricas, texto inline ou blocos de citação/contexto. Links exclusivos dessas legendas deixam de ser referências editoriais. Texto simples não é interpretado como HTML.

Treze controles novos cobrem esses limites. No replay **sem rede** da mesma página pública de PIB, duas legendas deixaram de contaminar o corpo: zero→uma família elegível na página isolada, com data de publicação e texto factual preservados. Isso não é uma segunda família fabricada nem um novo veredito online.

**Verificação final após as correções: 1.190 testes backend passaram, zero skips/HTTP inesperado, 22 arquivos de testes frontend passaram e build concluído.** A taxa factual de 8/12 continua exclusivamente vinculada ao snapshot anterior registrado, sem atualizar o número com replay offline.
