# Roteiro básico para apresentar o Verify à banca

Preparado em **07/10/2026**. Duração: **8–12 minutos**, mais perguntas. Este roteiro não certifica o deploy nem garante acerto de todas as APIs. Referências: [arquitetura](general.md), [matriz de controles](MATRIZ-VALIDACAO-30-CASOS.md), [diagnóstico real de 07/10](FECHAMENTO-2026-10-07.md), [retomada de transcrição](TRANSCRICAO-PENDENTE-2026-10-07.md) e [plano de fechamento](ENTREGA-ATE-11-OUTUBRO.md).

## Objetivo da apresentação

Atualização de 08/10: conferir o [status das verificações e configuração](STATUS-VERIFICACOES-2026-10-08.md) e a [revisão candidata](ENTREGA-BANCA-2026-10-08.md) antes do ensaio. A guarda local de reenvio após renovação de sessão foi corrigida; isso não homologa todas as corridas de cookies nem a produção.

Mostrar três coisas: uma pessoa leiga consegue enviar conteúdo; o relatório explica os sinais e suas limitações; o sistema não inventa certeza quando faltam evidências. **Resultado correto não significa sempre “verdadeiro” ou “falso”.** Uma abstenção por falta de cobertura é comportamento seguro, mas não deve ser contada como acerto de classificação de uma imagem IA conhecida.

Não apresentar pedido financeiro fictício como golpe consumado. Não apresentar foto publicada como autenticada por câmera. Não apresentar voz sintética de demonstração como clonagem de pessoa real.

## Preparar antes do dia

Faça um ensaio completo na mesma versão, domínio, navegador e computador usados na apresentação. Registre data, revisão/commit, tempo e saída de cada caso. A versão do código local pode não ser a que está publicada.

- [ ] Identificar **commit do frontend e do backend** apresentados; não presumir que push já significa deploy atualizado.
- [ ] Abrir a aplicação e verificar conexão com backend. `/health` é vida do processo; `/ready` verifica conexão com banco. Nenhum deles homologa APIs.
- [ ] Conferir as modalidades autorizadas e créditos no painel dos provedores, sem compartilhar tela de chaves. `/api/capabilities` mostra configuração, não saldo, permissão ou precisão.
- [ ] Escolher perfil **publicado com integrações reais** ou **local com fornecedores desativados** e dizer isso à banca. Não alternar silenciosamente para um mock.
- [ ] Ensaiar cada caso selecionado pela interface, preservar a saída real e anotar falhas/inconclusivos. Não ajustar limiares para os exemplos escolhidos.
- [ ] Usar uma única sessão de apresentação, sem trocar de conta durante análises. Testes de corrida de sessão e homologação do candidato devem ser fechados antes de promovê-lo; a limitação não deve ser ocultada.
- [ ] Não usar conta pessoal com histórico privado; se demonstrar histórico, usar somente conta de teste e conteúdo fictício já preparado. Cadastro e troca de contas não são necessários no roteiro principal.
- [ ] Testar Modo Fácil, fonte ampliada, navegação por teclado e movimento reduzido no computador da banca. Preferir texto grande e zoom legível; animação não substitui a explicação.
- [ ] Se demonstrar PDF, **baixar, salvar e abrir** o arquivo no ensaio. PDF/200 não comprova que o navegador salvou; não anunciar essa fronteira validada sem o teste.
- [ ] Deixar os arquivos abaixo acessíveis no seletor de upload e manter seus manifestos de procedência. Não renomear para nomes que anunciem um suposto veredito.
- [ ] Levar este roteiro e capturas de contingência. Marcar toda captura como **registro de ensaio**, nunca resultado ao vivo.

### Orçamento do ensaio e da banca

Um clique pode consultar vários serviços; vídeo pode consultar detectores para vários quadros. Estabeleça teto antes do ensaio, conte também falhas e nunca repita apenas para obter a cor desejada.

