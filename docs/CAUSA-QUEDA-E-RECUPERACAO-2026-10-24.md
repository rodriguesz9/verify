# Causa da queda e recuperação limitada — 24/10

Revisão após `9cfcbe8`, validada localmente. Não é nova medição de precisão nem confirmação de deploy.

## O que caiu, exatamente

Nos **mesmos doze textos**, o acerto caiu de 9/12 (75%) para 6/12 (50%). Quatro conclusões corretas viraram inconclusivas; um inconclusivo virou refutação correta. Os 30% são 6/20 após incluir oito novos textos, todos inconclusivos; comparar diretamente 75% com 30% mistura conjuntos diferentes.

[Auditoria sanitizada](diagnostic-decline-2026-10-24.json), [rodada de 75%](validation-bindings-2026-10-24.json), [rodada de 20](validation-research-gaps-2026-10-24.json).

| Caso | Antes → depois | Causa observada |
| --- | --- | --- |
| Elizabeth II, data verdadeira | Apoiada → inconclusiva | G1 permaneceu elegível, mas Agência Brasil não foi recuperada para completar cobertura |
| OMS, classificação de pandemia | Apoiada → inconclusiva | O pronunciamento formal não foi recuperado; restou página geral de uma família |
| Webb, lançamento | Apoiada → inconclusiva | Brasil Escola permaneceu elegível, mas faltou o corpo G1 que completava a cobertura |
| PIB | Apoiada → inconclusiva | Mesmas duas fontes elegíveis; Gemini 503 e OpenRouter 404 impediram comparação |
| Brasil campeão de 2014 | Inconclusiva → refutada | Novos corpos G1/BBC forneceram duas famílias com relação explícita |

As rotinas de leitura, relação factual e decisão eram idênticas entre os dois commits medidos; hashes dos quatro módulos constam na auditoria. Os snapshots comuns G1/Elizabeth, G1/PIB, CNN/PIB e Brasil Escola/Webb também preservavam as mesmas frases, papéis, título e URL. Não se comparou a data de consulta, que naturalmente mudou, nem se afirma igualdade de toda a resposta HTTP.

Isso localiza as perdas: três ocorreram na descoberta/cobertura e uma no transporte dos modelos, não porque uma nova regra final rejeitou os mesmos trechos. As consultas do planejador mudaram, inclusive após as pistas novas. Portanto não há teste controlado para separar completamente efeito do prompt e variação da busca pública; não se pode atribuir toda a queda apenas ao fornecedor externo ou afirmar que o código não contribuiu.

Os oito novos também expuseram um problema arquitetural anterior: identidade da norma, paráfrases e relações nem sempre atravessam o filtro anterior à IA. Isso continua pendente; esta revisão não remove a barreira de prova nem cadastra respostas dos exemplos.

## Correções implementadas

### Pesquisa compatível com o leitor

O planejador agora recebe capacidades explícitas: HTML/XHTML/texto estático, sem executar JavaScript ou extrair PDF. Arquivos de formato sabidamente indisponível deixam de receber IDs de leitura selecionáveis pelo modelo. A recuperação comum prioriza páginas potencialmente legíveis antes de PDFs, documentos Office, arquivos compactados e mídia, dentro dos mesmos limites de tentativas.

Extensão é apenas pista de descoberta, não prova de MIME. Um endereço terminado em `.pdf` continua podendo ser lido se não houver alternativa e retornar HTML real; o MIME, DNS, redirecionamentos e tamanho ainda são validados pelo fetcher. A URL submetida pelo usuário não é silenciosamente substituída. Tentativas anteriores, inclusive PDF rejeitado, continuam consumindo o orçamento e não são repetidas.

### Recuperar indisponibilidade transitória na comparação

A comparação pode fazer **uma única nova tentativa** após Gemini HTTP 503, com espera aleatória de 1–2 s e respeitando `Retry-After`. Se o servidor pede mais de 5 s, a indicação é inválida, ou falta tempo útil no prazo atual, a recuperação é abandonada. Não se inicia outro prazo integral.

Isso segue a recomendação de espera com backoff para 503 da [documentação oficial Gemini](https://ai.google.dev/gemini-api/docs/troubleshooting). Não se repete 429, autenticação/saldo, timeout ambíguo, JSON inválido ou resposta válida insuficiente. A operação preserva modelo, chave, prompt e schema. Cada envio físico reserva sua quota normal, incluindo falhas; não há reembolso, compra, troca de chave ou renovação de orçamento.

O escopo é somente a comparação documental. O cliente geral, OCR, voz e pesquisa mantêm a política anterior; configurações com fallback explícito de modelos também não recebem esse reenvio adicional, para não multiplicar tentativas. `SOURCE_CROSSCHECK_TRANSIENT_RETRY_ENABLED=false` desliga a recuperação; o padrão é `true` e está documentado no arquivo de exemplo. Nenhum segredo privado foi alterado.

### Erros identificáveis, sem expor respostas privadas

Gemini/OpenRouter passam a preservar código HTTP numérico e categoria fixa nos detalhes técnicos da comparação/pesquisa. Assim 503 pode ser distinguido de 404, em vez de ambos aparecerem apenas como indisponíveis. Corpo bruto, URL de chamada, cabeçalhos e credenciais não entram nessa informação.

HTTP 404 isolado não comprova chave inválida nem permite afirmar qual requisito da rota falhou. A [documentação OpenRouter](https://openrouter.ai/docs/api/reference/errors-and-debugging) descreve seu envelope de erros; esta revisão não relaxa schema, seleção de fontes ou preço máximo zero para contornar a falha.

## Verificação e limites

- 1.469 testes backend passaram, sem rede, credenciais ou skips; 21 novos controles nesta revisão.
- 22 arquivos de testes frontend passaram; build de produção concluído.
- Os testes incluem transportes HTTP simulados 503→200 e 503→404, duas reservas, mesmo payload/modelo, cancelamento durante espera, preservação do prazo, bloqueio após quota e dados privados ausentes do relatório.
- Leitura foi testada com MIME incompatível, extensão enganosa, PDF anterior sem reembolso, URL submetida e duas fontes HTML dentro do mesmo teto.
- Nenhuma chamada remota foi feita nesta revisão, de mídia ou de modelos. O orçamento OpenRouter anterior permanece 48/48, sem reset.

**Ainda não há nova porcentagem real.** Os 21 testes novos demonstram comportamento dos mecanismos, não acerto em notícias. A última medição remota permanece 50% nos 12 conhecidos e 0/8 nos novos. Precisão geral de 80% não foi demonstrada. A próxima rodada deve congelar esta revisão, manter as abstenções no denominador e usar também novos assuntos separados dos 20 já conhecidos.
