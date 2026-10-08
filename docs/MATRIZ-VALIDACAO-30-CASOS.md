# Verify - matriz de validação de 30 casos

Preparada e executada parcialmente em **04/10/2026**, para a entrega de 17/10. **22 controles têm execução registrada em pelo menos uma dimensão; 8 continuam pendentes. Isso NÃO significa 22 acertos de classificação nem todas as APIs homologadas.** Há falhas reais de transcrição e sinais errados de detector. Primeira bateria (20/10): [VALIDACAO-INTERFACE-2026-10-04.md](VALIDACAO-INTERFACE-2026-10-04.md). Continuação de OCR/HTML e controles auxiliares: [CONTROLES-EXTRACAO-2026-10-04.md](CONTROLES-EXTRACAO-2026-10-04.md).

São **30 controles de comportamento**, não 30 amostras independentes nem um benchmark de precisão: 10 texto/link, 6 OCR, 6 áudio, 4 imagem e 4 vídeo. Resultados anteriores permanecem nos documentos históricos; não foram copiados como aprovações desta rodada.

## 1. Dimensões e critérios

- **Veracidade factual:** corroborada/refutada apenas por evidência correspondente suficiente. Fonte ausente, irrelevante ou discordante não determina verdade ou falsidade.
- **Triagem de golpe:** identifica um padrão de pedido financeiro ou risco no discurso. Não prova fraude consumada, identidade falsa nem clonagem de voz.
- **Origem da mídia:** procedência sintética, captura conhecida ou edição convencional. Uma imagem IA não é automaticamente uma afirmação falsa; uma voz humana pode comunicar algo falso.
- **Extração:** OCR/transcrição devem preservar texto observável, especialmente negação, datas e valores. Extração insuficiente precisa ser identificada; não completar palavras por suposição.
- **Transporte/segurança:** decodificação, amostragem, indisponibilidade e bloqueio de endereço privado são controles técnicos, não acertos de veracidade ou deepfake.

Nos testes com **evidências simuladas**, a expectativa da política é determinística; as fontes fictícias não representam checagens editoriais realmente publicadas. Não visitar seus URLs nem apresentar suas avaliações como fatos do mundo real.

Nas **mídias de origem conhecida**, registrar separadamente: rótulo de procedência, resultado dos detectores e decisão permitida pela política. Um sintético conhecido que permaneça inconclusivo não virou acerto de detecção; é abstenção/cobertura insuficiente. Ausência de detector nunca autoriza declarar autenticidade. Também é falha tornar todos os testes de regra inconclusivos quando evidências simuladas suficientes exigem corroborar/refutar.

## 2. Inventário disponível

Disponibilidade abaixo confirma presença local e documentação de origem, **não execução dos 30 casos**. Os hashes identificam os bytes inventariados; não certificam autoria ou verdade.

| Código | Arquivo/receita existente | Origem documentada e limite |
|---|---|---|
| F-CAFE | `backend/tests/fixtures/synthetic-cafe.png` | Gerada por IA em 02/10; personagem fictícia. Positivo conhecido de origem sintética; não exemplo de fotografia humana ou face-swap. |
| F-CAFE-VIDEO | `backend/tests/fixtures/synthetic-cafe.mp4` | Sequência H.264 de 3 s criada a partir de F-CAFE. Mesmo grupo de origem; não vídeo produzido por modelo de vídeo, lip-sync ou manipulação facial. |
| F-SILENCIO | `backend/tests/fixtures/recorder-no-duration.webm` | 1 s de silêncio Opus/WebM criado por FFmpeg, sem duração no cabeçalho de streaming. Não é voz humana nem clonada. |
| F-TTS-CONVERSA | `frontend/public/audio/demo-conversa-sintetica.wav` | eSpeak NG, pt-br, velocidade 145; texto fictício de conversa. Sintético, sem imitar pessoa real. |
| F-TTS-PEDIDO | `frontend/public/audio/demo-pedido-sintetico.wav` | Mesmo gerador/configuração; pedido financeiro fictício. Sintético, não clonagem comprovada. |
| R-IMPRESSO | `backend/scripts/multimodal_probe.py`, função `printed_control()` e `OCR_LINES` | Receita disponível de PNG impresso por Pillow; arquivo de controle ainda precisa ser materializado para esta matriz. Não executar o probe remoto para gerar a imagem. |
| R-BLANK | `backend/tests/helpers.py`, função `valid_png()` | Receita disponível de PNG azul 32 x 32, sem texto e sem modelo generativo; não fotografia. Arquivo ainda precisa ser materializado. |
| R-FONTES | `backend/tests/test_claim_decisions.py`, funções `review()`/`pair()` | Afirmação e checagens **simuladas**, disponíveis no código; não pesquisa real no Google nem ground truth factual externo. |