- Hive é pago por uso. A autorização anterior de **até US$ 0,01** era um smoke limitado, não autorização permanente. Mantê-lo pausado; novo teste precisa de orçamento autorizado. Não adicionar cartão, recarga ou habilitar modalidades públicas.
- AssemblyAI e Sightengine: usar somente créditos gratuitos confirmados, sem cobrança automática. Verifique saldo e acesso a cada modalidade no dia; chave de imagem não habilita detector de voz.
- OpenRouter: manter somente modelos gratuitos e restrição de preço zero. Falta de disponibilidade gratuita não autoriza fallback pago.
- Gemini: registrar limite de chamadas do novo ensaio; HTTP 503 não é resolvido por cliques repetidos. Aumentar espera só dentro do prazo configurado, sem aguardar indefinidamente.
- Se não houver saldo/modalidade autorizada, mostrar a camada indisponível e fazer o roteiro local de triagem/OCR. Isso deve ser declarado, não vendido como integração remota validada.

## Casos preparados e expectativas honestas

Os caminhos são relativos à raiz do repositório. Os arquivos já existem nesta revisão; textos podem ser copiados literalmente.

| Caso | Entrada | O que conferir | O que não prometer |
| --- | --- | --- | --- |
| A — pedido financeiro fictício | `Pague uma taxa para liberar seu Pix.` | Triagem local encontra pedido de taxa; alerta de sinais de golpe, trecho e orientação. Veracidade factual continua não comprovada. | Fraude consumada, identidade do remetente ou investigação bancária. |
| B — aviso negado | `Não pague uma taxa para liberar seu Pix.` | O pedido negado não recebe o mesmo alerta de golpe; sem checagens correspondentes, informação continua não determinada. | “Verdadeiro” só por não ter encontrado padrão de golpe. |
| C — leitura da imagem | `backend/tests/fixtures/validation/ocr/impresso-base.png` | OCR → conferência humana; preservar `Nao`, `R$ 123,45` e `03/10/2026`. Controle local já executado pela interface. | Gráfico impresso ser fotografia, documento real ou prova de veracidade. |
| D — foto publicada | `backend/tests/fixtures/validation/internet-real-2026-10-07/nasa-zinnia-iss046e009018.jpg` | Procedência NASA documentada; mostrar cobertura, sinais e limitações. Sem cobertura suficiente, inconclusivo é permitido. | EXIF/Photoshop provar montagem, ou sinal baixo provar autenticidade. |
| E — imagem gerada | `backend/tests/fixtures/validation/generated-2026-10-07/ai-plant-windowsill.png` | Origem IA conhecida pela geração documentada; comparar sinais dos detectores com essa origem, sem forçar decisão final. | Um score alto isolado garantir detecção ou informação falsa. |
| F — fala sintética, opcional | `frontend/public/audio/demo-conversa-sintetica.wav` | Escutar, comparar texto literalmente, mostrar transcrição separada da origem da voz. | Voz humana, clonagem ou identidade por conteúdo cotidiano. |
| G — vídeo técnico, opcional | `backend/tests/fixtures/synthetic-cafe.mp4` | Decodificação, quadros amostrados e ausência de faixa de áudio no controle; explicar cobertura parcial. | Face-swap, lip-sync ou perícia temporal completa. |

Casos A/B têm controles de regra e interface descritos na matriz. C foi ensaiado com OCR local e provedores externos desativados. D/E tiveram observações exploratórias de detector, com decisão final inconclusiva por cobertura insuficiente. **Ensaiar novamente no candidato não equivale a refazer um benchmark independente.**

Referências de procedência: [OCR](../backend/tests/fixtures/validation/ocr/manifest.json), [fotografias publicadas](../backend/tests/fixtures/validation/internet-real-2026-10-07/README.md), [imagem IA](../backend/tests/fixtures/validation/generated-2026-10-07/README.md), [áudios/vídeos sintéticos](../backend/tests/fixtures/README.md).

Não usar `voz_humana_real.mp3` ou `voz_golpe_clonado.mp3` como rótulos: nomes antigos não comprovam procedência. As gravações humanas autorizadas e os vídeos próprios ainda precisam ser enviados e avaliados; arquivos sintéticos não substituem essa etapa.

## Roteiro de 8–12 minutos

### 0:00–1:00 — problema e proposta

Abra a landing, apresente o objetivo e entre na tela de verificação, `/app`.

Fala sugerida:

