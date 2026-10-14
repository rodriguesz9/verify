# Verify — documentação completa e manual de entrega

**Adendo de 13/10:** [cruzamento fundamentado de fontes](CRUZAMENTO-FONTES-2026-10-13.md) complementa a decisão histórica exclusivamente por ClaimReview: documentos podem acrescentar apoio/refutação com citações validadas e cobertura suficiente, sem voto de IAs. [Retomada Railway](REATIVAR-RAILWAY-2026-10-13.md) documenta a hospedagem expirada e a configuração atual. Controles públicos locais ainda abstiveram; não há homologação universal de vereditos/APIs.

**Adendo atual de 10/10:** [correções das verificações inconclusivas](INCONCLUSIVOS-2026-10-10.md) documenta os campos `media_signal`, `source_attribution`, `provider_coverage.google_fact_check.query_plan`, limites e testes. [Publicação de 08/10](PUBLICACAO-2026-10-08.md) comprova a revisão anterior. A base/configurações e números datados no corpo abaixo são histórico de 07/10; não usar o antigo Hive “pausado” como estado atual: o responsável autorizou saldo existente e configurou imagem/áudio com limites, sem contratação ou recarga pelo agente.

**Atualização:** 07/10/2026. **Novo prazo solicitado:** esta semana, até 11/10/2026. O calendário anterior de 04–17/10 permanece como histórico; consulte o [fechamento acelerado](ENTREGA-ATE-11-OUTUBRO.md).

Este é o manual consolidado da **revisão local** do Verify. Base Git examinada: `5db970da8f8a109472050ed96e3ab77d20e7f5e7`, acrescida das alterações locais registradas nos documentos de 03–07/10. Essas alterações ainda não têm um novo commit de entrega nem comprovação de publicação. O número `1.0.0` da API e `0.1.0` do pacote frontend não identificam o commit servido em produção. Resultados mais recentes, mudanças e bloqueios estão no [registro de 07/10](FECHAMENTO-2026-10-07.md).

O objetivo é entregar um **verificador assistido**, com evidências, limites e revisão humana. Não há garantia de identificar toda falsidade, certificar toda verdade ou detectar qualquer deepfake. Nem todas as integrações foram homologadas em todas as modalidades.

Este manual documenta o código; o [plano detalhado de 14 dias](PLANO-ENTREGA-14-DIAS.md) transforma as pendências em tarefas, responsáveis, dependências e critérios de aceite. Documentos antigos são registros de etapas: não substituem esta configuração consolidada.

## Sumário