Hashes SHA-256 dos cinco arquivos disponíveis:

| Código | SHA-256 |
|---|---|
| F-CAFE | `e73eb7f8d081bebbf528f83ede7f689c41433b0aed0c2a42ed7487d72dbf5ca3` |
| F-CAFE-VIDEO | `55475f1b0e562ab4b4bad2911936b7be749aef97ce4400bbb114c37ee3f45199` |
| F-SILENCIO | `6b3700925f4315450c93c93a3b7d5a35df0bdceb72478bfcfe7f6279b9b80ba9` |
| F-TTS-CONVERSA | `70d5fa877db6f0fd0ddaa75c3a838017479fc95242b4d56a0c2dfd9cdb6f72ec` |
| F-TTS-PEDIDO | `8deefe71c742c3c06f6c50cda552721767d70a872824933749b31192f36e6c7f` |

**Excluídos como rótulos de procedência:** `voz_humana_real.mp3` e `voz_golpe_clonado.mp3`, preservados em `frontend/public/audio/`. Seus nomes não comprovam origem; a documentação registra procedência não auditada. Não utilizá-los como exemplos de humano/clonado.

Os cinco PNGs de `backend/tests/fixtures/validation/ocr/` foram materializados; referências e hashes em seu `manifest.json`. Os demais arquivos marcados **A OBTER** continuam pendentes. Capturas próprias exigem registro de autor, data, consentimento/licença e autorização para envio aos serviços escolhidos. EXIF sozinho não substitui esse registro.

Continuação: HTML local em `validation/links/pagina-controle.html` e OCR05 em `validation/extended/impresso-degradado.jpg`, com parâmetros/hash do original em `validation/extended/manifest.json`. O vídeo `video-tts-auxiliar.mp4` testa áudio/quadros locais, fora dos 30 casos; **não substitui VID04 nem captura/voz humana**. A URL `example.test` do harness é resposta simulada, não página pública consultada.

## 3. Serviços e limites desta preparação

- **LOCAL-R:** política factual, regras de triagem, parser de HTML e transporte com respostas simuladas. Sem Google, LLM ou pesquisa remota.
- **LOCAL-OCR:** Pillow/Tesseract no serviço isolado, com chamadas remotas desativadas. Enviar pelo fluxo completo de upload pode acionar outras camadas; não fazê-lo sem revisar os serviços ativos.
- **LOCAL-M:** Pillow/FFmpeg/ffprobe e validação/amostragem local. Não comprova qualidade de detector.
- **ASR:** AssemblyAI somente em créditos gratuitos confirmados, com consentimento da gravação. Gemini é uma alternativa a medir separadamente; a falha histórica não deve ser escondida por sucesso de outro provedor.
- **IMG:** Sightengine, apenas se acesso e créditos gratuitos estiverem confirmados. HF continua experimental, sem voto. Hive pago permanece pausado; autorização pontual antiga não autoriza nova bateria paga.
- **FATOS-REAL:** Google Fact Check com recuperação registrada e revisão manual das fontes. Notícias/Serper e sugestões Gemini/OpenRouter não substituem checagens correspondentes. OpenRouter somente gratuito, sem fallback pago.

Este documento **não autoriza execução remota, habilitação de detector, geração de mídia, contratação, alteração de política ou deploy**. Serviços mencionados indicam dependências para uma rodada posterior. Primeiro executar controles isolados/offline; integrações reais precisam de orçamento/consentimento conferidos.