> “Mensagens falsas e pedidos suspeitos chegam todos os dias, principalmente pelo WhatsApp. O Verify reúne leitura do conteúdo, busca de evidências e sinais de possíveis manipulações em um relatório simples. Ele ajuda a decidir o próximo passo, mas não substitui checar a fonte nem garante 100% de acerto.”

Mostre Modo Fácil por alguns segundos. Diga que a interface foi pensada também para idosos e pessoas leigas: texto legível, poucas ações e orientação de segurança.

### 1:00–3:00 — pedido Pix e importância da negação

1. Na aba **Texto**, cole o caso A e execute uma vez.
2. Leia o trecho encontrado e o alerta: pedido de taxa para liberar Pix.
3. Abra a explicação do relatório: **sinal de possível golpe**, não prova de remetente criminoso. Orientação cadastrada não é uma checagem factual realizada naquele momento.
4. Volte à entrada, cole o caso B e execute uma vez.
5. Compare os resultados. O “Não” muda o sentido e precisa ser preservado. Ausência de alerta não autoriza dizer “100% verdadeiro”.

Fala sugerida:

> “Aqui a aplicação encontrou um padrão de risco e mostrou exatamente onde. Agora eu troco o pedido por um aviso: ‘Não pague’. Ela deve respeitar a negação. Isso demonstra a diferença entre triagem de risco e comprovação factual.”

Aceite do ensaio: A apresenta o padrão; B não acusa o pedido negado; nenhuma das duas frases ganha certeza factual inventada. Se falhar, registrar a divergência — não modificar o resultado na apresentação.

### 3:00–5:00 — imagem com texto e conferência humana

1. Na aba **Imagem**, envie o caso C.
2. Na conferência, compare imagem e leitura, principalmente as três partes críticas:

```text
CONTROLE DE TESTE
Nao pague taxa para liberar seu Pix.
Valor: R$ 123,45
Data: 03/10/2026
```

3. Marque a confirmação somente após conferir. Se editar, diga **o que foi editado**; preserve a leitura original e não esconda erro de OCR.
4. Solicite a checagem do texto conferido. Mostre que a análise da mensagem e a análise da origem da imagem são dimensões diferentes.

Fala sugerida:

> “Antes de pesquisar a mensagem, eu confiro o que foi lido. Se o sistema perder um ‘não’, trocar o valor ou a data, a pergunta passa a ser outra. A conferência humana evita esse erro. A leitura correta da imagem, sozinha, não torna o conteúdo verdadeiro.”

Se o ensaio usar OCR local, diga isso. Não atribuir sucesso do Tesseract ao Gemini. O diagnóstico de 07/10 registrou falhas 503 em Gemini OCR/inspeção; texto mínimo funcionando não valida essas modalidades.

### 5:00–7:30 — foto publicada versus imagem IA

Só fazer uploads D/E ao vivo se ambos estiverem ensaiados, com tempo e orçamento compatíveis. Caso contrário, exibir os dois arquivos e seus registros de procedência, sem fingir nova análise.

1. Mostre a imagem D e o registro NASA. Explique que é uma fotografia publicada, com processamento editorial conhecido — não um RAW autenticado.
2. Mostre E e o registro de geração por IA. A origem deste controle é conhecida; ela não deve ser escondida para parecer uma foto humana.
3. Se executar análises reais, abra as camadas do relatório: quais serviços responderam, quais falharam e qual foi a conclusão permitida pela política.
4. Se aparecer inconclusivo, explique **cobertura insuficiente**. Um único detector com sinal alto não vira certeza; dois nomes de modelos do mesmo fornecedor não representam duas fontes independentes.

Fala sugerida:

> “Estes arquivos têm procedências diferentes e documentadas. Os detectores retornam sinais, que podem errar. O sistema separa esses sinais da conclusão e pode se abster quando falta cobertura. Imagem feita por IA também não significa automaticamente que toda informação associada a ela seja falsa.”

Não chamar a abstenção do caso E de acerto de detecção. Diga: “a procedência é conhecida, mas a análise automática não conseguiu concluir com a cobertura disponível”.

### 7:30–9:00 — áudio OU vídeo, somente se houver ensaio

Escolha um, não todos. Se o tempo estiver curto ou a integração ainda não estiver homologada, pule para o fechamento.

