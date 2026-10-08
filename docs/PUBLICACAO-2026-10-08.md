# Verify — publicação e controles públicos de 08/10/2026

Registro de evidências em **8 de outubro de 2026**, horário de Brasília (UTC−3). Preserva o checkpoint da base e o desenvolvimento posterior; a publicação final do código está confirmada na seção 7. Commits posteriores exclusivos de documentação não alteram o código ensaiado. Não contém chaves, cookies, tokens de relatório, mensagens privadas ou parâmetros SQL.

## 1. Revisão publicada

SHA confirmado nas duas plataformas:

```text
ef9655ff9d3fa4d350d149cc5b48e44b3611b729
```

| Plataforma | Deployment | Estado observado | Momento registrado |
| --- | --- | --- | --- |
| Railway/backend `verify` | `a0e0d2b0-fbf9-4473-9350-eae24d9be5b7` | SUCCESS | 08/10, 16:24:40Z / 13:24:40 Brasília |
| Vercel/frontend | `dpl_J5zdpkUjexfSMs8xsWTMi7GN9sDm` | READY | Criação 16:24:06,142Z; READY 16:24:17,859Z / 13:24:17,859 Brasília |

Interface testada: [verifybr.vercel.app](https://verifybr.vercel.app). API pública: [Verify no Railway](https://verify-production-ead7.up.railway.app).

SUCCESS/READY e igualdade de SHA comprovam a revisão observada, não garantem disponibilidade futura ou acerto das análises. O SHA antigo `5db970d…` e os incidentes de validação/data anteriores permanecem no [diagnóstico de produção](CORRECOES-PRODUCAO-2026-10-08.md).

O usuário confirmou aplicação/deploy destas variáveis no Railway: Lite principal/mídia, timeout 60 s, HF desligado, Hive v3 para imagem/áudio, reservas 20 imagens e 60 segundos, três quadros de vídeo. Esse relato não revela valores secretos. Respostas reais Hive nas imagens/voz são evidência de operação nesses controles; presença de variável sozinha não seria prova.

Nenhum dado de produção foi apagado nem banco substituído pelos ensaios descartáveis. Nenhum cartão, recarga ou novo endpoint pago foi provisionado nesta rodada.

## 2. Regressões associadas

- Revisão publicada: **482 backend, 155 frontend, build da interface e três jobs CI aprovados**. [Execução GitHub Actions do candidato](https://github.com/rodriguesz9/verify/actions/runs/37762904667), [execução de master no mesmo SHA](https://github.com/rodriguesz9/verify/actions/runs/37808481312).
- Testes backend isolam credenciais e bloqueiam HTTP real; não medem disponibilidade ou precisão de fornecedores.
- PostgreSQL descartável: mesmo runner com 482 aprovados; **quatro são integração real PostgreSQL**, demais usam mocks/SQLite. Duas execuções da mesma suíte não são 964 cenários independentes.
- Primeiro checkpoint posterior de notícias: **490 backend offline aprovados, zero skips**, incluindo oito testes de relevância. Com dois testes adicionais de extração curta, a revisão local final passou **492 backend em 9,087 s e 156 frontend em 598,515 ms**, zero skips; build Vite concluído em 3,74 s. Contagem frontend detalhada obtida com `node --test --experimental-test-isolation=none tests/*.test.js`; `npm test` também passou (18 arquivos de teste no reporter local). Não faz parte do SHA ef9655ff nem tem publicação comprovada neste checkpoint.
- Teste funcional, resposta 200 ou dois detectores concordando não constituem evidência científica de acurácia universal.

## 3. Controles pela interface publicada

As durações abaixo correspondem à requisição observada no navegador, não ao tempo de cada fornecedor isolado.

| Controle | Fronteira HTTP | Resultado público | Cobertura observada |
| --- | --- | --- | --- |
| Texto preventivo: “Não pague taxa para liberar seu Pix. Confirme pelo canal oficial.” | `/api/check-text` 200, 5,704 s | Inconclusivo: ausência de checagens correspondentes; negação preservada, sem transformar prevenção em golpe comprovado | OpenRouter e Serper responderam; Google Fact Check sem resultados |
| Planta conhecida gerada por IA | `/api/upload` 200, 40,745 s | Indícios de geração por IA | Sightengine 99,0%, Hive 100,0% arredondados; Gemini visão respondeu; leitura sem texto; HF desativado |
| Foto NASA zinnia | `/api/upload` 200, 5,320 s | Inconclusivo, não “foto certificada autêntica” | Sightengine IA 0,1%, Hive 0,0% arredondados; Gemini visão respondeu; OCR retornou somente “A”, não usado para checagem factual |
| Voz sintética eSpeak NG, 6,859456 s | `/api/upload` 200, 2,774 s | Origem da voz não determinada; leitura disponível para conferência | Hive respondeu com sinal 97,4% arredondado; transcrição respondeu; Sightengine voz não habilitado |
| PDF da planta IA | `/api/verificar/relatorio-pdf` 200, 25 ms | PDF preparado pelo servidor a partir do relatório original | Sem nova análise/reenvio aos detectores; salvamento/abertura do arquivo não confirmados |

### Origem dos controles

- Planta IA: [`ai-plant-windowsill.png`](../backend/tests/fixtures/validation/generated-2026-10-07/ai-plant-windowsill.png), gerada previamente com IA; [procedência declarada](../backend/tests/fixtures/validation/generated-2026-10-07/README.md).
- Foto: [`nasa-zinnia-iss046e009018.jpg`](../backend/tests/fixtures/validation/internet-real-2026-10-07/nasa-zinnia-iss046e009018.jpg); [manifesto de fonte/limites](../backend/tests/fixtures/validation/internet-real-2026-10-07/README.md). Procedência de publicação não comprova que todos os pixels são originais, nem autentica legendas posteriores.
- Voz: [`demo-conversa-sintetica.wav`](../frontend/public/audio/demo-conversa-sintetica.wav), eSpeak NG, deliberadamente sintética. Não é gravação humana nem controle de clonagem de pessoa identificável.
- Texto é um controle fictício/preventivo, sem dados pessoais ou necessidade de veredito conclusivo.

Pontuações acima são **sinais não calibrados**. “100,0%” é arredondamento do retorno, não 100% de certeza. `hive_deepfake` compartilha a chamada Hive de imagem; não deve ser contado como terceiro fornecedor independente. Zero sinal de IA/manipulação nunca certifica câmera, identidade ou autenticidade.

O fragmento “A” não permite avaliar fidelidade do OCR nem checar uma afirmação. Não foi descartado ou corrigido automaticamente; não concluir alucinação apenas por seu tamanho. O gate de dez caracteres impediu consulta factual e emissão de token de conferência para esse fragmento. O Modo Fácil foi ativado e restaurado no relatório de voz; a visão simples manteve as informações de fornecedor fechadas. A tentativa de viewport 390×844 não se refletiu no navegador (DOM/screenshot continuaram em 1280), portanto **não conta como homologação móvel**.

### Voz: fronteira observada

Resposta de upload às 16:41:58,789Z / 13:41:58,789 Brasília. A UI primeiro pediu conferência da transcrição:

> Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.

Foi escolhida **“Ver só sinais da mídia”**. Não foi disparada nova checagem factual; o relatório preservou a separação entre leitura, origem da voz e verdade do discurso. O rótulo observado mostra transcrição disponível, mas não identifica AssemblyAI versus Gemini: este registro não atribui o reconhecimento a um deles.

Hive foi o único detector de origem da voz disponível. O relatório permaneceu **origem da voz não determinada**: resposta de um detector nesta amostra não certifica gravação real/sintética para qualquer voz. Sightengine `ai_speech` não foi habilitado automaticamente nem homologado; chave de imagem/“AI Music Detection” não libera detector de fala. [Ativação e limites](ATIVACAO-HIVE-VOZ-2026-10-08.md).

## 4. Problema encontrado no contexto e melhoria posterior

Embora o controle de texto tenha preservado a negação e ficado inconclusivo, a busca de contexto retornou notícias de cassino/apostas/dívidas sem correspondência pertinente suficiente. Essas notícias não participaram dos votos factuais, mas prejudicavam a clareza do relatório.

Patch local posterior, **ainda não publicado neste checkpoint**:

- Política `literal_context_anchors_v1` aplicada apenas a notícias Serper, antes de relatório, métricas temporais, persistência e PDF.
- Exige duas âncoras lexicais não genéricas na mesma frase literal original. Extração/paráfrase do LLM e domínio do publicador não autorizam aceitação.
- Negação explicitamente divergente ou números/datas explícitos incompatíveis não são apresentados como correspondência. Não inventa quantidades omitidas pelo snippet.
- Limita a inspeção a 15 resultados deduplicados, preserva consultas/estados e contagens brutas, deduplicadas, excluídas e não processadas.
- Busca válida com nenhuma notícia admitida recebe `no_results`, distinta de consulta indisponível. Ausência de contexto não prova falsidade.
- Não filtra Google Fact Check, não altera avaliações, famílias editoriais, limiares ou votos de verdade/falsidade. Notícia lexicalmente relacionada continua somente contexto.
- Nenhuma lista subjetiva de domínios, nova dependência, chave, serviço ou chamada paga foi adicionada.

Testes: notícias de cassino que só mencionam “Pix” e dívidas com “pague/canal oficial” são excluídas; orientação “Não existe taxa para liberar Pix” é admitida. Regressões incluem português/acentos, negação, valores/datas, limites, preservação de fact-checks e distinção de consulta vazia/erro. Oito testes novos passaram; suíte local total 490.

**Limitação deliberada:** regras lexicais podem excluir sinônimos, refutações que usem negação diferente e resumos numericamente incompletos. Âncoras iguais não demonstram equivalência semântica. O filtro melhora pertinência aparente, não precisão científica; publicação e nova observação da interface ainda precisam ser confirmadas por SHA.

### Fragmentos curtos de leitura

Melhoria posterior no mesmo candidato: OCR literal como “A”, “NASA”, “42”, “R$ 5”, “123,45” ou “Não” permanece disponível para comparação. O relatório explica que o fragmento é curto demais para checar uma afirmação; não o chama automaticamente de alucinação e não descarta labels reais. Texto vazio, menor que dez caracteres e maior que 5000 recebem motivos distintos. Não alteramos reconhecimento, limiares, provedores ou limites da conferência. Regressões asseguram ausência de consulta factual e de token de conferência nos fragmentos curtos; a observação pública preserva caracteres Unicode.

## 5. Consumo autorizado, sem garantia financeira global

Somente saldo Hive já existente foi autorizado. Estimativa nominal desta rodada pública: duas imagens até US$ 0,012 e voz de 6,859456 s até aproximadamente US$ 0,01945; **total menor que US$ 0,032**. Não houve consulta de saldo/fatura real; erro/timeout poderia ser processado remotamente e não provar ausência de consumo. Controles diagnósticos anteriores possuem registros e estimativas separados, não incluídos neste total público.

As reservas `HIVE_V3_IMAGE_REQUEST_LIMIT=20` e `HIVE_V3_AUDIO_SECONDS_LIMIT=60` são contadores em memória **por processo**. Reinício renova contadores; múltiplas réplicas têm contadores próprios. Não são orçamento diário, teto global em dólares nem consulta de saldo. Guardas contam reserva antes do envio e não devolvem crédito presumido em erro. Vídeo usa imagens/quadros e pode usar áudio; três quadros diminuem custo/cobertura, não certificam o vídeo completo.

Hugging Face permanece desativado. Sightengine voz não foi ativado, nenhum endpoint pago novo foi criado e nenhuma recarga automática foi autorizada.

## 6. Fronteiras ainda pendentes

1. **Concluído posteriormente na seção 7:** publicar/retestar patch lexical, conferir SHA/CI e notícias na interface. Permanecem pendentes os itens seguintes; não homologar precisão por esse único controle.
2. Link público autorizado com escrita/histórico no PostgreSQL publicado; login/refresh/troca de conta, isolamento e privacidade completos em produção.
3. PDF: capturar download, abrir o arquivo e verificar conteúdo/layout/páginas. HTTP 200 sozinho não encerra essa fronteira.
4. Voz humana portuguesa autorizada com negação, valores/data; controles de gravação real e síntese/clonagem independente. Só habilitar segundo detector se houver acesso gratuito/crédito expressamente autorizado.
5. Vídeos humanos autorizados sem fala e com voz fora do quadro; apresentar separadamente quadros/voz/transcrição. Não prometer lip-sync, identidade ou cobertura de todos os quadros.
6. Corpus independente representativo e benchmark com falsos positivos/negativos e inconclusivos incluídos. Dois exemplos ensaiados não demonstram taxa de acerto.
7. Retenção/exclusão de dados, recuperação e governança operacional conforme [fechamento até 11/10](ENTREGA-ATE-11-OUTUBRO.md).

Para a banca: [roteiro](ROTEIRO-BANCA.md). Mostrar os resultados reais, incluindo inconclusivos, sem escolher ou alterar rótulo esperado. “Respondeu” não significa “certeiro”; transcrição não é detector de clonagem, e origem de uma mídia não é veracidade de sua legenda.

## 7. Publicação da revisão posterior e rechecagem

Código `cba8d3f77cb60ae1906ab1ccb292c77f6f3e7b40`, enviado ao candidato e promovido por fast-forward a master, sem substituir alterações pendentes da cópia original. [CI do candidato](https://github.com/rodriguesz9/verify/actions/runs/37812069733) e [CI de master](https://github.com/rodriguesz9/verify/actions/runs/37812326226): três jobs SUCCESS, frontend/build e backend SQLite/PostgreSQL descartável. Testes locais da revisão: 492 backend e 156 frontend, sem skips, build concluído. Não somar execuções da mesma suíte como cenários independentes.

| Plataforma | Deployment da revisão | Estado confirmado | Momento |
| --- | --- | --- | --- |
| Railway | `17cef0ed-56e3-4cc1-bf0a-fe008c7bf935` | SUCCESS, SHA cba8d3f | 16:54:31,745Z / 13:54:31,745 Brasília |
| Vercel | `dpl_CM3kQKw7miAgaexyViNCP3oFrVzh` | READY, SHA cba8d3f | 16:53:55,974Z / 13:53:55,974 Brasília |

Após carregar o frontend novo, a mesma mensagem preventiva foi enviada **uma única vez**: `/api/check-text` HTTP 200, **4,924 s**, em 16:55:03,502Z / 13:55:03,502 Brasília. A UI preservou as duas frases literais, manteve veracidade inconclusiva sem checagens correspondentes e não mostrou as notícias de cassino/dívidas. Cobertura: OpenRouter respondeu; Google Fact Check consulta sem resultados; Serper consulta concluída sem notícias com correspondência lexical utilizável. Ausência de contexto não foi apresentada como erro, verdade ou falsidade. As contagens internas brutas/excluídas não foram exibidas nessa visão e não foram presumidas.

A orientação de OCR curto foi verificada por testes automatizados e publicada no mesmo código; não houve outro upload pago só para repetir a foto. Os controles de imagem/voz/PDF da seção 3 pertencem à base ef9655ff, não são novas chamadas no cba8d3f. A rechecagem textual não usa Hive. Nenhuma compra, recarga, troca de chave ou ativação de Sightengine voz/HF foi feita.

O relatório/documentação não declara o projeto “100% certeiro”. Arquivos humanos autorizados podem ser colocados em `/mnt/externo/IMPORTANTES/mostra/arquivos-para-validacao/` (subpastas `audios`, `videos`, `fotos`), conforme o [guia de envio privado](ENTREGA-ATE-11-OUTUBRO.md); não são enviados ou commitados automaticamente. Precisão independente, fluxo autenticado completo e download local de PDF continuam pendentes.