## 4. Texto/link - 10 casos

Base fictícia B: **“O município de Exemplo inaugurou a ponte em 2024”**. R-FONTES fornece datas válidas, famílias diferentes e origem de recuperação simulada. Manter esses dados claramente identificados como fixtures, jamais checagens reais.

| ID | Entrada/arquivo e disponibilidade | Dimensão e expectativa | Motivo/controle de origem | Serviço necessário | Status |
|---|---|---|---|---|---|
| TXT01 | B + `pair(rating="Verdadeiro")`; receita R-FONTES disponível. | Regra de veracidade: `supported`, rótulo `Authentic` no contrato textual; confiança numérica ausente. | Duas famílias diferentes, mesma frase/data/origem **simuladas**; não certifica a ponte fictícia nem mídia autêntica. Grupo F-PONTE. | LOCAL-R; nenhuma API. | APROVADO · regra simulada |
| TXT02 | B + `pair(rating="Falso")`; receita disponível. | Regra de veracidade: `refuted`/`False`, argumentos e duas fontes exibidos. | Fixture altera a avaliação das fontes; não é notícia falsa real descoberta. Mesmo F-PONTE, não amostra independente de TXT01. | LOCAL-R. | APROVADO · regra simulada |
| TXT03 | “O município de Exemplo não inaugurou a ponte em 2024”; fontes de B. Entrada literal pronta. | Regra de veracidade: `unverified`; fontes da frase afirmativa excluídas, sem remover “não”. | Negação muda a proposição. Não há ground truth factual externo desta narrativa. F-PONTE. | LOCAL-R. | APROVADO · regra simulada |
| TXT04 | B + duas reviews de `checamos.afp.com` e `factcheck.afp.com`; receita existente. | Regra de veracidade: `unverified`; uma família editorial não vira dois votos. | Transportes/domínios distintos não significam fontes independentes. F-PONTE. | LOCAL-R. | APROVADO · regra simulada |
| TXT05 | B + par “Verdadeiro” e review “Falso” de `fullfact.org`; receita existente. | Regra de veracidade: `conflicting` e inconclusiva, mostrando a discordância. | Todas as fontes são simuladas; maioria numérica não apaga uma discordância correspondente. F-PONTE. | LOCAL-R. | APROVADO · regra simulada |
| TXT06 | “O município de Exemplo inaugurou a ponte em 2025 e cobrou R$ 500”; reviews apenas de B. Entrada literal pronta. | Regra de veracidade: `unverified`; ano/valor adicionais preservados, sem equivalência por similaridade. | Data e valor não cobertos. F-PONTE; variante controlada, não nova afirmação real validada. | LOCAL-R. | APROVADO · regra simulada |
| TXT07 | “Não pague uma taxa para liberar seu Pix.” Entrada literal pronta. | Triagem: não sinalizar o pedido negado como golpe; veracidade `unverified` sem fontes. | Aviso de segurança fictício. Não deduzir veracidade da frase pela ausência de padrão. Grupo F-PIX. | LOCAL-R, regras de triagem; fontes desligadas/simuladas. | APROVADO · regra + UI/OpenRouter |
| TXT08 | “Pague uma taxa para liberar seu Pix.” Entrada literal pronta. | Triagem: sinal de possível golpe/`Scam` com trecho e orientação; veracidade continua sem comprovação. | Pedido financeiro fictício oposto a TXT07; não existe remetente ou fraude consumada neste controle. F-PIX. | LOCAL-R. | APROVADO · regra + UI local |
| LNK09 | `http://127.0.0.1:8000/health`; endereço de controle definido, sem arquivo. | Segurança de link: rejeição 400 antes de conexão/análise; não produzir resultado factual. | Endereço loopback deliberado. Não consultar a URL para medir este caso; validar o bloqueio isolado. | LOCAL-R, `public_fetch`, transporte observável/simulado. | APROVADO · bloqueio + UI |
| LNK10 | **MATERIALIZADO:** `validation/links/pagina-controle.html`, com texto: “CONTROLE FICTÍCIO. Não pague uma taxa para liberar seu Pix. Valor informado: R$ 123,45. Data informada: 03/10/2026.” URL HTTPS pública sob controle do projeto ainda pendente. | Extração/link: preservar negação, valor e data; sem fontes correspondentes, `unverified`. Separar texto principal de scripts/menu e texto oculto. | HTML fictício escrito para o teste. Resposta HTTP simulada; uso de URL pública será integração distinta, não aprovação automática. Grupo F-HTML. | LOCAL-R e UI com harness explícito, sem consulta pública. | APROVADO · extração offline + UI simulada; HTTPS público pendente |