**Áudio F:** declare geração offline por eSpeak, sem imitar pessoa real. Reproduza e compare com a referência:

> “Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.”

Mostre conferência da fala e estado dos detectores de origem. Se houver pendência, leia o aviso. Não clicar repetidamente: a retomada ASR é limitada à mesma conta/aba/arquivo e uma janela por processo; não protege todas as APIs ou reinícios. Não confirmar fidelidade de texto enquanto não houver fala correspondente.

**Vídeo G:** declare construção programática a partir de uma imagem IA. Mostre que o sistema analisa quadros amostrados e trata áudio separadamente; este arquivo não demonstra voz clonada nem face-swap. Não usar vídeo técnico como substituto de vídeos humanos autorizados.

### 9:00–10:00 — relatório, PDF e fechamento

Mostre no relatório: evidência, fonte/procedência, limitações e próximo passo. Indicador animado é um índice de sinais/decisão conforme a semântica do relatório, **não porcentagem calibrada de verdade ou acerto**. Inconclusivos não recebem número inventado.

Se PDF tiver passado no ensaio, baixe e abra o resultado atual: ele deve conservar conteúdo e limitações, sem nova análise da mídia. Caso contrário, diga que o salvamento no navegador ainda está sendo homologado.

Fala sugerida:

> “O principal resultado é a explicação: o que foi encontrado, de onde veio a evidência, o que não foi possível verificar e como agir com segurança. A proposta é apoiar a pessoa, não fazer ela confiar cegamente em uma cor ou em um modelo.”

Use os minutos finais para perguntas. O roteiro de 8 minutos encerra após as imagens; o de 12 inclui um controle de áudio/vídeo e perguntas.

## E se a banca pedir “mostre um verdadeiro e um falso”?

Explique a diferença entre **origem da mídia**, **veracidade da afirmação** e **sinal de golpe**. Não trocar o significado só para obter verde/vermelho.

A política factual exige checagens correspondentes da mesma afirmação, com contexto/data e famílias editoriais distintas. Nos controles reais registrados, algumas consultas retornaram sem correspondência e ficaram não determinadas. **Ainda não há, neste roteiro, um par real homologado de afirmação corroborada/refutada pela recuperação efetiva de duas famílias.** Não prometer esse par antes de ensaiá-lo e revisar as fontes.

Para adicioná-lo depois:

1. Escolher duas afirmações públicas sem dados pessoais nem aconselhamento médico/financeiro, já avaliadas por fontes editoriais independentes.
2. Preservar a frase exata, negação, valor, data e contexto; não transformar notícia atual em afirmação absoluta sem data.
3. Executar pela aplicação e conferir os artigos realmente recuperados, autoria, avaliação explícita e correspondência. Duas URLs da mesma família não contam como independência.
4. Registrar a saída, revisão e tempo, incluindo abstenção. Só apresentar como caso homologado se tiver evidência real suficiente; não criar reviews fictícias para a API real “acertar”.

Testes offline já mostram decisões corroboradas/refutadas com fontes **simuladas**. Se a banca quiser ver a regra, apresente o teste como simulação técnica com esse rótulo visível. Isso valida comportamento da política, não comprova uma notícia do mundo real nem acesso ao Google Fact Check.

## Plano de falha — sem esconder o problema

| Situação | Ação na apresentação | Explicação curta |
| --- | --- | --- |
| Internet/backend indisponível | Usar capturas identificadas, dizer data e perfil do ensaio. Não simular um upload live. | “Este é um registro anterior; agora a conexão não respondeu.” |
| Gemini 503, quota ou timeout | Mostrar a falha no relatório; OCR local só se disponível. Não repetir para forçar sucesso. | “A camada externa falhou; isso reduz cobertura, não torna o conteúdo falso.” |
| ASR pendente ou estado incerto | Mostrar o aviso; avançar no roteiro. Não reenvio automático/manual repetido nem marcar fidelidade inexistente. | “O processamento não foi concluído ou confirmado; ainda não há leitura utilizável.” |
| Detector sem crédito/acesso à modalidade | Manter desabilitado/inconclusivo, sem contratação ou fallback pago. | “A chave existe, mas essa operação não está autorizada/disponível.” |
| OCR/ASR perde negação, valor ou data | Comparar com referência; corrigir explicitamente ou não confirmar a leitura. | “A conferência humana existe justamente para evitar analisar uma frase diferente.” |
| Resultado inesperado no controle | Registrar o caso e as camadas; não trocar de arquivo silenciosamente. | “Este é um limite/erro observado, que precisa entrar na avaliação.” |
| Espera ultrapassa o tempo do roteiro | Depois de cerca de 45 s, explicar o estado e seguir para evidência preparada; não dizer que uma operação foi cancelada no provedor. | “Vou seguir com o registro do ensaio para não gastar o tempo da apresentação.” |