- [1. Produto, público e escopo](#produto)
- [2. Situação comprovada e pendências](#situacao)
- [3. Arquitetura e organização](#arquitetura)
- [4. Fluxos por modalidade](#fluxos)
- [5. Políticas de evidência e interpretação](#politicas)
- [6. Contrato dos relatórios](#relatorios)
- [7. Banco de dados e histórico](#banco)
- [8. Rotas da interface](#interface)
- [9. Referência da API](#api)
- [10. Autenticação e sessões](#autenticacao)
- [11. Limites, admissão e proteção de recursos](#limites)
- [12. Variáveis de ambiente: inventário completo](#ambiente)
- [13. Instalação local e Docker](#instalacao)
- [14. APIs: obtenção e ativação segura](#provedores)
- [15. Publicação no Railway e na Vercel](#deploy)
- [16. PDF, revisão humana e registro de integridade](#pdf)
- [17. Segurança, privacidade e lacunas conhecidas](#seguranca)
- [18. Testes, corpus e evidências](#testes)
- [19. Acessibilidade e uso por pessoas leigas](#acessibilidade)
- [20. Operação, diagnóstico e contingência](#operacao)
- [21. Entrega em 14 dias e definição de conclusão](#entrega)
- [22. Contribuição, modelos de registro e apresentação](#contribuicao)
- [23. Glossário e referências](#referencias)

<a id="produto"></a>
## 1. Produto, público e escopo

### 1.1 Problema atendido

Mensagens recebidas em redes sociais e aplicativos podem misturar afirmações verdadeiras, falsas, desatualizadas ou sem fonte, além de pedidos financeiros e arquivos sintéticos. O Verify ajuda a organizar sinais e consultar checagens, sem substituir confirmação com a fonte original ou uma avaliação especializada.

O público inclui idosos e pessoas sem formação técnica. O relatório precisa responder, nesta ordem: **o que foi analisado; o que foi encontrado; por que isso importa; o que ainda não se sabe; qual é o próximo passo seguro**.

### 1.2 Funcionalidades e fronteiras

| Recurso | Implementação atual | O que não se pode prometer |
| --- | --- | --- |
| Texto | Consulta de checagens, afirmações literais e padrões de possível golpe | Que ausência de checagem signifique verdade; que um LLM conheça a verdade |
| Link | Leitura pública estática e análise do texto extraído | Certificação do domínio inteiro, reputação de malware, idade do domínio ou leitura de todo JavaScript |
| Imagem | Validação dos bytes, OCR, metadados e detectores disponíveis | Origem humana porque scores foram baixos; perícia conclusiva a partir de inspeção visual |
| Áudio | Validação, tratamento de silêncio, transcrição e camadas específicas de fala sintética | Identificação do falante, autorização da fala ou detecção universal de clonagem |
| Vídeo | Quadros amostrados e faixa de áudio separada, quando presente | Análise de todos os quadros, identidade facial ou sincronização labial completa |
| Conferência humana | Edição/confirmação de OCR/transcrição em `/app`, seguida de nova checagem textual | Que confirmar o texto comprove fidelidade da leitura ou autenticidade da mídia |
| Relatório/PDF | Evidências, cobertura, limites e exportação da mesma análise assinada | Certificado de verdade ou nova análise no momento do download |
| Histórico/painel | Persistência e consulta vinculadas à conta | Exclusão de conta/histórico, retenção automática ou cobrança por planos já implementadas |
| Registro SHA-256 | Registro e comparação de bytes | Assinatura de câmera, autoria, veracidade da cena ou C2PA |
| Demonstração | Recursos educativos e simulador de WhatsApp | Bot real homologado enviando mensagens a números externos |

### 1.3 Escopo de entrega

O caminho recomendado até o prazo é **apresentação e piloto efetivamente limitado**, com conteúdo fictício ou autorizado e restrição de acesso real. Uma página aberta com o rótulo “piloto” continua acessível ao público: o rótulo não é um controle técnico.

Para lançamento público irrestrito, o pacote adicional de exclusão/retenção, migrações, backup/restauração, isolamento, segurança e operação precisa estar pronto. Esse pacote pode substituir polimento visual e consumir 2–4 dias adicionais de trabalho, dependendo dos achados. O prazo não autoriza omitir proteções essenciais.

<a id="situacao"></a>
## 2. Situação comprovada e pendências

### 2.1 Vocabulário de status

- **Implementado:** existe caminho no código; pode ainda faltar teste real ou publicação.
- **Validado localmente:** determinado cenário passou no ambiente e na versão registrados.
- **Transporte validado:** uma API aceitou a chamada e retornou um formato utilizável; não mede precisão.
- **Parcialmente executado:** pelo menos uma dimensão do caso foi testada; não significa todas as etapas corretas.
- **Experimental:** sinal apresentado sem elegibilidade para decidir o veredito.
- **Homologado no deploy:** fluxo completo repetido no commit publicado e registrado com evidências. Essa etapa não está concluída para esta revisão.
- **Inconclusivo:** há insuficiência, conflito ou cobertura inadequada para concluir. É um resultado válido, não um sinônimo de “falso”.

### 2.2 Últimos resultados registrados

Estes resultados vêm dos registros existentes; **não são uma nova execução realizada ao escrever este manual**.

| Evidência | Resultado registrado | Limite da conclusão |
| --- | --- | --- |
| Backend mais recente | 424 testes offline, Python 3.11 em Docker, SQLite, sem rede | Regressão funcional com respostas controladas; não benchmark de fornecedores |
| Frontend mais recente | 124 testes e build, Node 22; build com 1.976 módulos | Não substitui ensaio completo de acessibilidade ou deploy |
| PostgreSQL descartável atual | Mesmos 424 testes, Python 3.11, banco isolado | Só três são integração PostgreSQL; os restantes continuam SQLite/mocks. Não homologa todos os fluxos da aplicação |
| Matriz de entradas | 30 casos: 22 parcialmente executados, 8 pendentes | Não são 22 acertos de classificação |
| Extração local adicional | 18/19 comparações estritas passaram | OCR05 mudou “Valor” para “valor”; falha preservada no registro |
| PDF textual/link/histórico | Respostas 200 com `application/pdf`; relatório original preservado | Salvamento final pelo navegador integrado não foi comprovado |
| Docker | Build da raiz e ferramentas verificados em etapa anterior | Build isolado de `backend` e publicação final ainda pendentes |
| CI | Workflow e runner preparados; comandos locais verificados | Execução no GitHub e bloqueio de publicação por checks ainda pendentes |

Referências: [PDF texto/link](PDF-TEXTO-LINK-2026-10-04.md), [PDF/banco/CI](PDF-READINESS-CI-2026-10-04.md), [controles de extração](CONTROLES-EXTRACAO-2026-10-04.md), [validação pela interface](VALIDACAO-INTERFACE-2026-10-04.md).

### 2.3 Integrações: estado honesto

| Serviço | Papel | Resultado/pendência relevante |
| --- | --- | --- |
| Google Fact Check | Recuperar checagens editoriais | Transporte respondeu; controles Apollo 11/Terra plana não tiveram evidência literal suficiente para conclusão automática |
| Serper | Notícias/contexto de pesquisa | Respondeu; notícia relacionada não vota como prova de verdade |
| Gemini | Extração literal, OCR, transcrição, inspeção e TTS | Em 07/10, 3.8 respondeu ao controle mínimo de texto; 3.7/OCR/inspeção retornaram 503. Prazos corrigidos; multimodal não homologado |
| OpenRouter gratuito | Extração literal e OCR alternativo | Texto respondeu; OCR teve 404/incompletude; prazo externo agora compatível com cliente de 25 s. Não é decisor factual |
| AssemblyAI | Transcrição | Houve erros como “Pix urgente” → “pic surgente”; revisão humana é obrigatória no fluxo principal antes da checagem factual |
| Sightengine | Imagem/deepfake e áudio opt-in | Três controles de imagem responderam; isso não homologa face-swap nem `ai_speech` |
| Hive | Imagem/facial e áudio com versões/projetos próprios | Smoke test v3 de imagem anterior; sem homologação completa de fala/clonagem e sem novas chamadas pagas nesta documentação |
| Hugging Face | Detector experimental de imagem | Errou controles conhecidos em sentidos opostos; permanece sem voto, inclusive em vídeo |
| SerpAPI | Busca reversa opcional | Autenticação/metadados verificados em etapa anterior; busca reversa real ainda pendente |
| C2PA | Credenciais de conteúdo | Caminho implementado; ferramenta, confiança e corpus assinado real ainda não homologados |
| Wayback/TinEye/GPTZero | Integrações auxiliares/legadas | Não equivalem a cobertura homologada do fluxo principal |
| VirusTotal | Variável prevista | Não há implementação atual de reputação/malware de URL |
| WhatsApp/Evolution | Demonstração e infraestrutura opcional | Simulador funciona; transporte real autenticado e envio de resposta não homologados |

### 2.4 Bloqueadores principais

1. Fechar o escopo piloto versus público e conferir saldo/expiração da hospedagem.
2. Receber gravações humanas e vídeos originais autorizados para os controles restantes; fotos publicadas/IA não os substituem.
3. Homologar auth/upload/URL no PostgreSQL e conferir o contexto Docker escolhido para o deploy; suíte regressiva atual já passou em banco isolado.
4. Consolidar as alterações locais em Git, executar CI, publicar e conferir o commit efetivo.
5. Homologar ponta a ponta, incluindo link HTTPS público e download de PDF salvo/aberto.
6. Resolver os requisitos de privacidade/operação se a entrega for pública.
7. Auditar orçamento, autenticação e limitações por processo antes de qualquer expansão de acesso.

<a id="arquitetura"></a>
## 3. Arquitetura e organização

### 3.1 Tecnologias

| Camada | Tecnologia | Observação |
| --- | --- | --- |
| Interface | React 18, React Router 6, Vite 5, Tailwind 3, Lucide, Axios | SPA; não é Next.js |
| API | Python 3.11, FastAPI, Pydantic, HTTPX | Operações assíncronas; erro externo não deve fabricar resultado |
| Persistência | SQLAlchemy assíncrono, asyncpg/PostgreSQL 16 | SQLite para desenvolvimento e testes isolados |
| Sessão | JWT, python-jose, cookies HTTP-only | Argon2 para senhas; tokens não retornados ao JavaScript no login |
| Mídia | FFmpeg, ffprobe, Pillow, ExifTool | Decodificação e limites reais, não apenas MIME/extensão |
| OCR | Tesseract português/inglês | Local primeiro; provedores remotos como alternativas |
| PDF | ReportLab | Poppler é necessário nos testes de extração/renderização, não para gerar o PDF em produção |
| Publicação | Vercel frontend; Railway backend/PostgreSQL | Configurações e segredos têm destinos diferentes |

### 3.2 Topologia

```text
Navegador ── arquivos estáticos ── Vercel / React-Vite
    │
    └── HTTPS /api + cookies ── Railway / FastAPI
                                 ├── PostgreSQL: contas, resultados, métricas, registros
                                 ├── ferramentas locais: OCR, mídia, metadados, PDF
                                 └── fornecedores habilitados: busca, leitura, detectores

Testes descartáveis: SQLite/PostgreSQL próprios + provedores simulados
```

Chamadas externas ficam no backend. Uma chave em `VITE_*` passa a fazer parte do JavaScript público, não vira um segredo protegido pela Vercel. Consulte [variáveis do Vite](https://vite.dev/guide/env-and-mode).

### 3.3 Mapa de arquivos

```text
verify/
├── README.md                          entrada rápida do repositório
├── AGENTS.md                          orientação de trabalho no código
├── Dockerfile                         backend com contexto da raiz
├── docker-compose.yml                 ambiente de desenvolvimento
├── railway.toml                       configuração com contexto da raiz
├── .github/workflows/tests.yml         regressão SQLite/PostgreSQL + frontend
├── backend/
│   ├── .env.example                   modelo sem segredos
│   ├── Dockerfile / railway.toml       alternativa com contexto backend
│   ├── requirements.txt               dependências Python
│   ├── app/main.py                    inicialização, middleware e routers
│   ├── app/api/                       contratos de entrada e endpoints
│   ├── app/core/                      banco, sessão, pipeline e clientes
│   ├── app/models/                    modelos SQLAlchemy e schemas
│   ├── app/services/                  validação, políticas, revisão e PDF
│   ├── scripts/                       probes, harnesses e runner offline
│   └── tests/                         regressões e controles rotulados
├── frontend/
│   ├── .env.example                   apenas configuração pública
│   ├── vercel.json                    fallback de rotas SPA
│   ├── src/pages/                     telas e fluxos
│   ├── src/components/                interface, relatório e demonstração
│   ├── src/services/                  API, privacidade e ciclo da mídia
│   ├── src/utils/                     normalização, revisão e exportação
│   └── tests/                         testes Node de contratos/utilitários
└── docs/                              manual, plano, decisões e evidências
```

### 3.4 Responsabilidades de módulos

| Módulo | Responsabilidade |
| --- | --- |
| [pipeline.py](../backend/app/core/pipeline.py) | Recuperar checagens/contexto, executar triagem e montar análise textual |
| [claim_policy.py](../backend/app/services/claim_policy.py) | Decidir relação com checagens correspondentes, sem voto de LLM |
| [evidence_policy.py](../backend/app/services/evidence_policy.py) | Combinar sinais utilizáveis sem transformar ausência em autenticidade |
| [media_validation.py](../backend/app/services/media_validation.py) | Validar bytes, streams, dimensões e duração; extrair quadros |
| [media_analysis.py](../backend/app/services/media_analysis.py) | Orquestrar imagem/áudio/vídeo e preservar cobertura por camada |
| [public_fetch.py](../backend/app/services/public_fetch.py) | Consulta pública limitada, DNS/IP, TLS e redirecionamentos revalidados |
| [local_ocr.py](../backend/app/services/local_ocr.py) | OCR local e informação de qualidade/indisponibilidade |
| [audio_service.py](../backend/app/services/audio_service.py) | Transcrição configurável e prazo de processamento |
| [request_budget.py](../backend/app/core/request_budget.py) | Origem de escrita, corpo, taxa e concorrência por processo |
| [privacyStorage.js](../frontend/src/services/privacyStorage.js) | Limpar caches legados e isolar relatório da sessão/conta |
| [api.js](../frontend/src/services/api.js) | Base de URL, cookies, renovação de sessão, chamadas e PDF |
| [pdf_snapshot.py](../backend/app/services/pdf_snapshot.py) | Assinar e validar uma cópia do relatório original |
| [extracted_text_review.py](../backend/app/services/extracted_text_review.py) | Vincular texto conferido à leitura original com finalidade própria |
| [readiness.py](../backend/app/services/readiness.py) | Conectividade read-only do banco, deadline e cache curto |

<a id="fluxos"></a>
## 4. Fluxos por modalidade

### 4.1 Texto e lote

1. Receber texto de 10–5.000 caracteres; lote aceita 1–10 mensagens válidas.
2. Aplicar admissão e verificar quota da conta, quando houver conta válida.
3. Preservar a consulta literal; extração por modelo auxilia pesquisa, não gera novas “afirmações verdadeiras”.
4. Recuperar checagens e notícias; registrar indisponibilidade ou cobertura insuficiente.
5. Aplicar política editorial e triagem de possível golpe separadamente.
6. Retornar relatório com fontes, explicação, data e versão; persistir quando autenticado.
7. Anexar capacidade de exportação somente depois da persistência bem-sucedida e se o relatório for compatível.

Falha de item de lote não recebe PDF nem deve aparecer como conclusão factual. Um lote não torna fontes duplicadas independentes.

### 4.2 Link

O backend aceita HTTP/HTTPS público nas portas 80/443, rejeita credenciais na URL e endereços locais/privados/reservados. Resolve DNS, valida os IPs, conecta ao IP validado e mantém validação do hostname TLS. Revalida até cinco redirecionamentos, limita resposta a 2 MiB e rejeita conteúdo comprimido na consulta segura.

Tipos aceitos: `text/html`, `application/xhtml+xml`, `text/plain`. HTML é lido estaticamente: scripts, menus, templates e ocultações explícitas são removidos; o título do artigo é preservado. Não há navegador executando CSS/JavaScript. Extrai até 5.000 caracteres; menos de 50 caracteres é insuficiente para esse fluxo.

O relatório guarda `source_url`, `source_text` e `source_extraction`, incluindo método, truncamento e `rendered_browser=false`. Ele analisa aquele recorte, naquela data, não todo o site. Login, paywall, bloqueio anti-bot e layout dinâmico podem impedir a leitura.

### 4.3 Imagem

Valida formato/decodificação/dimensões → OCR local ou alternativa disponível → detectores/metadados/C2PA/inspeção auxiliar → relatório de origem sintética separado do conteúdo textual. GIF animado não equivale a inspeção completa de toda a animação.

Em `/app`, texto extraído aguarda revisão antes da checagem factual. A pessoa pode corrigir negação, valores e datas; a nova checagem não repete detectores de imagem nem altera o arquivo original.

### 4.4 Áudio

Valida streams e duração → normaliza entrada de fala → bloqueia quase silêncio → tenta transcrição na ordem configurada → oferece revisão → checa apenas o texto confirmado. Detectores de fala sintética, quando autorizados, permanecem uma camada distinta.

AssemblyAI é transcritor, não detector de clonagem. Um texto transcrito corretamente pode conter uma afirmação falsa; uma voz sintética pode ler uma afirmação verdadeira. Não identificar falante com base nesses sinais.

Retomada ASR implementada por conta validada ou nonce aleatório de aba, mesmos bytes preparados e projeto/modelo/opções. Após criação, novas rodadas consultam o ID privado existente; POST com resposta incerta bloqueia recriação temporária. Máximo 64 registros/8 workers, prazos de 25 s, pendência 30 minutos + marcador expirado de 5 minutos; sucesso retido 5 minutos e falha determinística 60 s. Timers limpam dados locais, não os artefatos remotos. Não há garantia depois de reinício, outra réplica/worker, reload/perda do contexto ou remoção do registro. Outros detectores podem ser consultados de novo. [Arquitetura, estados e ensaio simulado](TRANSCRICAO-PENDENTE-2026-10-07.md).

### 4.5 Vídeo

Valida streams/duração → seleciona de 3 até o limite configurado de quadros, conforme duração → reduz dimensão dos quadros → analisa imagens → extrai áudio quando presente → agrega cobertura sem fabricar consenso entre instantes diferentes.

Padrão: até 9 quadros; configuração limitada a 3–12. Os tempos amostrados cobrem aproximadamente 10%–90% do vídeo, não todos os frames. Concordância precisa existir no mesmo quadro; sinais de fornecedores em quadros distintos não se tornam automaticamente prova conjunta. Áudio, transcrição, geração visual e possível manipulação facial ficam separados.

### 4.6 Histórico e exportação

Histórico requer conta válida e filtra somente registros daquela conta. Reabrir uma análise usa o resultado persistido; não recalcula os detectores. Exportar usa o snapshot assinado do resultado original; não reenvia a mídia nem consome quota diária de análise.

### 4.7 WhatsApp

Webhook: autenticação do segredo antes de processamento → parser → descartar mensagens próprias/duplicadas → obter texto/bytes de forma limitada → analisar → responder JSON. Gateway precisa transportar e enviar a resposta. O simulador não é teste de entrega ao WhatsApp real.

O perfil Evolution do Compose não cria sozinho seu banco específico, nem configura todos os headers de autenticação ou transporte. Ele permanece opcional e fora do escopo principal de entrega.

<a id="politicas"></a>
## 5. Políticas de evidência e interpretação

### 5.1 Veracidade textual — versão `2026-10-03.1`

Uma checagem só é elegível quando:

1. Sua afirmação corresponde literalmente à entrada normalizada.
2. A recuperação foi identificada como `google_fact_check`.
3. URL usa HTTPS seguro e pertence a uma família editorial cadastrada.
4. Data de revisão existe, é interpretável e não está no futuro.
5. Avaliação é explicitamente `true`/`verdadeiro`/`verdadeira` ou `false`/`falso`/`falsa`.
6. A entrada não contém contexto relativo, pergunta ou citação que exija revisão adicional.

A normalização preserva acentos, negação, números e pontuação interior; uniformiza caixa/espaços e remove ponto final. “avó” e “avô”, “não” e afirmação positiva, datas e valores diferentes não se tornam equivalentes.

Famílias cadastradas: Aos Fatos, Boatos.org, Lupa, Estadão, AFP, Reuters, AP e Full Fact, por domínios explicitados no código. Dois domínios da mesma família contam uma vez. Estar na lista não torna uma fonte infalível.

| Condição | Estado |
| --- | --- |
| Pelo menos duas famílias distintas corroboram, sem refutação correspondente | `supported` |
| Pelo menos duas famílias distintas refutam, sem apoio correspondente | `refuted` |
| Há apoio e refutação correspondentes | `conflicting` |
| Trechos diferentes têm apoio e refutação | `mixed` |
| Falta cobertura suficiente ou correspondente | `unverified` |

Primeiro tenta a entrada inteira; se não concluir, examina até cinco segmentos literais. A mensagem inteira só é corroborada/refutada quando há cobertura completa segundo essa política. Mais de cinco segmentos sem cobertura integral geram limitação explícita.

Essa política privilegia evitar conclusões indevidas, mas tem **baixa recuperação de paráfrases**. Melhorar recall exige preservar negação, temporalidade, entidades, quantidades e fonte verificável; não basta baixar um limiar de similaridade. Notícias relacionadas, reputação do domínio e concordância entre LLMs não substituem checagens correspondentes.

### 5.2 Origem de mídia — versão `2026-10-03.2`

Scores só entram quando o fornecedor está disponível, a resposta tem sucesso e o número é finito entre 0 e 1. Campo ausente, string, booleano, erro ou detector experimental não fabrica score.

Sinal alto: `>= 0.8`; sinal baixo: `<= 0.2`. A regra atual exige pelo menos dois fornecedores elegíveis com sinal alto, sem sinal baixo contraditório, para indicar geração por IA. Manipulação facial usa duas camadas dedicadas de fornecedores distintos; duas respostas Hive não contam como dois fornecedores independentes.

C2PA validado com indicação de geração pode ser uma via específica para imagem/vídeo, mas depende de validação e confiança reais. Áudio não usa essa exceção. Hugging Face permanece `voting_eligible=false` no cliente atual. Não reativar voto porque “a API respondeu”.

Mesmo com sinais baixos, o resultado permanece origem **não determinada**. A regra não afirma “humano”, “verdadeiro” ou “sem edição”. Scores não foram calibrados como probabilidade de erro ou acerto.

### 5.3 Possível golpe

Regras de triagem destacam trechos de urgência, pedidos financeiros e padrões de risco. Isso pode produzir `Scam` como rótulo de cautela sem provar falsidade de cada afirmação ou identidade do remetente. Extensão de domínio isolada não deve determinar golpe. Orientações cadastradas são referências educativas, não checagens recuperadas automaticamente.

### 5.4 Por que não exibir “90% verdadeiro”

O campo legado `score` utiliza índices fixos associados a decisões: por exemplo, 90 para texto corroborado, 10 para refutado e 50 para inconclusivo. **Não é uma medição de 90% de veracidade.** O contrato declara `score_semantics=legacy_decision_index_not_probability` e mantém `confidence`/`authenticity_percentage` nulos quando não medidos.

A animação pode mostrar um índice compatível com seu rótulo, respeitando movimento reduzido. Inconclusivo deve aparecer como “Não determinado”, sem barra parando artificialmente em 50%. Não divulgar porcentagem de precisão baseada nesses índices.

<a id="relatorios"></a>
## 6. Contrato dos relatórios

### 6.1 Campos principais

| Campo | Interpretação |
| --- | --- |
| `content_type` | `text`, `url`, `image`, `audio`, `video`, conforme fluxo |
| `query_input` / `source_text` | Consulta textual / recorte de texto lido no link |
| `source_url`, `source_extraction` | Origem final e limites da leitura pública |
| `analyzed_at`, `policy_version`, `model_used` | Momento e regra/auxiliar usados; não basta o modelo para reproduzir tudo |
| `verdict`, `score`, `score_semantics` | Compatibilidade legada; a semântica precisa ser preservada |
| `veracity_status` | Relação com checagens factuais; diferente da origem da mídia |
| `authenticity_status` | Indícios de geração/manipulação ou origem não determinada |
| `analysis_status` | Parcial/inconclusivo, não selo global de sucesso |
| `plain_explanation`, `summary` | Explicação compreensível e atribuída às evidências |
| `claim_assessments` | Por afirmação: estado, fontes elegíveis/excluídas e motivos |
| `fact_checks`, `serper_news` | Resultados recuperados; notícias são contexto, não votos factuais |
| `provider_coverage` | O que respondeu, faltou, falhou e qual papel teve |
| `limitations` | Recortes e motivos que impedem conclusão mais forte |
| `forensics`, `content_analysis` | Camadas de mídia e conteúdo extraído, separados |
| `text_review` | Leitura original, texto confirmado, edição e datas, quando aplicável |
| Campos `pdf_*` e `text_review_token` | Capacidades temporárias; não persistir ou copiar em JSON técnico público |

### 6.2 Exemplo ilustrativo, não resposta de uma análise real

```json
{
  "content_type": "text",
  "query_input": "Mensagem fictícia sem checagens correspondentes.",
  "verdict": "Suspicious",
  "veracity_status": "unverified",
  "authenticity_status": "not_applicable",
  "analysis_status": "inconclusive",
  "score": 50,
  "score_semantics": "legacy_decision_index_not_probability",
  "confidence": null,
  "authenticity_percentage": null,
  "policy_version": "2026-10-03.1",
  "limitations": ["Evidência correspondente insuficiente para concluir."]
}
```

O exemplo omite campos por brevidade. Não tratar o schema legado de `AnalysisResponse` como representação integral do contrato dinâmico atual: a formalização/versionamento dos modelos de resposta é uma pendência.

### 6.3 Conteúdo esperado no relatório detalhado

Mostrar afirmação exata, fonte/data, avaliação atribuída, motivo de inclusão/exclusão e limites. Para refutação, encaminhar para argumentos da checagem; não inventar uma justificativa causal quando a fonte não a forneceu. Para mídia, informar quais camadas/quadros/trechos foram analisados e quais faltaram. Falha de OCR ou API deve aparecer como falha, não como “indício de falsidade”.

<a id="banco"></a>
## 7. Banco de dados e histórico

### 7.1 Conexão e inicialização

`DATABASE_URL` é indispensável em produção. O código converte `postgres://`/`postgresql://` para o driver assíncrono `postgresql+asyncpg://`. Sem variável, usa SQLite local: **esse fallback não deve ser aceito como configuração de produção**.

SQLAlchemy cria tabelas via `create_all` no lifespan. Há ajustes aditivos de enum `SCAM`/`FALSE`, mas isso não é uma estratégia completa de migração. Não existe uma sequência versionada de migrations homologada; adicionar Alembic ou equivalente, revisar legado e testar em staging antes de mudanças de schema.

`/ready` confirma `SELECT 1`, não estrutura de tabelas, escrita, integridade de FK, restauração ou migração aplicada.

### 7.2 Dicionário de entidades

| Entidade | Dados principais | Relação/cuidados |
| --- | --- | --- |
| Usuário | UUID, email, nome, hash Argon2 opcional para OAuth, Google ID, avatar, tier, estado ativo, datas | Email único; tier interno não é cobrança |
| Verificação | UUID, dono, tipo, URL, índice/rótulo legado, resumo, resultado JSON, data, hash MD5 legado | FK de usuário; consultas devem incluir dono |
| Métricas | FK da verificação, scores auxiliares, data/origem disponíveis | Ausência não vira zero; scores não medem precisão |
| Cache legado | MD5, verificação associada, expiração | Upload atual não reutiliza resultado global por MD5 |
| Registro de integridade | UUID, SHA-256, nome/tipo/tamanho, assinatura HMAC, data e metadados | Compara bytes; não certifica captura/autor |
| Conversa WhatsApp | Hash de remetente e conteúdo/resposta, quando habilitado | Pseudônimo, não anonimização; texto pode conter dados pessoais |

Links são armazenados como tipo textual com `source_url`/metadados, e distinguidos pela consulta do histórico. O enum SQLAlchemy legível no código é diferente de rótulos/representações em JSON: não editar dados diretamente assumindo equivalência de strings.

**Corrigido localmente em 07/10:** URL de análise aceita até 512 caracteres após retirar espaços externos; protocolo `https://` automático entra na contagem. URL final/canônica após redirecionamentos também precisa caber em 512; excesso retorna 422 antes de analisar/persistir, sem cortar o endereço. O fetch público genérico mantém seu limite de 4.096, pois atende outros usos. Fluxo completo de URL no PostgreSQL publicado ainda precisa homologação.

### 7.3 Histórico e painel

Paginação: padrão 20, máximo 50 itens; página 1–10.000. Busca até 200 caracteres. Tipo e veredito filtram consulta e contagem no conjunto inteiro da conta, não só a página atual. Data/ID estabilizam ordenação.

Registro de outra conta retorna 404; ID inválido, 422. Estatísticas excluem inconclusivos e registros legados sem semântica confiável da média do índice. Sem base adequada, média é nula/“Não determinado”. Não apresentar essa média como precisão do sistema.

Não há endpoints completos de exclusão de histórico/conta nem job de retenção implementados. FK com cascade no modelo não equivale a disponibilizar exclusão segura ao usuário.

<a id="interface"></a>
## 8. Rotas da interface

| Rota | Finalidade | Sessão |
| --- | --- | --- |
| `/` | Landing azul/ciano, explicação e entrada | Pública |
| `/app` | Envio e checagem principal; revisão de texto extraído | Visitante ou autenticado |
| `/report` | Relatório atual da sessão | Não exige login para relatório visitante |
| `/report/:id` | Reabertura de registro | Backend exige conta dona do registro |
| `/login`, `/register` | Autenticação | Pública |
| `/dashboard`, `/history` | Painel/histórico; ambos usam painel atual | Protegida |
| `/demo`, `/demonstracao` | Demonstração educativa | Pública |
| `/mission`, `/suggestions` | Páginas institucionais | Pública; não presumir recebimento/persistência server-side de sugestões |
| `/terms`, `/privacy`, `/limitacoes` | Termos, privacidade e limites | Pública; texto não comprova implementação de controles |

SPA precisa de fallback ao `index.html` nas rotas de navegação. Não há rota catch-all de 404 implementada no App atual. Cadastro/login, navegação direta e expiração devem ser testados no domínio publicado.

Estado sensível: relatório em `sessionStorage` versionado, até 1 MiB, vinculado ao dono confirmado; memória temporária se armazenamento estiver bloqueado. Saída/troca de conta limpa conteúdo e consultas, preservando preferências. Sinal entre abas não inclui conteúdo/credenciais. Tokens de revisão ficam em memória; tokens de exportação não devem ser persistidos no banco ou log.

<a id="api"></a>
## 9. Referência da API

API base: origem do backend seguida de `/api`. Documentação FastAPI normalmente disponível em `/docs` e `/openapi.json`; ela mostra entradas implementadas, mas não substitui os limites semânticos deste manual.

### 9.1 Rotas operacionais e de sessão

| Método/rota | Entrada | Resposta/uso |
| --- | --- | --- |
| `GET /` | — | Identificação/liveness simples da API |
| `GET /health` | — | Processo ativo; não verifica banco/fornecedores |
| `GET /ready` | — | Banco acessível: 200; falha/timeout: 503 |
| `GET /api/capabilities` | — | Configuração/ferramentas presentes, sem revelar segredos nem consumir APIs |
| `POST /api/auth/register` | JSON: `email`, `name`, `password` | Cadastro e cookies; duplicidade: 400 |
| `POST /api/auth/login` | JSON: `email`, `password` | Sessão por cookies; credencial inválida: 401 |
| `POST /api/auth/google` | JSON: `id_token` | Verifica token do cliente Google configurado |
| `POST /api/auth/refresh` | Cookie de refresh | Renova cookies; sessão inválida: 401 |
| `POST /api/auth/logout` | Cookies | 204 e exclusão dos cookies; sem revogação de cópias externas |
| `GET /api/auth/me` | Sessão | ID/email/nome/tier/avatar do usuário |

### 9.2 Análises

| Método/rota | Entrada | Autenticação/comportamento |
| --- | --- | --- |
| `POST /api/check-text` | `{"text":"..."}` | Conta opcional; histórico se autenticado |
| `POST /api/check-text-batch` | `{"texts":["...","..."]}` | 1–10 entradas; erro individual não é conclusão |
| `POST /api/check-url` | `{"url":"https://..."}` | Conta opcional; consulta pública limitada |
| `POST /api/upload` | Multipart `file`; `review_text` opcional | Conta opcional; `/app` solicita revisão |
| `POST /api/check-extracted-text` | `text`, `review_token` | Valida procedência/dono antes da quota; nova checagem textual |
| `POST /api/verificar/completo` | Multipart `file`; revisão conforme endpoint | Entrada alternativa de mídia, com contrato forense |
| `POST /api/verificar/audio-rapido` | Multipart `file` | Conteúdo da fala; não identificação ou clonagem universal |

### 9.3 Histórico, PDF, registro e WhatsApp

| Método/rota | Entrada | Observação |
| --- | --- | --- |
| `GET /api/history` | `page`, `limit`, `search`, `content_type`, `verdict` | Conta obrigatória; filtros Titlecase (`Text`, `Url`, etc.) |
| `GET /api/history/stats` | Sessão | Agregados dentro da conta |
| `GET /api/history/{id}` | UUID e sessão | Somente dono; reabre resultado sem nova análise |
| `POST /api/verificar/relatorio-pdf` | JSON `snapshot_token` | Resposta `application/pdf`; não aceita mídia/resultado arbitrário |
| `POST /api/capturar/selo` | Multipart `file` | Alias `/api/selo/capturar`; registra bytes/assinatura |
| `POST /api/verificar/selo` | Multipart `file` | Compara hash com registro existente |
| `GET /api/verificar/selo/{file_hash}` | Hash | Consulta do registro de integridade; não é prova factual |
| `POST /api/whatsapp/simulate` | JSON `message`; campos opcionais de mídia | Simulação educativa; não envio ao WhatsApp real |
| `POST /api/whatsapp/webhook` | Evento e segredo do webhook | Transporte real depende de infraestrutura adicional |

### 9.4 Exemplo de chamada local

Com backend iniciado e sem chaves externas habilitadas, esta entrada fictícia pode ficar inconclusiva. Com chaves ativas, pode consumir quota. Para testes rotineiros, preferir runner offline.

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/ready
curl --fail-with-body http://127.0.0.1:8001/api/check-text \
  -H 'Content-Type: application/json' \
  --data '{"text":"Exemplo fictício para testar o fluxo, sem afirmação verificada."}'
```

Não imprimir tokens em terminal compartilhado nem salvar cookies de contas reais em arquivos de teste. Fluxos autenticados devem usar conta descartável de staging e verificar dono/isolamento.

### 9.5 Códigos de erro

| Código | Causa típica | Tratamento esperado |
| --- | --- | --- |
| 400 | URL inválida/bloqueada, site recusou leitura, cadastro duplicado | Explicar entrada/contexto; não dar veredito factual |
| 401 | Sessão ausente/expirada ou credencial inválida | Renovar uma vez quando aplicável; solicitar login |
| 403 | Origem de escrita não autorizada, token vinculado a outra conta | Corrigir configuração/permissão; não desativar proteção |
| 404 | Registro não existe ou não pertence à conta | Não revelar existência de outra conta |
| 408 | Corpo demorou além do prazo | Orientar reenvio menor/rede estável |
| 410 | Capacidade temporária expirada | Reabrir histórico ou gerar análise válida; não adulterar validade |
| 413 | Corpo, arquivo ou recurso remoto excedeu limite | Informar limite correspondente |
| 415 | Tipo real/declaração incompatível ou documento não suportado | Não confiar só em renomear extensão |
| 422 | Entrada insuficiente/inválida, token/snapshot incompatível | Corrigir entrada; não forçar resultado |
| 429 | Taxa, quota ou concorrência | Respeitar `Retry-After`; sem fallback pago automático |
| 503 | Ferramenta, assinatura ou prontidão indisponível | Mostrar indisponibilidade, não falsidade |
| 504 | Consulta pública excedeu prazo | Tentar depois ou enviar trecho autorizado |

Provedores podem retornar falha dentro de um relatório HTTP 200 com cobertura parcial. Ler estado/camadas e não apenas o status HTTP.

<a id="autenticacao"></a>
## 10. Autenticação e sessões

Na [revisão candidata de 08/10](ENTREGA-BANCA-2026-10-08.md), o cliente não reenvia POST/FormData após refresh; leitura só repete na mesma conta/época. Falha/logout antigos não encerram conta nova. Login/cadastro/Google invalidam contexto antes da mudança de cookies. 18 regressões locais cobrem esses caminhos; pedidos já enviados, cookies tardios e revogação permanecem fora dessa garantia.

Cookies atuais: `verifai_access` em `/` e `verifai_refresh` em `/api/auth/refresh`; ambos HTTP-only. Token access expira por padrão em 60 minutos; refresh, em 7 dias. Clientes manuais também podem usar Bearer; existe compatibilidade de leitura de cookie legado.

Produção exige `JWT_SECRET` forte, estável e com pelo menos 32 caracteres; desenvolvimento pode gerar segredo temporário e perder sessões ao reiniciar. Usar segredo independente para HMAC. Configurar HTTPS, `COOKIE_SECURE=true` e `COOKIE_SAME_SITE=none` no cenário cross-site Vercel/Railway. Bloqueio de cookies de terceiros pelo navegador ainda pode afetar esse arranjo; considerar domínios próprios sob o mesmo site, depois de testar.

Argon2 protege senhas. O cadastro atualmente aceita mínimo de 6 caracteres; uma função de política mais forte existente não está aplicada nesse caminho. Não anunciar exigência de senha forte, confirmação de email, recuperação de senha ou MFA como funcionalidades prontas.

Refresh emite novos tokens, mas não há armazenamento de revogação/replay protection. Logout elimina cookies do navegador, não revoga cópias já obtidas. Na revisão de 07/10, login por senha/Google bloqueia conta inativa antes de cookies/mutação. Google exige `email_verified` booleano verdadeiro, subject canônico e rejeita vínculos conflitantes. Associação automática por email só acontece em conta ativa sem vínculo prévio, para Gmail ou Workspace com `hd` assinado; outro email exige login convencional. Não há UI de associação autenticada explícita, nem constraint de unicidade de Google ID homologada no banco.

Regressões offline cobrem conta inativa, ausência de cookies/mutação, mensagens genéricas de falha e associação Google conservadora. Login Google real, controles de enumeração/rate limit e sessão em produção ainda exigem homologação. Este manual não certifica segurança integral.

<a id="limites"></a>
## 11. Limites, admissão e proteção de recursos

### 11.1 Limites de entrada

| Recurso | Limite atual |
| --- | --- |
| Texto/afirmação conferida | 10–5.000 caracteres |
| Lote | 1–10 textos |
| URL recebida/final de análise | Até 512 caracteres; trim/protocolo automático/canonicalização participam; sem truncamento |
| Documento remoto | 2 MiB, até 5 redirecionamentos, tipos de texto permitidos |
| Arquivo de mídia | 25 MiB |
| Imagem | 20 milhões de pixels |
| Áudio/vídeo | Até 120 segundos |
| Vídeo | Até 9 quadros padrão; variável limitada a 3–12 |
| Corpo API geral | 35 MiB (`36700160` bytes), com limites menores por rota |
| Corpo de auth/revisão | 64 KiB |
| PDF snapshot | Relatório até 384 KiB; token até 512 KiB; corpo até 512 KiB + 256 bytes |
| Histórico | 20 itens padrão; até 50 por página |

Formatos reconhecidos incluem PNG/JPEG/WebP/GIF, MP3/Ogg/FLAC/WAV/AAC e contêineres MP4/WebM, sujeitos a stream/decoder válido. Lista de extensão na UI não garante aceitação; a decodificação é a autoridade.

### 11.2 Taxa e concorrência

Padrões por processo: 10 requisições/minuto por IP, 60 globais/minuto, 4 análises simultâneas e até 2 por IP. Login tem limite próprio adicional de 5 tentativas por 15 minutos. Origens de escrita devem corresponder à lista/regex configurada; chamadas sem Origin não ficam automaticamente autenticadas.

Esses controles usam memória do processo: reinício reseta estado; várias réplicas/workers não compartilham contagem. Não são um orçamento financeiro global. Proxy/IP efetivo no deploy precisa ser conferido; não confiar indiscriminadamente em headers enviados pelo cliente.

### 11.3 Prazos de análise

Gemini: 60 s padrão, configurável entre 10 e 90; uma chamada e seu fallback explicitamente configurado compartilham o mesmo deadline. As camadas externas de OCR, inspeção e transcrição não cancelam o cliente aos antigos 12–20 s. No padrão, OCR tem até 100 s (inclui local/Gemini/OpenRouter), inspeção 65 s e áudio 105 s (inclui preparação/AssemblyAI). OCR OpenRouter tem janela externa de 27 s para seu cliente de 25 s, não os antigos 12 s. Outros detectores mantêm 18 s. Esses limites não prometem disponibilidade nem transformam HTTP 503 em sucesso; TTS mantém deadline separado de 20 s.

Interface: texto/conferência/simulador até 150 s, link/mídia/lote até 180 s; autenticação mantém 60 s e PDF 30 s. Aviso de espera acessível pede não reenviar. Proxy/plataforma podem impor limites menores: homologar no ambiente publicado. Não há retry automático pago nem progresso fictício em porcentagem.

### 11.4 Quota diária e tiers legados

| Tier interno | Textuais/dia | Mídias/dia |
| --- | ---: | ---: |
| Standard | 300 | 100 |
| Premium | 10.000 | 5.000 |
| Enterprise | 9.999 | 9.999 |

Esses valores são os do código, não planos comerciais, preços ou recomendação de orçamento. Enterprise não é ilimitado e o limite textual não é monotônico em relação a Premium.

**Visitante não tem quota diária implementada**: `verify_limit` retorna sem contar para usuário ausente. Permanece sujeito à admissão, mas não a um limite diário de 30. Comentários legados não devem ser usados como promessa.

Contagem usa registros persistidos; não reserva atomicamente consumo antes de todas as chamadas externas e pode não contabilizar falhas que custaram ao fornecedor. Conclusão: configurar chaves não garante controle financeiro completo. Para acesso ampliado, implementar admissão/orçamento compartilhado, reserva atômica e calendário de quota consistente.

<a id="ambiente"></a>
## 12. Variáveis de ambiente: inventário completo

### 12.1 Por que `.env` e `.env.example` diferem

`.env.example` é um modelo público, com nomes e valores ilustrativos/defaults. `.env` é privado, contém chaves reais e escolhas do ambiente. Não é esperado que sejam idênticos; espera-se que o template liste as configurações suportadas sem revelar segredos.

Copiar tudo do `.env` local para Railway é arriscado: pode substituir banco remoto por SQLite, CORS/HTTPS por localhost, defaults de teste por produção e opções pagas por habilitações indevidas. Copiar apenas variáveis necessárias, conferir cada valor e preservar referências corretas. Não colar segredos no chat, issue, README, screenshot ou RAW Editor compartilhado.

**Sincronizado em 07/10:** `.env.example` agora inclui `DATABASE_URL` com SQLite identificado como LOCAL, e `GEMINI_REQUEST_TIMEOUT_SECONDS`. Railway deve usar a referência privada ao PostgreSQL, não o exemplo SQLite. Opções adicionais de runtime continuam descritas no inventário abaixo; nenhum segredo privado foi copiado.

### 12.2 Backend: ambiente, sessão e recursos

| Variável | Valor/papel | Cuidado |
| --- | --- | --- |
| `APP_ENV` | `development` local; `production` remoto | Produção muda exigências de segredo |
| `DATABASE_URL` | PostgreSQL remoto; SQLite só local/teste | Ausente no template atual; não publicar credenciais |
| `JWT_SECRET` | Segredo de sessão | Pelo menos 32 caracteres, aleatório/estável |
| `JWT_ALGORITHM` | Padrão `HS256` | Runtime adicional; mudança exige revisão de compatibilidade |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Padrão 60 | Runtime adicional |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Padrão 7 | Runtime adicional; não implica revogação |
| `HMAC_SECRET_KEY` | PDF, revisão e registro com finalidades próprias | Independente do JWT; rotação afeta capacidades/registros |
| `COOKIE_SECURE` | `false` local; `true` HTTPS | Não usar false no deploy HTTPS |
| `COOKIE_SAME_SITE` | `lax` local; `none` cross-site HTTPS | Navegador pode bloquear cookie terceiro |
| `CORS_ORIGINS` | Origens exatas separadas por vírgula | Incluir protocolo/porta; não usar `*` com credenciais |
| `CORS_ORIGIN_REGEX` | Opcional, vazia por padrão | Regex ampla permite origens indevidas; preferir lista exata |
| `GOOGLE_CLIENT_ID` | ID OAuth público, também usado para verificar audiência | Não é client secret nem chave Gemini |
| `ANALYSIS_REQUESTS_PER_MINUTE` | 10 padrão | Por IP/processo |
| `ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE` | 60 padrão | Por processo, não orçamento global |
| `ANALYSIS_MAX_CONCURRENT` | 4 padrão | Até 2 por IP no middleware |
| `API_MAX_BODY_BYTES` | 36700160 padrão | Rotas específicas têm limites menores |
| `VIDEO_MAX_FRAMES` | 9 padrão; clamp 3–12 | Mais quadros podem aumentar consumo de detectores |
| `MIN_CONFIDENCE_THRESHOLD` | 0.75 no template | Legado; não altera os limiares ativos da política de evidência |
| `PORT` | Injetada pela hospedagem | Docker respeita variável; não fixar porta incompatível no Railway |

### 12.3 Leitura, checagens e modelos

| Variável | Papel | Condição |
| --- | --- | --- |
| `GEMINI_API_KEY` | Credencial Gemini | Backend somente |
| `GEMINI_MODEL_NAME` | Modelo principal | Template/default `gemini-3.8-flash`; texto respondeu em 07/10, OCR permaneceu indisponível; não é homologação multimodal |
| `GEMINI_REQUEST_TIMEOUT_SECONDS` | Deadline total da chamada | 60 s padrão; inteiro ASCII entre 10 e 90; inválido volta a 60; fallback explícito compartilha o prazo |
| `GEMINI_FALLBACK_MODELS` | Alternativas explícitas | Não habilitar modelo pago sem orçamento |
| `GEMINI_MEDIA_MODEL_NAME` | Modelo multimodal separado | Vazio herda principal; conferir suporte a mídia |
| `GEMINI_TTS_MODEL` | Voz educativa | Template contém `gemini-3.8-flash-tts`; default não comprova disponibilidade |
| `LOCAL_OCR_ENABLED` | Tesseract local primeiro | Exige instalação e idiomas |
| `OPENROUTER_API_KEY` | Credencial OpenRouter | Backend somente |
| `OPENROUTER_ENABLED` | Habilita alternativa | Pode ficar false sem chave/quota |
| `OPENROUTER_MODEL` | Padrão `openrouter/free` | Somente rota gratuita ou IDs `:free` aceitos pelo cliente |
| `OPENROUTER_FALLBACK_MODELS` | Alternativas gratuitas | Sem fallback pago |
| `OPENROUTER_DAILY_LIMIT` | 40 padrão, limitado a 1–40 | Contagem local por processo, não por conta/projeto inteiro |
| `GOOGLE_FACT_CHECK_KEY` | Consulta de checagens | Ativar Fact Check Tools API; não é chave OAuth |
| `SERPERAPI_KEY` | Pesquisa/contexto Serper | Diferente da SerpAPI |
| `SERPAPI_KEY` | Busca reversa opcional SerpAPI | Revogar/rotacionar se exposta; fluxo real ainda pendente |
| `ASSEMBLYAI_API_KEY` | Transcrição alternativa | Conferir créditos e retenção |
| `AUDIO_TRANSCRIPTION_PROVIDER` | Ordem de transcrição | Template `gemini`; controles recentes preferiram `assemblyai` |

IDs de modelos acima são **valores presentes no repositório**, não garantia de existência, gratuidade ou suporte no catálogo atual. Verificar [modelos Gemini](https://ai.google.dev/gemini-api/docs/models) e [variantes gratuitas OpenRouter](https://openrouter.ai/docs/guides/routing/model-variants/free) antes de ativar.

### 12.4 Detectores e ferramentas auxiliares

| Variável | Papel | Condição |
| --- | --- | --- |
| `SIGHTENGINE_API_USER`, `SIGHTENGINE_API_SECRET` | Credenciais Sightengine | Modelo/plano autorizado, não basta credencial válida |
| `SIGHTENGINE_AUDIO_ENABLED` | `ai_speech` opt-in | false até conferir acesso/preço e homologar |
| `HIVE_API_VERSION` | `v2`/`v3` | Credenciais/formatos diferentes |
| `HIVE_API_KEY` | Compatibilidade Hive v2 | Não libera automaticamente todas as cabeças |
| `HIVE_IMAGE_API_KEY`, `HIVE_DEEPFAKE_API_KEY` | Projetos v2 de imagem/facial | Projetos/modelos apropriados |
| `HIVE_AUDIO_API_KEY`, `HIVE_TEXT_API_KEY` | Projetos v2 áudio/texto | Não tratar transcrição como detector |
| `HIVE_V3_API_KEY` | Secret Key v3 | Não confundir com Access Key ID mostrado na tela |
| `HIVE_V3_MEDIA_TYPES` | Opt-in de modalidades v3 | Vazio mantém chamadas pausadas; `image,audio` pode consumir saldo |
| `HUGGINGFACE_API_TOKEN` | Autorização de inferência | Token não hospeda detector |
| `HUGGINGFACE_IMAGE_API_URL` | Endpoint oficial HTTPS explícito | Sem URL, integração não configurada |
| `HUGGINGFACE_AI_LABEL` | Classe positiva exata | `artificial` default; deve coincidir com modelo; sem voto |
| `EXIFTOOL_ENABLED` | Metadados locais | Ferramenta instalada; EXIF não comprova origem |
| `C2PATOOL_ENABLED` | Inspeção C2PA opcional | Runtime permanece sem confiança/voto até homologação |
| `C2PATOOL_TRUST_ANCHORS` | Âncoras que a CLI pode ler | Presença da variável não certifica trust; validar CLI/versão/corpus |
| `TINEYE_API_KEY` | Busca reversa auxiliar | Sem homologação completa atual |
| `WAYBACK_API_ENABLED` | Consulta histórica auxiliar | Rede externa; não prova data/autoria de toda mídia |
| `GPTZERO_API_KEY` | Detector textual auxiliar legado | Não é prova factual |
| `VIRUSTOTAL_API_KEY` | Roteiro futuro | Nenhuma reputação/malware pronta só por cadastrar |

### 12.5 WhatsApp e frontend

| Variável | Destino/papel | Cuidado |
| --- | --- | --- |
| `WHATSAPP_BOT_ENABLED` | Backend; false padrão | Ativação não provisiona gateway |
| `WHATSAPP_WEBHOOK_SECRET` | Backend; autenticação do evento | Forte, pelo menos 32 caracteres |
| `WHATSAPP_HISTORY_ENABLED` | Backend; false padrão | Habilitar só com retenção definida |
| `WHATSAPP_HASH_SECRET` | Backend; pseudonimização | Independente, pelo menos 32 caracteres |
| `EVOLUTION_API_URL`, `EVOLUTION_INTERNAL_URL` | Endereços de gateway | Infraestrutura opcional, não homologada |
| `EVOLUTION_API_KEY` | Segredo do gateway | Compose lê interpolação do ambiente/root `.env`, não automaticamente `backend/.env` |
| `PUBLIC_FRONTEND_URL` | Backend; URL em respostas educativas | Runtime adicional; revisar domínio correto |
| `VITE_API_URL` | Frontend; origem pública do backend | **Sem `/api`**; código adiciona prefixo |
| `VITE_GOOGLE_CLIENT_ID` | Frontend; ID OAuth público | Igual ao client ID validado no backend |
| `VITE_API_PROXY_TARGET` | Processo Vite local; alvo do proxy | Não é segredo; Compose usa `http://backend:8000` |

### 12.6 Perfil mínimo seguro de produção

Exemplo sem credenciais: completar pelo painel privado, preservando chaves/referências válidas. **Não colar valores vazios sobre segredos existentes.**

```dotenv
APP_ENV=production
COOKIE_SECURE=true
COOKIE_SAME_SITE=none
CORS_ORIGINS=https://verifybr.vercel.app
CORS_ORIGIN_REGEX=
LOCAL_OCR_ENABLED=true
EXIFTOOL_ENABLED=true
C2PATOOL_ENABLED=false
VIDEO_MAX_FRAMES=9
OPENROUTER_MODEL=openrouter/free
OPENROUTER_DAILY_LIMIT=40
SIGHTENGINE_AUDIO_ENABLED=false
HIVE_V3_MEDIA_TYPES=
WHATSAPP_BOT_ENABLED=false
WHATSAPP_HISTORY_ENABLED=false
ANALYSIS_REQUESTS_PER_MINUTE=10
ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE=60
ANALYSIS_MAX_CONCURRENT=4
API_MAX_BODY_BYTES=36700160
```

Adicionar separadamente `DATABASE_URL` de referência do serviço Postgres, `JWT_SECRET`, `HMAC_SECRET_KEY` e apenas as credenciais/modelos habilitados. Se não quiser chamadas OpenRouter, usar `OPENROUTER_ENABLED=false`. A ausência de detectores não deve impedir a interface de explicar cobertura insuficiente.

<a id="instalacao"></a>
## 13. Instalação local e Docker

### 13.1 Pré-requisitos e cuidado com o ambiente existente

Docker/Compose para o caminho integrado; ou Python 3.11, Node 22, PostgreSQL/local SQLite e ferramentas de mídia para execução nativa. Dependências podem exigir rede durante instalação/build; testes offline não equivalem a instalação offline universal.

Executar comandos a partir da raiz de **um checkout escolhido**. Há um repositório original e uma revisão local; não misturar `.env`, venv ou banco entre eles. O Compose usa nomes fixos de contêiner/portas: conferir `docker ps` antes de iniciar. Não parar/remover serviços existentes só porque há colisão.

### 13.2 Preparar configuração privada

Criar `backend/.env` usando o template como referência em editor/gerenciador de segredos. Não substituir `.env` existente. Em desenvolvimento, adicionar `CORS_ORIGINS=http://localhost:5174`, pois a porta publicada pelo Compose é 5174, diferente do 5173 do template.

Pode começar sem chaves externas para testar navegação/erros; análises sem evidência podem ser inconclusivas. `HMAC_SECRET_KEY` estável permite PDF/revisão mesmo em dev; usar segredo de teste próprio, não segredo da produção.

### 13.3 Compose de desenvolvimento

```bash
docker compose config --services
docker compose up --build -d db backend frontend
docker compose ps
docker compose logs --tail=100 backend
```

`config --services` evita imprimir a configuração resolvida com segredos. Não usar `docker compose config` completo em saídas compartilhadas.

| Serviço | Acesso do host | Comunicação interna |
| --- | --- | --- |
| Frontend | `http://localhost:5174` | Vite 5173; proxy para backend 8000 |
| Backend | `http://localhost:8001` | Uvicorn 8000 |
| PostgreSQL | `localhost:5433` | `db:5432` |
| Evolution opcional | `localhost:8090` | Fora do caminho principal |

Backend usa `--reload` e bind mount; frontend usa servidor de desenvolvimento. Banco tem credenciais ilustrativas `verify`/`verify_pass` e volume persistente. A variável `DATABASE_URL` do Compose aponta ao serviço `db` e sobrepõe a do env file. **Não usar esse Compose como produção nem expor suas portas à internet.**

Ao terminar, só parar esta stack se ela for realmente sua e estiver identificada. `docker compose down` não remove volumes por padrão; **não usar `down -v`** sem intenção explícita de apagar o banco e backup verificável.

### 13.4 Execução nativa

Na raiz, preparar venv novo apenas se ele ainda não existir:

```bash
python3.11 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements.txt
```

Em um terminal com diretório `backend`:

```bash
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Em outro com diretório `frontend`:

```bash
npm ci
npm run dev -- --host 127.0.0.1
```

Frontend usa proxy `/api` para localhost:8000 quando não há `VITE_API_URL`. Para essa execução, CORS padrão localhost:5173 precisa coincidir com a origem realmente usada. `localhost` e `127.0.0.1` são origens distintas: cadastrar a usada ou ambas explicitamente.

Ferramentas de sistema: `ffmpeg`, `ffprobe`, `exiftool`, `tesseract` com `por`/`eng`; para testes PDF, `pdftotext`/`pdftoppm` do Poppler. Instalação depende do sistema operacional; Dockerfiles backend já instalam mídia/ExifTool/Tesseract, mas não c2patool ou Poppler de teste.

### 13.5 Imagens Docker e diferenças de contexto

```bash
docker build -t verify-backend-local .
docker build -t verify-backend-context-local backend
```

Ambos são backend, com contextos diferentes. Não combinar Dockerfile da raiz, que copia `backend/`, com contexto já dentro de `backend`. `.dockerignore` exclui `.env*`, bancos locais e caches dos contextos backend; revisar arquivo antes de acrescentar material privado.

Os Dockerfiles atuais não definem usuário não root. O ambiente de testes executado de forma restrita em etapa anterior não torna a imagem de produção automaticamente não root. Hardening e build final são pendências.

`frontend/Dockerfile` possui build Node 20 e nginx com fallback SPA/proxy de `/api` para `backend:8000`; não é o caminho usado pela Vercel nem pelo Compose de desenvolvimento. Usa `npm install`; alinhar a versão e instalação determinística no pacote de reprodução. Não presumir que esse nginx esteja homologado só porque o Vite passou.

<a id="provedores"></a>
## 14. APIs: obtenção e ativação segura

### 14.1 Sequência recomendada sem novas contratações

Conferir o [status/configuração e fontes de 08/10](STATUS-VERIFICACOES-2026-10-08.md), que antecede observações históricas deste manual. Mais chaves não homologa modalidades, orçamento nem precisão.

1. Ferramentas locais: FFmpeg/ffprobe, Tesseract e ExifTool, sem chave.
2. Google Fact Check para recuperação de evidências.
3. Gemini e/ou OpenRouter gratuito para leitura/extração auxiliar, com modelo acessível.
4. AssemblyAI somente com crédito gratuito confirmado, se necessário para ASR.
5. Detectores já autorizados, dentro de saldo explícito. Manter demais desligados.
6. Não contratar endpoint GPU do HF nem ligar Hive pago para “completar a lista”.

Planos, quotas e catálogos mudam; este manual não promete gratuidade permanente. Verificar saldo, renovação/cobrança automática, modelo autorizado e retenção no painel antes de teste real. Usar controles próprios/fictícios, não mídia privada de terceiros.

### 14.2 Google Fact Check

Abrir [Fact Check Tools API no Google Cloud](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com), selecionar projeto, ativar API, criar chave em [Credenciais](https://console.cloud.google.com/apis/credentials) e restringir à API pertinente. Colocar em `GOOGLE_FACT_CHECK_KEY` somente no backend.

O Verify consulta checagens; não publica ClaimReview. A [documentação oficial](https://developers.google.com/fact-check/tools/api) distingue pesquisa e recursos de publicação. Busca vazia ou sem correspondência literal continua sem conclusão; chave válida não garante cobertura de qualquer tema.

### 14.3 Gemini e login Google são diferentes

Chave Gemini: [Google AI Studio](https://aistudio.google.com/app/apikey), conforme [guia oficial](https://ai.google.dev/gemini-api/docs/api-key). Escolher modelo explicitamente acessível e compatível com texto/imagem/áudio/TTS. Conferir [preços e limites do plano](https://ai.google.dev/gemini-api/docs/pricing); nível gratuito de uma função não garante todas as funções.

Login Google: cliente OAuth web em Google Cloud; definir origens autorizadas. Copiar o client ID público para backend `GOOGLE_CLIENT_ID` e frontend `VITE_GOOGLE_CLIENT_ID`. Não é necessário expor client secret no browser. Ver [configuração oficial do client ID](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid).

### 14.4 OpenRouter gratuito

Criar/gerenciar chave em [OpenRouter Keys](https://openrouter.ai/settings/keys), guardar no backend e usar `openrouter/free` ou modelo `:free` permitido. O cliente atual restringe preço máximo zero, limita chamadas e não faz fallback pago. Disponibilidade/rate limit e suporte a visão/estrutura variam; conferir [variantes gratuitas](https://openrouter.ai/docs/guides/routing/model-variants/free).

Teste registrado com `liquid/lfm-2.5-2.6b:free` é histórico, não recomendação de disponibilidade permanente. Resposta truncada/fora de contrato é falha, não texto “corrigido” inventado. Limite local não agrega vários serviços ou réplicas.

### 14.5 Hive v2 versus v3

Entrar no [portal Hive](https://portal.thehive.ai/). V2 usa chave do **projeto/modelo**; verificar imagem, deepfake e áudio separadamente. O [guia oficial de autenticação v2](https://docs.thehive.ai/reference/authentication) não deve ser usado como instrução de credencial v3.

O cliente v3 implementado usa Secret Key/Bearer e classes específicas. **Access Key ID visível na tela não é Secret Key**. Credencial válida sem permissão/modelo/saldo não fornece cobertura. Na revisão, imagem/facial v3 compartilham uma chamada; continuam um fornecedor.

Deixar `HIVE_V3_MEDIA_TYPES` vazio enquanto chamadas pagas estiverem pausadas. Vídeo envia quadros como imagens, podendo multiplicar consumo. Autorizações pontuais antigas de gasto não são autorização contínua. Nova homologação paga exige limite explícito autorizado e preço confirmado.

### 14.6 Hugging Face

Criar token restrito em [Tokens HF](https://huggingface.co/settings/tokens), conforme [guia de tokens](https://huggingface.co/docs/hub/security-tokens). Conferir permissão de inferência e acesso ao modelo. Escolher endpoint já hospedado e autorizado; token sozinho não disponibiliza um detector. [Inference Providers](https://huggingface.co/docs/inference-providers/index) descreve alternativas de infraestrutura.

Cliente atual só aceita HTTPS oficial em `router.huggingface.co`, `api-inference.huggingface.co` ou subdomínio `.endpoints.huggingface.cloud`, sem credenciais/query/fragmento na URL. Espera lista de classes e classe positiva exata configurada em `HUGGINGFACE_AI_LABEL`. Modelo sem a classe esperada retorna resposta inválida, não probabilidade zero.

Mesmo que transporte funcione, HF permanece experimental e sem voto, pois controles conhecidos falharam. Não provisionar endpoint dedicado pago sem autorização. Não resolver uma classificação errada apenas invertendo classe para favorecer exemplos já vistos; usar corpus independente.

### 14.7 Sightengine e AssemblyAI

Sightengine: [painel](https://dashboard.sightengine.com/) e [documentação](https://sightengine.com/docs/). Obter API user/secret e conferir quais modelos estão incluídos. Acesso de imagem não implica acesso a fala sintética. `SIGHTENGINE_AUDIO_ENABLED=false` até autorização/preço e teste real do modelo.

AssemblyAI: [painel](https://www.assemblyai.com/dashboard/) e [documentação](https://www.assemblyai.com/docs). Credencial em `ASSEMBLYAI_API_KEY`; `AUDIO_TRANSCRIPTION_PROVIDER=assemblyai` seleciona preferência quando disponível. Conferir créditos/retenção; testar português, negação, valores e ruído. ASR não substitui detector de voz sintética.

### 14.8 Serper e SerpAPI

[Serper](https://serper.dev/) fornece a chave `SERPERAPI_KEY` para pesquisa/contexto. [SerpAPI — gerenciar chave](https://serpapi.com/manage-api-key) fornece `SERPAPI_KEY`, usada em recursos distintos como busca reversa. Não intercambiar nomes ou credenciais.

A chave SerpAPI anteriormente exposta foi informada como revogada pelo responsável. Não reproduzir a chave antiga, nem considerar a nova validada apenas porque foi cadastrada. Evitar publicar mídia privada para obter uma URL exigida por busca reversa.

### 14.9 Critério de ativação de qualquer fornecedor

Registrar: modelo/endpoint, formato esperado, finalidade, permissão, quota, preço, dado enviado, retenção, timeout, resposta inválida e controles positivos/negativos. Primeiro validar parser/erro sem rede; depois uma chamada real autorizada; finalmente corpus e fluxo UI. Somente o papel efetivamente validado pode ser anunciado.

<a id="deploy"></a>
## 15. Publicação no Railway e na Vercel

Esta seção é um procedimento a executar com autorização; **a documentação não realizou deploy, commit, push ou mudança de variáveis**.

### 15.1 Antes de publicar

- Decidir piloto restrito versus público e fechar os P0 correspondentes.
- Conferir alterações no checkout revisado e transferir de forma controlada ao repositório de entrega, preservando trabalho preexistente.
- Verificar ausência de segredos/arquivos privados em Git e imagens.
- Executar regressões, PostgreSQL, build e CI; registrar SHA candidato.
- Fazer backup verificável antes de mudanças de schema; ensaiar migrations em staging.
- Conferir saldo/expiração dos hosts e plano de reserva local.

### 15.2 Backend Railway

1. Selecionar serviço do backend, não o serviço PostgreSQL.
2. Escolher um contexto: **Root Directory `backend` + Dockerfile dessa pasta**, ou raiz + Dockerfile da raiz. Não misturar.
3. Confirmar o arquivo `railway.toml` realmente usado e comando que respeita `$PORT`.
4. Vincular `DATABASE_URL` ao Postgres correto. Referência `${{Postgres.DATABASE_URL}}` só serve se o nome do serviço for exatamente Postgres; usar seletor de referência do painel.
5. Definir ambiente de produção, segredos independentes, cookies HTTPS e origem exata do frontend.
6. Ativar apenas fornecedores autorizados; manter Hive pago, WhatsApp e C2PA não homologados desabilitados.
7. Revisar alterações pendentes no painel antes de aplicar; registrar qual commit/configuração foi publicado sem registrar segredos.
8. Usar `/ready` para health check de implantação. Conferir build, ferramentas, conexão e caminhos, além de `/health`.

Fontes oficiais: [Dockerfiles Railway](https://docs.railway.com/builds/dockerfiles), [variáveis](https://docs.railway.com/variables), [health checks](https://docs.railway.com/deployments/healthchecks). Health check de implantação não substitui monitoramento contínuo nem testes dos fornecedores.

### 15.3 Frontend Vercel

Configuração do projeto: Root Directory `frontend`; framework Vite; build `npm run build`; output `dist`. `frontend/vercel.json` contém fallback SPA. Ver [Vite na Vercel](https://vercel.com/docs/frameworks/frontend/vite).

Configurar `VITE_API_URL` com a **origem do backend, sem `/api`**, e opcionalmente `VITE_GOOGLE_CLIENT_ID`. Exemplo: `https://verify-production-ead7.up.railway.app`, se continuar sendo o domínio do serviço escolhido. Esse endereço é uma referência do projeto, não comprovação de saúde ou versão atual.

Separar variáveis de Preview e Production: preview não deve consultar dados reais da produção por acidente. Valores Vite entram no build; alteração exige novo build/deploy. Não colocar `DATABASE_URL`, JWT, HMAC ou chaves de fornecedores na Vercel frontend. Ver [ambientes de variáveis Vercel](https://vercel.com/docs/environment-variables).

Sem `VITE_API_URL`, a SPA usa `/api` relativo. Na configuração estática atual da Vercel não há proxy backend: a reescrita pode devolver HTML em vez de JSON. Isso costuma aparecer como erro de rede/JSON ou login quebrado, não como falha do detector.

### 15.4 Homologação do commit publicado

| Grupo | Verificação |
| --- | --- |
| Versão | SHA esperado corresponde a frontend/backend publicados; não basta push ou deploy “Ready” |
| Operação | `/health`, `/ready`, ferramentas e capabilities coerentes; segredos não aparecem |
| Conta | Cadastro/login/logout/refresh, conta inativa, troca entre duas contas e isolamento |
| Entradas | Texto, link HTTPS público autorizado, imagem, áudio e vídeo com origem documentada |
| Revisão | OCR/ASR aguarda conferência em `/app`; texto original e confirmado preservados |
| Resultado | Estado, fontes, indisponibilidade e cobertura iguais às evidências reais |
| Histórico/PDF | Reabrir registro correto, baixar arquivo, salvá-lo e abri-lo; mesma análise |
| Falhas | Quota/timeout/credencial ausente e arquivo inválido não viram veredito conclusivo |
| Uso | Celular, Modo Fácil, teclado, zoom e movimento reduzido |
| Orçamento | Nenhuma rota/modelo pago inesperado; custos registrados sem segredos |

### 15.5 Git, CI e publicação não são a mesma etapa

Revisar diff → testes locais → commit candidato → push autorizado → CI remoto → preview/staging → homologação → promoção/publicação autorizada → smoke test. Workflow atual só testa: não publica e não configura sozinho branch protection ou ordem dos autodeploys.

Se Vercel/Railway publicarem automaticamente antes dos checks, criar fluxo de promoção controlada ou gate equivalente. Registrar decisão. Não afirmar que todo push está protegido por testes sem verificar configuração real.

<a id="pdf"></a>
## 16. PDF, revisão humana e registro de integridade

### 16.1 Snapshot PDF

Token `vpdf1`, assinado por HMAC, finalidade própria e validade de 1 hora. Para usuário autenticado, vinculado à conta; visitante recebe capacidade bearer. É **assinado, não criptografado**: quem possui um token visitante pode usar a capacidade até expirar, e seu conteúdo não deve ser tratado como secreto por criptografia.

Assinatura, finalidade, validade, dono e estrutura são verificados antes de renderização. Limites impedem snapshot enorme; relatório incompatível não é truncado silenciosamente para fingir exportação. Em produção sem HMAC forte, análise pode continuar, mas PDF/revisão ficam indisponíveis.

Texto/link/lote/texto conferido usam renderer textual. Mídia usa renderer forense. Não adicionar SHA de texto como prova de verdade ou camadas de imagem ao PDF textual. Valores ausentes são identificados, zero é preservado e sinais 0–1 são não calibrados.

Tokens são anexados após persistência, removidos do banco/JSON técnico copiável e não devem ir para logs. Reabertura de registro compatível gera capacidade a partir do resultado original. Legado incompleto não recebe snapshot inventado.

Exportar não consome quota diária de análise, mas a rota permanece sujeita à origem de escrita, taxa/concorrência do middleware e limite específico de corpo. Exportações repetidas podem retornar 429; não apresentar o PDF como caminho ilimitado para contornar admissão.

### 16.2 Revisão de texto extraído

Token `vrev1`, finalidade/chave derivada distinta, validade de 15 minutos e limite de token de 32 KiB. Enviar `text` de 10–5.000 caracteres sem HTML e token ao endpoint de revisão. Confirmar dono antes de pesquisar/persistir; erro/expiração exige fluxo válido novamente.

O novo relatório preserva leitura original, método, fornecedor, mídia/hash/nome quando disponíveis e datas, além do texto confirmado e flag de mudança. Não reescreve relatório forense da mídia. Revisão humana reduz risco de pesquisar uma transcrição errada, mas não prova a afirmação.

### 16.3 Registro SHA-256 versus C2PA

O registro compara bytes com um registro anterior assinado pelo serviço. Se bytes mudam, hash muda; se bytes permanecem, isso não prova que a cena é verdadeira. Qualquer arquivo, inclusive sintético, pode ser registrado.

C2PA é um caminho separado. Strings `c2pa`/`jumb` detectadas no binário são marcadores não validados. `c2patool` não vem instalado nos Dockerfiles atuais. A CLI pode ler `C2PATOOL_TRUST_ANCHORS`, mas a presença da variável e status vazio não comprovam cadeia validada. Na revisão atual, runtime informa `trusted=false`/sem voto até homologação real. A origem sintética só é inspecionada nas ações/URI exatas previstas; comentários/substrings não certificam procedência.

<a id="seguranca"></a>
## 17. Segurança, privacidade e lacunas conhecidas

### 17.1 Controles existentes

HTTP-only nas sessões, hashing Argon2, exigência de segredo JWT em produção, isolamento de histórico, proteção de origens de escrita, limites de corpo/taxa/concorrência, validação real de mídia, consulta pública restrita e tokens assinados com finalidade/validade. API usa `Cache-Control: no-store` e headers de proteção.

Esses controles têm testes específicos, mas não equivalem a auditoria integral, proteção contra todo XSS/abuso ou certificação jurídica. `no-store` não remove cópias exportadas, extensões maliciosas ou conteúdo já enviado a terceiros.

### 17.2 Dados que podem sair do servidor

| Etapa | Dados potencialmente enviados |
| --- | --- |
| Busca/checagem | Texto/afirmações/termos de pesquisa |
| OCR/inspeção remota | Imagem ou quadros derivados |
| Transcrição | Áudio ou faixa extraída de vídeo |
| Detector | Imagem, quadro, áudio ou trecho, conforme modalidade |
| Busca reversa | Imagem/URL conforme integração; não publicar arquivo privado para facilitar consulta |
| TTS | Texto de resposta educativa |
| Login Google | Token/atributos de identidade necessários ao login |

Ferramentas locais podem evitar envio em determinadas etapas, não em todo o pipeline. Temporários locais não significam que o fornecedor não retenha o conteúdo. Verificar políticas de cada conta e explicar envio antes da submissão de dados reais.

### 17.3 Pendências antes de uso público irrestrito

- Definir retenção por classe de dado e implementar exclusão de conta/histórico, incluindo relações, caches e tratamento de backups.
- Informar processamento por terceiros, finalidades e contato responsável; alinhar telas de privacidade ao que realmente acontece.
- Homologar isolamento/conta inativa/OAuth/revogação e fortalecer política de senha conforme escopo.
- Criar migrations versionadas e backup/restauração testados fora da produção.
- Implementar controle de orçamento apropriado ao acesso: visitantes, falhas cobradas, concorrência e múltiplos processos.
- Revisar execução não root, dependências, segredos, armazenamento e observabilidade sem dados sensíveis.
- Corrigir divergência de comprimento de URL e formalizar modelos de resposta/API.
- Auditar C2PA/trust antes de qualquer promessa criptográfica de procedência.

A lista é um plano de engenharia, não parecer legal sobre conformidade. Não coletar mídia íntima, documentos pessoais ou voz/imagem de terceiros sem finalidade e autorização adequadas ao teste.

### 17.4 Segredos e rotação

Não comitar `.env`; templates têm apenas nomes/defaults seguros. `.gitignore` e `.dockerignore` ajudam, mas não apagam segredo já versionado. Antes de publicar, revisar arquivos rastreados e diffs sem imprimir valores. Se exposto, revogar/rotacionar no fornecedor e atualizar ambientes privados.

JWT rotacionado invalida sessões. HMAC rotacionado invalida capacidades e pode afetar verificação de registros antigos; planejar compatibilidade/identificação de chave, não trocar casualmente. Backup não deve armazenar `.env` no repositório público.

<a id="testes"></a>
## 18. Testes, corpus e evidências

### 18.1 Pirâmide de validação

1. **Unidade/política:** respostas simuladas corretas, insuficientes, contraditórias e malformadas.
2. **Integração offline:** rotas, banco descartável, tokens, mídia local e PDF.
3. **Interface local:** navegação, revisão, conta, histórico e download com fronteiras registradas.
4. **Transporte real:** fornecedor autorizado com quota e dado controlado.
5. **Corpus conhecido:** positivos/negativos de origem documentada, sem treinar/ajustar no conjunto final.
6. **Deploy:** todos os componentes no commit publicado, CORS/cookies/ferramentas/banco reais.

Passar uma camada não conclui as seguintes. Fazer todas as análises ficarem inconclusivas também não demonstra eficácia: controles com evidência elegível suficiente devem produzir o estado esperado.

### 18.2 Comandos de regressão

No diretório `backend`, com venv e ferramentas de teste instalados:

```bash
venv/bin/python -B scripts/run_offline_tests.py
```

Runner ignora dotenv, limpa credenciais de teste, gera SQLite temporário, bloqueia transportes HTTP reais e exige zero testes ignorados. Precisa de FFmpeg/ffprobe e Poppler. Não é comando de benchmark de precisão.

No diretório `frontend`:

```bash
npm ci
npm test
npm run build
```

Não há script de lint/TypeScript declarado atualmente. Acrescentar qualidade estática somente com configuração/testes próprios, sem alegar que já passou.

### 18.3 PostgreSQL descartável

`run_offline_tests.py --postgres-test-url` aceita driver `postgresql+asyncpg`, host loopback, nome contendo `test` e sem query extra. **Os testes recriam tabelas.** Nunca apontar produção, túnel de produção ou banco compartilhado. Usar serviço descartável próprio e validar alvo antes de executar.

O workflow [tests.yml](../.github/workflows/tests.yml) contém serviço de teste Postgres e jobs SQLite/PostgreSQL. Ele não usa secrets dos provedores nem faz deploy. Instalação de dependências utiliza rede; a suíte deve permanecer sem chamadas reais.

### 18.4 Scripts de apoio

| Script | Finalidade | Restrição |
| --- | --- | --- |
| `run_offline_tests.py` | Regressões sem dotenv/API real | Banco próprio; PostgreSQL opt-in recria tabelas |
| `local_release_server.py` | Servidor descartável da primeira etapa | Não é configuração de deploy |
| `release_http_probe.py` | Histórico/PDF/isolamento local | Somente localhost; dados fictícios |
| `validation_ui_server.py` | Harness UI e fronteiras de requisições | Não substituir autenticação/configuração de produção |
| `prepare_validation_fixtures.py` | Preparar controles declarados | Não transformar TTS em “voz humana real” |
| `prepare_extended_controls.py` | Transformações/controlos de extração | Derivados não são amostras independentes |
| `offline_validation_matrix.py` | Dimensões controladas da matriz | Não homologa fornecedores reais |
| `provider_probe.py`, `free_provider_probe.py`, `multimodal_probe.py` | Transporte real opt-in | Podem consumir quota/créditos; revisar flags/escopo antes de usar |
| `evaluate_predictions.py` | Métricas a partir de rótulos/predições | Não cria ground truth nem corpus independente |

Consultar `--help` e o registro da etapa antes de cada probe. Não executar “todos os scripts” contra `.env` privado: alguns fazem chamadas reais ou criam dados.

### 18.5 Matriz de 30 casos

Distribuição: 10 texto/link, 6 OCR, 6 áudio, 4 imagem e 4 vídeo. Fonte de verdade do andamento: [MATRIZ-VALIDACAO-30-CASOS.md](MATRIZ-VALIDACAO-30-CASOS.md). Registrar expectativa por dimensão: extração, veracidade, origem sintética, cobertura, persistência e exportação.

Oito pendentes exigem cinco originais:

| ID | Entrada necessária | Derivação/expectativa |
| --- | --- | --- |
| AUD04 | Voz humana própria/autorizada com negação, valor e data | Comparar transcrição literal; não certificar identidade |
| AUD05 | Derivado ruidoso/comprimido de AUD04 | Preservar termos críticos ou pedir revisão |
| AUD06 | Voz humana autorizada lendo mensagem financeira fictícia | Triagem do discurso separada da origem da voz |
| IMG01 | Foto própria de objeto/planta, sem rosto/documentos | Origem conhecida por registro; detector baixo não é prova |
| IMG04 | Recorte/brilho convencional de IMG01 | Edição comum não vira automaticamente geração por IA |
| VID02 | Vídeo próprio de objeto/planta, ~10 s, sem fala | Cobertura de quadros, não todo o vídeo |
| VID03 | Compressão/redimensionamento/edição de VID02 | Derivado; não conta como amostra independente |
| VID04 | Vídeo próprio 10–30 s, voz autorizada fora de quadro com termos críticos | Áudio, extração e quadros avaliados separadamente |

Originais: AUD04, AUD06, IMG01, VID02, VID04. Seguir o roteiro/frases exatos da matriz e registrar consentimento, origem, hash e transformações. Nome de arquivo “humano” não comprova origem. Não substituir esses arquivos por TTS/gráfico/vídeo programático e marcar validação humana como concluída.

LNK10 ainda precisa de dimensão HTTPS pública real. `https://example.test/controle.html` foi fixture de transporte simulado: não valida DNS/TLS/acesso público real. Usar página pública própria/autorizada sem dados privados.

### 18.6 Critérios de avaliação

Registrar acertos, erros, abstenções, indisponibilidades e custos por modalidade. Inconclusivos entram nos denominadores definidos; reportar cobertura e erro entre os casos conclusivos separadamente. Transformações da mesma origem precisam permanecer no mesmo grupo/split para evitar vazamento.

Não divulgar “100% de precisão” a partir de 30 controles ou scores de detector. Não reajustar limiares sobre o mesmo conjunto e chamá-lo de avaliação independente. Guardar falhas ASR/HF/OCR existentes; corrigir código não apaga a evidência histórica.

<a id="acessibilidade"></a>
## 19. Acessibilidade e uso por pessoas leigas

Manter linguagem direta, fonte confortável, contraste, botões com área suficiente e resultado compreensível sem cor. Modo Fácil deve simplificar apresentação sem ocultar ausência de fonte ou permitir ações irreversíveis por engano.

Testes mínimos: 320/375/768/1280 px, Modo Fácil ligado/desligado, zoom 200%, teclado, foco, leitor de tela nas ações essenciais e `prefers-reduced-motion`. Evitar cortes, ellipsis em instrução essencial e rolagem horizontal. Scrollbar customizada deve manter rolagem nativa e capacidade de teclado, não substituir por área difícil de operar.

Animações devem ser discretas, canceláveis e não atrasar leitura do relatório. Splash está condicionada ao modo/movimento; validar que não bloqueia acesso repetidamente. Barra/contador não comunica certeza falsa. PDF gerado não foi certificado como PDF acessível/tagged; não declarar equivalência de acessibilidade entre UI e exportação.

Realizar tarefas com 3–5 participantes, se disponíveis: enviar conteúdo, entender inconclusivo, localizar fonte, conferir transcrição, reabrir resultado e sair. Registrar onde precisaram de ajuda, sem coletar dados pessoais desnecessários. Usar [WCAG 2.2 — referência W3C](https://www.w3.org/WAI/WCAG22/quickref/) como checklist, não como declaração automática de conformidade.

<a id="operacao"></a>
## 20. Operação, diagnóstico e contingência

### 20.1 Sinais de saúde

| Sinal | O que comprova | O que não comprova |
| --- | --- | --- |
| `/health` 200 | Processo responde | Banco, modelos, quota ou precisão |
| `/ready` 200 | Consulta read-only do banco, deadline 2 s/cache curto | Schema, escrita, backup ou serviços externos |
| Capabilities configurada | Presença de env/ferramenta | Chave válida, saldo, acesso ao modelo ou operação real |
| Provedor HTTP 200 | Transporte e talvez parser | Rótulo correto ou cobertura do arquivo inteiro |
| CI verde | Cenários automatizados daquele SHA | Homologação de produção e corpus real |
| PDF HTTP 200 | Geração/resposta no backend | Arquivo salvo e aberto pelo navegador |

### 20.2 Logs e acompanhamento

Registrar rota fixa, status, duração, versão, fornecedor/estado sem conteúdo, e contagens agregadas. Não registrar mensagem, imagem, query sensível, SQL com dados, cookie, token ou URL de assinatura. Logs do harness atual registram fronteiras limitadas, não corpos/credenciais.

Definir responsável, frequência de revisão e limiares de alerta por erro/latência/indisponibilidade/custo, após medir baseline. Nenhum monitor recorrente foi configurado por este manual. Custos e saldos precisam ser conferidos nos painéis privados sem copiar chaves.

### 20.3 Diagnóstico por sintoma

| Sintoma | Conferir primeiro | Não fazer |
| --- | --- | --- |
| Frontend recebe HTML em vez de JSON | `VITE_API_URL`, build efetivo, `/api/api`, rewrite SPA | Colocar chave de API no frontend |
| Login funciona local, falha remoto | CORS exato, HTTPS/SameSite/Secure, bloqueio de cookies terceiros | Liberar todas as origens/retirar HTTP-only |
| `/ready` 503 | Referência DATABASE_URL, serviço Postgres, rede, pool/startup | Apontar runner destrutivo ao banco real |
| OCR vazio/errado | Qualidade/rotação, Tesseract por/eng, cobertura de fallback | Completar palavras/valores sem revisão |
| ASR muda negação/valor | Texto original, provedor, silêncio/ruído, revisão | Tratar texto automático como fiel só porque HTTP 200 |
| HF não configurado | Token, endpoint oficial, classe positiva | Provisionar GPU paga automaticamente |
| Hive 401/403/vazio | v2/v3, Secret Key, projeto/cabeça/permissão | Usar Access Key ID como segredo ou ativar todas modalidades |
| OpenRouter 429/JSON inválido | Quota, disponibilidade e resposta estruturada | Fallback pago ou aceitar texto truncado como evidência |
| PDF indisponível | HMAC, prazo/dono, compatibilidade/tamanho, legado | Reanalisar arquivo para fabricar “mesmo” resultado |
| Vídeo sem cobertura | ffprobe/FFmpeg, quadros/estados reais e faixa de áudio | Inferir humano ou fazer média temporal virar consenso |
| Link rejeitado | DNS público, tipo, tamanho, redirect, compressão e layout | Desabilitar validação de IP/TLS |

### 20.4 Backup e restauração — procedimento a homologar

Antes de público: definir frequência, retenção, criptografia/controle de acesso, responsável e destino fora do repositório. Usar mecanismo do provedor ou dump com credencial privada, sem senha literal em comando/log. Registrar momento, schema e versão.

Testar restauração **em banco novo descartável/staging**: conferir contagens, relacionamentos, login de teste e leitura de histórico/PDF compatível. Medir tempo e perda máxima aceitável. Não restaurar sobre produção durante um ensaio. Procedimento ainda não testado; não anunciar “backup garantido”.

### 20.5 Rollback e interrupção segura

Registrar versão anterior funcional e configuração necessária. Retornar código/frontend não desfaz migration, mudança de dado ou rotação de segredo. Compatibilidade de schema precisa ser prevista e ensaiada; evitar comandos destrutivos como reset hard ou remoção de volume para “voltar versão”.

Em falha: limitar efetivamente acesso, suspender camadas com custo/erro, informar indisponibilidade e preservar evidências sem dados pessoais. Não substituir resultado real por mock silencioso em produção. Demonstração gravada/local deve ser rotulada como tal.

### 20.6 Contingência de apresentação

Docker local testado, controles fictícios/autorizados preparados, PDFs/resultados de exemplo identificados e vídeo de reserva. Conferir hospedagem: trial/créditos têm condições e podem expirar, conforme [Railway — free trial](https://docs.railway.com/pricing/free-trial). Não depender de recarga ou cartão de última hora para apresentar.

<a id="entrega"></a>
## 21. Entrega em 14 dias e definição de conclusão

Plano executivo completo: [PLANO-ENTREGA-14-DIAS.md](PLANO-ENTREGA-14-DIAS.md). Referência: 04–17/10/2026, 4 h/dia, 48 h planejadas + 8 h de reserva. Datas futuras indicam planejamento, não execução automática.

Frentes: escopo/orçamento; corpus/qualidade; conta/privacidade; reprodução/CI; publicação/homologação; acessibilidade; documentação/apresentação. Correções locais já existentes reduzem implementação, mas não eliminam repetição no deploy e nos serviços reais.

### Checklist da versão candidata

- [ ] Escopo e acesso real definidos; sem promessa de detector infalível.
- [ ] P0 do escopo escolhido fechados, sem custo ou vazamento inesperado.
- [ ] SHA registrado; regressões atuais em SQLite/PostgreSQL e frontend/build passam.
- [ ] Imagem de deploy correta construída, ferramentas verificadas e segredos fora dela.
- [ ] CI remoto executado; gate/autodeploy entendido e controlado.
- [ ] Cinco modalidades e fluxos auxiliares homologados no commit publicado.
- [ ] Matriz inclui origem, expectativas, falhas e inconclusivos; pendências explicitadas.
- [ ] Fontes pertinentes; nenhum “falso/verdadeiro” baseado apenas em LLM/score/domínio.
- [ ] Revisão preserva original; histórico/PDF mantêm análise; PDF salvo e aberto.
- [ ] Modo Fácil/celular/teclado/zoom/movimento reduzido permitem tarefas essenciais.
- [ ] Documentação seguida por outra pessoa e demonstração/reserva ensaiadas.
- [ ] Para público: retenção/exclusão, migrações, backup/restauração e controles adicionais concluídos.

Uma pendência crítica não vira concluída por falta de prazo. Se não couber, reduzir escopo explicitamente e restringir acesso; entregar apresentação honesta, não anunciar homologação inexistente.

<a id="contribuicao"></a>
## 22. Contribuição, modelos de registro e apresentação

### 22.1 Regras para alterar o projeto

Ler [AGENTS.md](../AGENTS.md) e [general.md](general.md). Preservar alterações preexistentes e segredos. Reproduzir bug em ambiente próprio; acrescentar regressão proporcional; modificar camada responsável; repetir cenário e fluxos afetados. Não introduzir nova API paga, migração em produção ou publicação sem autorização.

Mudança em política exige versionamento, justificativa, controles positivos/negativos e efeito nos legados. Mudança de env exige atualizar template/manual; mudança no relatório exige UI/PDF/histórico coerentes. Testes devem separar mock, transporte real e corpus.

### 22.2 Modelo de bug

```text
ID / prioridade / responsável:
Versão e ambiente (local/staging/prod):
Passos mínimos:
Entrada fictícia/autorizada e origem (sem segredo):
Esperado / observado:
Dimensão afetada: leitura / veracidade / origem / conta / PDF / uso
Fornecedor e estado (sem credencial):
Evidência e impacto:
Correção / regressão / resultado da repetição:
Situação no deploy:
```

### 22.3 Modelo de execução e release

```text
Caso / data / executor / SHA frontend-backend:
Origem, consentimento/licença e grupo da mídia:
Expectativa por dimensão e justificativa:
Configuração de modelos/ferramentas (sem valores secretos):
Serviços chamados, quota/custo autorizado:
Resultado, cobertura, tempo, erro ou abstenção:
Histórico/revisão/PDF/celular:
Diferença e decisão: aprovado / parcial / falhou / pendente
Artefatos sanitizados e próximos passos:
```

Release: SHA + checks + migrations/configuração + modo de acesso + resultados de homologação + limites conhecidos + rollback/backup + responsável. Não preencher “aprovado” sem evidência.

### 22.4 Roteiro de apresentação de 5 minutos

1. Problema e promessa limitada (30 s).
2. Texto/link: mostrar fonte correspondente ou explicar abstenção (60 s).
3. Imagem/áudio: conferir leitura, separar conteúdo da origem sintética (90 s).
4. Vídeo: mostrar recorte de quadros/áudio e limites (45 s).
5. Histórico/PDF da mesma análise e Modo Fácil (45 s).
6. Pendências, orçamento e próximos passos (30 s).

Usar exemplos já ensaiados, sem esconder resultados inconclusivos. Se API/rede falhar, explicar e usar reserva explicitamente identificada. Não apresentar TTS como voz humana real.

<a id="referencias"></a>
## 23. Glossário e referências

| Termo | Significado neste projeto |
| --- | --- |
| Veracidade | Relação da afirmação com evidências factuais correspondentes |
| Origem/autenticidade de mídia | Indícios de geração/manipulação/procedência; não verdade da cena |
| OCR / ASR | Leitura de texto em imagem / transcrição de fala |
| Deepfake | Manipulação sintética; detecção depende do tipo/corpus, não de um score universal |
| Coverage/cobertura | Quais camadas/trechos realmente produziram evidência utilizável |
| Ground truth | Origem/rótulo conhecido e justificado, independente da resposta do detector |
| Abstenção | Não concluir quando evidência é insuficiente/conflitante |
| Snapshot | Cópia assinada da análise original para exportação |
| Bearer capability | Quem possui o token pode exercer a capacidade, respeitando vínculo/prazo |
| Hash | Resumo dos bytes; igualdade de hash não comprova verdade/autor |
| C2PA | Credenciais de conteúdo com validação/confiança próprias, diferentes do registro Verify |
| Homologação | Teste ponta a ponta do escopo na versão/ambiente entregues |

### Evidências internas e navegação

- [Índice de documentos](README.md), [README principal](../README.md), [arquitetura resumida](general.md).
- [Plano detalhado de entrega](PLANO-ENTREGA-14-DIAS.md), [matriz de 30 casos](MATRIZ-VALIDACAO-30-CASOS.md).
- [Primeira etapa](PRIMEIRA-ETAPA-2026-10-03.md), [validação UI](VALIDACAO-INTERFACE-2026-10-04.md).
- [Conferência de texto](CONFERENCIA-TEXTO-2026-10-04.md), [extração](CONTROLES-EXTRACAO-2026-10-04.md).
- [PDF/readiness/CI](PDF-READINESS-CI-2026-10-04.md), [PDF texto/link](PDF-TEXTO-LINK-2026-10-04.md).
- [Multimodal](MULTIMODAL-2026-10-03.md), [integrações](INTEGRACOES-GRATUITAS.md), [mídias de teste](../backend/tests/fixtures/README.md).

Referências externas estão junto aos assuntos que sustentam. Foram consultadas páginas oficiais de configuração; quotas/preços/modelos podem mudar. Nenhum painel privado, saldo atual ou segredo foi validado para escrever este manual.