**Lacuna factual importante:** TXT01/TXT02 exercitam decisões com fixtures. Duas afirmações reais foram enviadas pela UI: uma histórica verdadeira e um boato falso, ambos documentados no relatório da rodada. Google não trouxe checagens correspondentes; ambos permaneceram `unverified`. Isso é abstenção, NÃO acerto de classificação. Ainda faltam casos reais corroborados/refutados por fontes correspondentes efetivamente recuperadas e revisadas. Não fabricar reviews para declarar que a API real funcionou.

## 5. OCR - 6 casos

| ID | Entrada/arquivo e disponibilidade | Dimensão e expectativa | Motivo/controle de origem | Serviço necessário | Status |
|---|---|---|---|---|---|
| OCR01 | R-IMPRESSO disponível como receita; **MATERIALIZADO** `validation/ocr/impresso-base.png`. Quatro linhas: “CONTROLE DE TESTE”; “Nao pague taxa para liberar seu Pix.”; “Valor: R$ 123,45”; “Data: 03/10/2026”. | Extração: quatro linhas na ordem, “Nao”, valor e data preservados. Conteúdo sem cobertura factual não vira falso; aviso negado não vira pedido de golpe. | Renderização programática conhecida, não foto humana. Grupo F-IMPRESSO. | LOCAL-OCR; alternativas Gemini/OpenRouter apenas em rodada separada autorizada. | APROVADO · OCR local/Gemini + UI; OpenRouter bloqueado 429 |
| OCR02 | **DISPONÍVEL:** `validation/ocr/afirmativo.png`, mesma receita com “Pague uma taxa para liberar seu Pix.”; demais linhas iguais a OCR01. | Extração + triagem: frase afirmativa lida, possível pedido suspeito identificado; origem/verdade não determinadas pelo texto. | Variante de F-IMPRESSO; comparar com OCR01 sem contar dois documentos independentes. | LOCAL-OCR + LOCAL-R. | APROVADO · OCR local |
| OCR03 | **DISPONÍVEL:** `validation/ocr/numeros.png`: “R$ 1.000,00”; “R$ 10,00”; “Taxa: 10%”; “Taxa: 100%”. | Extração: valores distintos não normalizados para o mesmo número; não completar zeros ausentes. | Texto fictício renderizado, referência literal disponível. F-IMPRESSO, variante diagnóstica. | LOCAL-OCR. | APROVADO · OCR local |
| OCR04 | **DISPONÍVEL:** `validation/ocr/datas.png`: “Data: 03/10/2026”; “Outra data: 30/10/2026”. | Extração: distinguir as datas, sem confundi-las ou tratá-las como avaliações factuais. | Datas impressas de controle, não datas de captura inferidas. F-IMPRESSO. | LOCAL-OCR. | APROVADO · OCR local |
| OCR05 | **MATERIALIZADO:** `validation/extended/impresso-degradado.jpg`, derivado de OCR01: rotação 3,5°, contraste 0,20, JPEG 55. Parâmetros e hashes no manifest. | Extração difícil: preservar trechos legíveis ou informar insuficiência. Qualquer troca silenciosa de negação/data/valor é falha; não exigir transcrição inventada para preencher lacunas. | Transformação de F-IMPRESSO; não amostra independente. Referência continua a de OCR01. | LOCAL-OCR, upload e revisão pela UI; nenhum provedor remoto. | EXECUTADO · “Valor” → “valor”; trechos críticos preservados; revisão explícita na UI |
| OCR06 | R-BLANK disponível como receita; **MATERIALIZADO** `validation/ocr/sem-texto.png`. | Extração negativa: sem palavras inventadas; ausência de texto/insuficiência explícita. | PNG azul sem caracteres, criado por código. Grupo F-BLANK; não é prova de “voz/foto humana”. | LOCAL-OCR; chamadas remotas desligadas. | APROVADO · OCR local |