Capturas existentes, sempre com rótulo **“Ensaio de 07/10/2026 — não é consulta ao vivo”**:

- [OCR local e conferência](evidencias-2026-10-07/ui-local-ocr-review.jpg): upload/conferência local, fornecedores externos desativados.
- [Gemini indisponível](evidencias-2026-10-07/ui-gemini-unavailable.jpg): ensaio com respostas reais 503; não sucesso multimodal.
- [ASR pendente em Modo Fácil](evidencias-2026-10-07/ui-asr-pending-easy.png): **transporte simulado**, não transcrição real.
- [Retomada ASR no editor](evidencias-2026-10-07/ui-asr-resumed-review.png): frase fornecida pelo mock, entrada era um tom; **não** é reconhecimento de fala. Não marcar confirmação nem apresentá-la como prova de fidelidade.

## Perguntas prováveis e respostas curtas

**“Todas as verificações funcionam?”**

“Não estão todas homologadas em produção. Triagem, OCR local e fluxos têm controles; disponibilidade remota e precisão são avaliadas por modalidade. O relatório informa falta de cobertura, em vez de inventar um veredito.”

**“Por que não dizer verdadeiro quando o detector não acha IA?”**

“Ausência de sinal não autentica a mídia, e autenticidade da mídia não prova uma afirmação. Para checagem factual, precisamos de fontes correspondentes.”

**“Por que usar Gemini e OpenRouter?”**

“Ajudam na leitura e extração literal para pesquisa. Não votam como prova de verdade ou autenticidade. Sucesso de texto não comprova visão ou áudio.”

**“A voz foi clonada?”**

“Transcrição só informa o conteúdo da fala. Estes áudios são sintéticos declarados; não imitam pessoa real. Clonagem e identidade precisam de avaliação própria, ainda sem homologação completa.”

**“Quantos testes passaram?”**

“O registro da etapa ASR de 07/10 tem 424 testes backend, 124 frontend e build aprovado. São regressões de comportamento, muitos com mocks, não 548 acertos de detecção. A execução PostgreSQL repete a suíte e tem só três integrações reais; não duplicamos a contagem. Se o candidato mudar, apresentamos as contagens da execução nova.”

**“O projeto está 100% pronto?”**

“Está sendo fechado com critérios verificáveis. Ainda precisamos homologar modalidades indisponíveis, gravações humanas/vídeos autorizados, candidato publicado, sessões, persistência e operação. Nenhum detector garante 100% de acerto.”

## Registro simples do último ensaio

Preencher antes de apresentar; deixar campos ausentes como **não verificado**, nunca como aprovado.

| Campo | Preenchimento |
| --- | --- |
| Data/hora, navegador/computador | A preencher |
| URL/perfil: live, local sem fornecedores ou simulado | A preencher |
| Commit frontend / backend e deploy correspondente | A preencher |
| Casos escolhidos e hashes/manifestos | A preencher |
| Serviços/modalidades autorizadas e teto de chamadas/gasto | A preencher, sem segredos |
| Saída/tempo de cada caso e camadas indisponíveis | A preencher |
| Conferência de negação/valor/data | A preencher |
| PDF salvo e aberto / Modo Fácil / teclado | A preencher |
| Falhas, abstenções, limites a mencionar à banca | A preencher |

Durante a apresentação, usar somente conteúdo fictício, público autorizado ou próprio com consentimento para envio aos fornecedores. Não abrir `.env`, dashboards com secrets, dados pessoais, rostos reais ou documentos privados na tela compartilhada.