## 6. Áudio - 6 casos

| ID | Entrada/arquivo e disponibilidade | Dimensão e expectativa | Motivo/controle de origem | Serviço necessário | Status |
|---|---|---|---|---|---|
| AUD01 | **DISPONÍVEL:** F-TTS-CONVERSA. Referência: “Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.” | ASR: comparar com referência; não inserir pedido financeiro. Origem conhecida sintética, mas decisão do detector pode abster-se por cobertura; não chamá-la humana pelo conteúdo cotidiano. | eSpeak documentado; 16 palavras na normalização do controle existente. Grupo F-ESPEAK. Não clonagem. | LOCAL-M + ASR em rodada autorizada; detectores de origem não são requisito para transcrição. | APROVADO · ASR/TTS na UI; origem inconclusiva |
| AUD02 | **DISPONÍVEL:** F-TTS-PEDIDO. Referência: “Mãe, caí na rua e perdi meu celular. Faz um Pix urgente para o guincho, por favor.” | ASR + triagem: preservar pedido, identificar padrão financeiro quando extraído; não transformar o padrão em prova de clonagem/fraude. | Fala fictícia eSpeak. Mesmo gerador de AUD01, não cobertura de dois geradores independentes. F-ESPEAK. | LOCAL-M + ASR + regras locais; Hive/segundo detector de voz não habilitados aqui. | FALHOU · palavras críticas no ASR; triagem corrigida |
| AUD03 | **DISPONÍVEL:** F-SILENCIO WebM. | Decodificação/ausência de fala: aceitar container válido sem duração no cabeçalho; nenhuma palavra inventada nem chamada ASR após identificação local de quase silêncio. | FFmpeg criou silêncio; origem de voz e veracidade não se aplicam. Grupo F-SILENCIO. | LOCAL-M + proteção local de fala; nenhuma API necessária. | APROVADO · local/UI após correção WebM/silêncio |
| AUD04 | **A OBTER:** `validation/audio/humana-negacao-valores.wav`, gravação própria autorizada: “Não faça um Pix. O valor informado é cento e vinte e três reais e quarenta e cinco centavos. A data informada é três de outubro de dois mil e vinte e seis.” | ASR: negação, valor e data conferidos com roteiro; sem alerta de pedido financeiro por frase negada. Não exigir que a política certifique origem humana. | Captura direta com roteiro/consentimento, sem TTS ou filtro de voz; ground truth só após documentação. Grupo F-VOZ-01. | LOCAL-M + ASR autorizado. | PENDENTE |
| AUD05 | **A OBTER:** `validation/audio/humana-negacao-ruido.wav`, derivado de AUD04 com ruído e compressão documentados. | ASR difícil: texto crítico correto ou insuficiência identificada; não preencher fala inaudível. Medir degradação separada da qualidade do arquivo limpo. | Mesmo F-VOZ-01; não nova voz nem amostra independente. Ruído não prova clonagem. | LOCAL-M + ASR autorizado; referência AUD04. | PENDENTE |
| AUD06 | **A OBTER:** `validation/audio/humana-pedido-ficticio.wav`, gravação própria autorizada do roteiro exato de AUD02. | Triagem: padrão financeiro possível tanto em voz humana quanto TTS. Conteúdo suspeito não determina origem sintética nem identidade falsa. | Pessoa autorizada lendo ficção, não golpe real. Grupo F-VOZ-02; se for a mesma pessoa de AUD04, manter ambas no mesmo grupo de participante ao dividir corpus. | LOCAL-M + ASR autorizado + regras locais. | PENDENTE |

Registrar WER quando a referência puder ser alinhada; registrar também erros críticos de negação/valor/data, que WER baixo pode esconder. Silêncio não entra como “humano negativo” numa matriz de clonagem. Não há amostra de voz clonada com consentimento nesta seleção.

## 7. Imagem - 4 casos

| ID | Entrada/arquivo e disponibilidade | Dimensão e expectativa | Motivo/controle de origem | Serviço necessário | Status |
|---|---|---|---|---|---|
| IMG01 | **A OBTER:** `validation/image/foto-propria-original.jpg`, foto direta de objeto/planta, sem rosto/dados pessoais, original preservado. | Origem: controle de captura fotográfica conhecida; medir falsos sinais IA. Sem evidência suficiente, resultado inconclusivo é seguro, não certificado de foto autêntica. | Autor/data/hash e ausência de geração/edição declarados e documentados; EXIF sozinho não basta. Grupo F-FOTO-01. | LOCAL-M; IMG apenas após confirmar créditos gratuitos. | PENDENTE |
| IMG02 | **DISPONÍVEL:** F-CAFE. | Origem: rótulo sintético conhecido; registrar detecção, erro ou abstenção sem prometer reconhecimento. Veracidade da cena/afirmação não é inferida desse rótulo. | Geração fictícia registrada. Mesmo F-CAFE usado em VID01; não novo exemplo de face-swap. | LOCAL-M; IMG em rodada autorizada; HF sem voto. | EXECUTADO · abstenção; HF errou sinal sintético |
| IMG03 | R-IMPRESSO; **MATERIALIZADO** o mesmo arquivo de OCR01, sem gerar nova amostra. | Origem: gráfico renderizado sem modelo generativo; medir falso sinal de IA. Não tratá-lo como fotografia humana nem comparar sua dificuldade com fotos naturais. | Mesmo F-IMPRESSO de OCR01; um arquivo observado em duas dimensões. | LOCAL-M; IMG opcional autorizado. | EXECUTADO · falso sinal HF no gráfico |
| IMG04 | **A OBTER:** `validation/image/foto-propria-editada.jpg`, recorte/ajuste de brilho convencional de IMG01; parâmetros e original registrados. | Origem/edição: transformação conhecida, não face-swap nem IA. Não concluir manipulação facial por edição comum; divergência SHA-256 comprova somente bytes diferentes. | Derivado de F-FOTO-01, não amostra independente. Nenhuma alegação de cena falsa. | LOCAL-M; IMG opcional autorizado; comparação de hash local. | PENDENTE |

## 8. Vídeo - 4 casos

| ID | Entrada/arquivo e disponibilidade | Dimensão e expectativa | Motivo/controle de origem | Serviço necessário | Status |
|---|---|---|---|---|---|
| VID01 | **DISPONÍVEL:** F-CAFE-VIDEO. | Decodificação/amostragem: duração/quadros/tempos reais registrados. Conteúdo visual deriva de IA conhecida; não apresentá-lo como face-swap, lip-sync ou teste de vídeo generativo. | Mesmo F-CAFE de IMG02. Avaliação por quadro, sem extrapolar para todos os instantes. | LOCAL-M; IMG por quadros somente com orçamento autorizado. | EXECUTADO · transporte aprovado; detector não homologado |
| VID02 | **A OBTER:** `validation/video/captura-propria-original.mp4`, 10 s de objeto/planta em movimento de câmera, sem fala/rosto/dados pessoais. | Origem/amostragem: capture conhecida, quadros previstos e ausência de faixa de fala explicitados. Detector sem evidência não certifica todo vídeo como verdadeiro. | Gravação original própria, autor/data/hash registrados. Grupo F-VIDEO-01; sem ground truth factual de narrativa. | LOCAL-M; IMG opcional autorizado. | PENDENTE |
| VID03 | **A OBTER:** `validation/video/captura-propria-editada.mp4`, recorte/redimensionamento/compressão convencional de VID02, parâmetros registrados. | Edição/amostragem: decodificar e informar cobertura; não confundir edição comum com IA/face-swap. Comparar diferença de bytes sem certificado de falsidade. | Mesmo F-VIDEO-01; derivação, não nova amostra independente. | LOCAL-M; IMG opcional autorizado. | PENDENTE |
| VID04 | **A OBTER:** `validation/video/captura-propria-com-fala.mp4`, 10-30 s de objeto com voz autorizada fora de quadro: “Não faça um Pix. O valor é cento e vinte e três reais e quarenta e cinco centavos.” | Faixa de áudio + conteúdo: extrair/transcrever negação/valor; preservar separação entre origem visual, origem da voz e triagem. Quadros/áudio analisados não comprovam identidade ou sincronização labial. | Captura direta consentida, sem TTS/edição de voz, roteiro fictício. Grupo F-VIDEO-02; agrupar pelo participante se repetido nos áudios. | LOCAL-M + ASR autorizado; IMG opcional. | PENDENTE |

## 9. Registro necessário em cada execução futura

Para cada ID, anexar:

- Data, commit/versionamento, ambiente e configuração não secreta; modalidade, dimensão e grupo de origem.
- Arquivo/hash ou entrada literal; autor/gerador/roteiro, consentimento/licença, transformações e caminho do original.
- Tipo da execução: regra simulada, ferramenta local ou integração remota real. Serviços/modelos efetivos, cobertura, tempo e consumo confirmado, sem chaves/tokens/conteúdo privado em logs públicos.
- Expectativa, resultado observado, erro/inconclusivo e motivos; referência literal de OCR/ASR; fontes usadas e excluídas com razões. Não usar HTTP 200 como comprovação de acerto.
- Consistência entre resposta, tela, histórico e PDF quando disponíveis. PDF deve reutilizar resultado original, sem nova chamada de detector.
- Decisão final: aprovado naquele controle, falhou, bloqueado por arquivo/consentimento/serviço, ou absteve-se na classificação. Manter **PENDENTE** até haver evidência de execução.

## 10. Lacunas e ordem recomendada

1. Os PNGs, HTML e a variante degradada foram materializados e executados localmente. Obter URL HTTPS pública controlada e capturas próprias autorizadas: AUD04/05/06, IMG01/04, VID02/03/04 continuam pendentes.
2. Executar primeiro regras/extração isoladas, com provedores desligados. Depois conferir saldos/consentimentos e concentrar integrações reais numa rodada limitada, sem chamadas pagas automáticas.
3. Obter afirmações reais com checagens correspondentes, registrar URLs/datas/famílias e recuperação pelo Google. Fixtures TXT01/TXT02 não fecham essa lacuna.
4. Antes de anunciar precisão de deepfake: corpus independente mais amplo, com fotos naturais diversas, vários geradores, manipulação facial, vídeo generativo, lip-sync e clonagem consentida. Esses exemplos não estão disponíveis nesta matriz.
5. Separar participantes/eventos/originais/geradores entre calibração e teste. Recorte, ruído, compressão, MP4 derivado de PNG e repetição do arquivo em outra dimensão não aumentam artificialmente o número de originais independentes.
6. Não mudar limiares no mesmo conjunto e chamá-lo depois de avaliação independente. HF segue sem voto; ausência de recursos para segundo detector não é solucionada inventando autenticidade.

Não há número de precisão/calibração divulgado por esta matriz. Ela prepara homologação limitada e identifica o que falta; não promete que todas as APIs ou tipos de conteúdo já funcionam corretamente.

## Fontes internas examinadas

- [Procedência das fixtures](../backend/tests/fixtures/README.md).
- [Roteiros eSpeak](../backend/scripts/generate_demo_audio.sh) e [receita OCR/controles multimodais](../backend/scripts/multimodal_probe.py).
- [Fixtures de regras factuais](../backend/tests/test_claim_decisions.py), [receitas PNG/WAV](../backend/tests/helpers.py) e [regras de negação/extração](../backend/tests/test_multimodal_resilience.py).
- [Arquitetura e limites](general.md), [resultados históricos de mídia](MULTIMODAL-2026-10-03.md), [separação de dimensões e avaliação](VERIFICACOES-2026-10-03.md) e [plano de entrega](PLANO-ENTREGA-14-DIAS.md).
