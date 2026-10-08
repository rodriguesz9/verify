# Verify — plano de entrega em 14 dias

> Prazo antecipado pelo responsável em 07/10: usar o [roteiro de fechamento até 11/10](ENTREGA-ATE-11-OUTUBRO.md). Este plano é preservado como backlog detalhado e critérios originais; seu calendário não é mais o prazo atual.

Planejado em **03/10/2026**. Prazo: **17/10/2026**.

**Consolidação detalhada em 04/10/2026:** este plano está integrado ao [manual completo do projeto](DOCUMENTACAO-COMPLETA.md). As seções 9–14 detalham backlog, execução diária, dependências, bloqueios, pacote público e aceite. O cronograma foi atualizado para aproveitar as correções locais já realizadas, sem confundir implementação com homologação.

Meta interna: versão candidata pronta em **15/10**, com **16 e 17/10 reservados para correções, repetição dos testes e apresentação**.

Este documento é um plano de trabalho. Marcar uma tarefa aqui não comprova implantação. Base examinada: commit `5db970da8f8a109472050ed96e3ab77d20e7f5e7`, código atual e registros de validação em `MULTIMODAL-2026-10-03.md`.

**Atualização de 03/10:** primeira rodada iniciada e validada localmente, antecipando histórico/painel, limpeza de dados no navegador e PDF consistente. As marcações abaixo referem-se a essa revisão local, **ainda sem commit/push/deploy**. Evidências, limitações e reprodução em [PRIMEIRA-ETAPA-2026-10-03.md](PRIMEIRA-ETAPA-2026-10-03.md).

**Atualização de 04/10 — primeira etapa:** SQLite/PostgreSQL 16.13 descartáveis passaram (212 testes + 141 subtestes), além de 67 controles frontend; demonstração foi verificada entre abas. Guards de câmera/microfone e leitura de registros antigos foram acrescentados.

**Atualização de 04/10 — próxima rodada:** 223 testes backend/SQLite, 71 frontend e build passaram. A [matriz de 30 casos](MATRIZ-VALIDACAO-30-CASOS.md) tem 20 controles com execução em pelo menos uma dimensão e 10 pendentes; há falhas ASR e sinais errados de HF, não 20 acertos de classificação. Fluxos de todas as modalidades foram operados pela UI local, com chamadas reais gratuitas limitadas e ferramentas locais. Correções/abstenções, registros e pendências em [VALIDACAO-INTERFACE-2026-10-04.md](VALIDACAO-INTERFACE-2026-10-04.md). Continua sem commit/push/deploy nesta revisão.

**Atualização de 04/10 — conferência:** `/app` passou a pausar checagem factual de OCR/transcrição para edição/confirmação humana. Nova análise textual preserva a leitura original, sem repetir detectores. Painel exclui inconclusivos da média em vez de mostrar placeholders 50/100. 242 testes backend e 79 frontend passaram, build passou; fluxo OCR real validado no navegador, incluindo Modo Fácil e oito controles responsivos. [Registro e limites](CONFERENCIA-TEXTO-2026-10-04.md). Sem novas chamadas externas, commit/push/deploy.

**Atualização de 04/10 — PDF/banco/CI:** PDF sem placeholders `None`, escala explícita e sinal zero preservado; `/ready` separa conectividade do banco de liveness/configuração de APIs. Runner offline e workflow de testes/build preparados. 256 testes backend passaram no Docker/Python 3.11/SQLite sem rede e no Python 3.12/PostgreSQL descartável; 79 frontend e build passaram. Exportação fictícia renderizada e conferida. [Registro](PDF-READINESS-CI-2026-10-04.md). CI remoto, deploy e validações reais restantes continuam pendentes; nenhum crédito de API consumido nesta rodada.

## 1. O que entregar

**Um verificador assistido, compreensível e estável para apresentação e piloto limitado. Não um detector infalível de falsidade ou deepfake.**

Escopo principal:

- Texto e links: buscar evidências relevantes, explicar a conclusão e permitir abrir as fontes.
- Imagens: extrair texto, apresentar sinais disponíveis e separar origem sintética de veracidade da mensagem.
- Áudio: transcrever português, permitir conferir o texto e verificar as afirmações extraídas.
- Vídeo: demonstrar análise de quadros amostrados e áudio quando disponível, com cobertura limitada claramente informada.
- Relatório, PDF e histórico: preservar a mesma análise, sua versão, evidências e limitações.
- Uso simples: celular, Modo Fácil, navegação por teclado e mensagens claras de indisponibilidade.
- Entrega reproduzível: Docker, configuração documentada, versão identificada e demonstração de reserva.

Premissas: uma pessoa com apoio de desenvolvimento; aproximadamente **4 horas por dia**; **48 horas planejadas + 8 horas de reserva**; nenhum serviço novo pago. O cronograma precisa ser reduzido se houver apenas 2–3 horas por dia.

### O que já existe e não precisa ser refeito

A aplicação já tem frontend e backend publicados, autenticação, histórico, relatórios, Docker e integrações. OCR local e transcrição AssemblyAI tiveram controles reais bem-sucedidos; houve regressões automatizadas e verificações HTTP. A landing azul e o Modo Fácil já receberam melhorias.

Isso é uma base funcional, **não uma medição de precisão universal**. Gemini apresentou falhas em transcrição; Hugging Face mostrou erros em controles e permanece experimental, sem voto no veredito. Clonagem de voz e manipulação facial ainda não têm validação suficiente. Consulte o registro multimodal para os resultados e limites de cada teste.

## 2. Prioridades

### P0 — bloqueadores da entrega

- [ ] Fixar as promessas: ausência de indícios não prova autenticidade; conteúdo sintético não significa necessariamente informação falsa.
- [x] Retirar o cache persistente automático de consultas no navegador; relatório somente em sessão, com limpeza ao sair/trocar de conta e isolamento de respostas antigas. Persistência opcional não foi adicionada.
- [x] Fazer o PDF usar a análise original assinada, sem nova chamada a detectores e sem mudar a conclusão. Mídia/texto/link/lote/texto conferido compatíveis têm PDF; legados incompatíveis permanecem sem exportação.
  - Atualização: texto/link/lote e texto conferido compatíveis também exportam desde a etapa de 04/10; apenas legados incompatíveis/erros permanecem sem PDF. Resultado local, não homologação remota.
- [ ] Corrigir bugs que impeçam enviar conteúdo, entender o resultado ou consultar evidências.
- [ ] Garantir que falhas, limite de uso e ausência de fontes produzam indisponibilidade/inconclusivo, não uma conclusão inventada.
- [ ] Preservar orçamento: nenhum fallback pago, nenhum detector pago reativado e limites gratuitos conferidos.
- [ ] Testar o fluxo completo no deploy da versão final, não apenas funções isoladas.
- [ ] Preparar demonstração local e resultados gravados identificados como tais.

O uso de fontes e a comunicação das limitações também seguem a orientação de verificação independente e redução de confiança excessiva em respostas de modelos da [OWASP](https://genai.owasp.org/llmrisk/llm092025-misinformation/).

### P1 — fechar antes da apresentação, conforme capacidade

- [x] Histórico/painel: corrigir tamanho de página, filtros globais, busca e suporte a vídeo; tornar as ações acessíveis por teclado. Validado com 45 registros e duas contas em ambiente local.
- [x] Conferência do texto extraído: revisão simples antes de checar afirmações quando OCR/transcrição estiverem incompletos.
  - Implementada em `/app`, com original, editor, confirmação e nova checagem textual vinculada. OCR real/fluxo autenticado testado localmente; áudio/vídeo cobertos por controles automatizados nesta etapa. Demo/WhatsApp seguem fluxo anterior; homologação no deploy e novos controles ASR reais continuam pendentes. Erros ASR anteriores não foram apagados.
- [ ] Revisão de acessibilidade e testes de tarefas com 3–5 pessoas leigas, se houver participantes disponíveis.
- [ ] Automatizar testes e build sem chaves externas, dentro da cota disponível.
  - Runner/workflow implementados e comandos validados localmente. Falta execução no GitHub e configurar os checks obrigatórios antes da publicação; não presumir que o autodeploy já aguarde testes.
- [ ] Consolidar README, configuração de produção, limitações e roteiro de apresentação.
- [ ] Auditar dependências e corrigir achados relevantes, evitando uma atualização geral perto do prazo.

### P0 extra para abrir ao público com dados reais

Antes de anunciar lançamento público homologado, incluir retenção definida, exclusão de histórico/conta, aviso de processamento por terceiros, canal de contato, isolamento entre usuários, backup/restauração testados, migração versionada e verificação de disponibilidade do banco.

Esse pacote pode exigir **mais 2–4 dias**, dependendo dos resultados. Ele substitui polimento e recursos opcionais, não a reserva final. Se não couber, limitar efetivamente o acesso ao piloto e usar conteúdo fictício ou autorizado; não apresentar a versão como pronta para uso público irrestrito. Esta lista de engenharia não equivale a certificação jurídica ou de segurança.

### P2 — depois da entrega

WhatsApp real; clonagem de voz; identidade facial/lip-sync; detector universal de deepfake; voto do Hugging Face; novos detectores pagos; várias réplicas, filas e Redis; novo redesign amplo; calibração estatística com conjunto independente maior.

Não adicionar uma API apenas para aumentar a lista de integrações. Uma integração nova precisa de benefício demonstrado, orçamento e testes próprios.

## 3. Cronograma

| Data | Trabalho principal | Evidência de conclusão |
|---|---|---|
| **04/10 — dia 1** | Escopo, orçamento, corpus e documentação consolidada: ENT-01/02/03, DOC-01. | Modo de entrega definido; arquivos solicitados; mapa de pendências publicado. |
| **05/10 — dia 2** | Repetir regressões em PostgreSQL; conferir isolamento e comprimento de URL: ENV-02, QA-01, SEG-01. | Suíte atual em banco descartável; URL longa tem comportamento definido; duas contas isoladas. |
| **06/10 — dia 3** | Checagem textual/links e conferência de extração: QA-02/03/05. | Evidência suficiente decide corretamente; ausência/conflito abstém; termos críticos preservados. |
| **07/10 — dia 4** | Oito controles pendentes e chamadas reais gratuitas autorizadas: ENT-03, QA-04/06. | Origem/expectativa/resultado por dimensão; nenhuma mídia sintética rotulada humana. |
| **08/10 — dia 5** | Corrigir P0 encontrados e repetir revisão/relatório: QA-05, REL-01/02. | Nenhum bug conhecido bloqueia enviar, conferir leitura ou entender a conclusão. |
| **09/10 — dia 6** | PDF/histórico, arquivo salvo e matriz de erros: REL-03, QA-07. | Mesma análise exportada e arquivo aberto; falhas não fabricam verdade/falsidade. |
| **10/10 — dia 7** | Orçamento/admissão, sessão e decisão de segurança: SEG-02/03/04. | Limites compatíveis com acesso escolhido; riscos sem mitigação impedem abertura pública. |
| **11/10 — dia 8** | Privacidade, backup e pacote público se escolhido: OPS-01/02, PUB-01–06. | Avisos verdadeiros; piloto realmente restrito ou requisitos públicos demonstrados. |
| **12/10 — dia 9** | Acessibilidade e tarefas com leigos: UX-01/02/03. | Fluxos essenciais funcionam em celular, Modo Fácil, teclado e zoom. |
| **13/10 — dia 10** | Docker/configuração/CI e ensaio de retorno: ENV-01/03, CI-01/02, OPS-03. | Checkout candidato reproduzível; checks remotos/gate; rollback ensaiado. |
| **14/10 — dia 11** | Publicação autorizada e homologação candidata: DEP-01/02/03. | SHA conferido nos dois serviços; todas as entradas e auxiliares no deploy. |
| **15/10 — dia 12** | Leitura independente do manual, roteiro e reserva: DOC-02, ENT-04/05. | Versão candidata congelada; documentação reproduzida; apresentação ensaiada. |
| **16/10 — dia 13** | Reserva de 4 h: apenas bloqueadores e regressões afetadas. | Nenhum recurso novo; correções têm evidência. |
| **17/10 — dia 14** | Reserva de 4 h: conferência final/entrega. | Checklist, limitações, versão e responsáveis registrados. |

### Bugs concretos identificados e situação

1. **Corrigido localmente:** diferença de 15/20 itens, filtros limitados à página atual e ausência de vídeo. Consulta e contagem usam os mesmos filtros dentro da conta.
2. **Corrigido localmente:** cache persistente sem prazo e ausência de limpeza no logout. Cache retirado; relatório de sessão isolado, preferências mantidas.
3. **Corrigido localmente:** PDF repetia `analyze_media`. Exportação agora exige cópia original assinada, validade e controle da conta; resultado arbitrário/reenvio de mídia são recusados.
   **Ampliado em 04/10:** texto/link/lote e texto conferido também exportam o resultado original. 274 testes backend, 84 frontend e build passaram. PDF/200 pela interface para texto, link e histórico; salvamento final no navegador integrado não comprovado. [Registro e limites](PDF-TEXTO-LINK-2026-10-04.md). Não marca homologação do deploy como concluída.
4. Guias antigos de produção divergem do estado validado atual, incluindo política de evidências e número de quadros de vídeo. Consolidar os exemplos antes de alguém copiá-los.
5. **Corrigido localmente:** `/health` permanece liveness; `/ready` testa conexão do banco com deadline/503; `/api/capabilities` informa configuração, não saúde dos fornecedores. Configuração local do Railway atualizada; homologação remota pendente.

## 4. Matriz mínima de validação

Preparar **30 casos documentados**, distribuídos assim:

| Entrada | Casos | Cobertura mínima |
|---|---:|---|
| Texto/link | 10 | Afirmações confirmadas/refutadas com fontes correspondentes; ausência de cobertura; negação, data/valor trocados; fontes duplicadas ou irrelevantes. |
| OCR | 6 | Texto português legível, contraste baixo, rotação, recorte, números e negação. |
| Áudio | 6 | Voz autorizada em português, TTS declarado, silêncio, ruído, trecho curto e informação com números/negação. |
| Imagem | 4 | Foto de origem conhecida, imagem sintética conhecida, gráfico não gerado por IA e imagem editada; distinguir origem de conteúdo factual. |
| Vídeo | 4 | Vídeo próprio, vídeo sintético declarado, edição convencional e conteúdo com fala; registrar quadros/trechos realmente analisados. |

Cada caso deve registrar: ID, origem/licença ou consentimento, entrada, expectativa e motivo, versão testada, serviços usados, resultado, tempo, inconclusivos e falhas. Transformações do mesmo arquivo não contam como amostras independentes. Não usar “humano” como rótulo para mídia de origem desconhecida.

Separar dois tipos de teste:

- **Regras controladas:** simular evidências suficientes, ausentes, contraditórias e irrelevantes; verificar a decisão esperada sem depender de quota externa.
- **Integrações reais:** testar o caminho com serviços ativos, dentro dos créditos autorizados, registrando o que realmente respondeu. Estar configurado não significa ter sido validado.

Critérios: zero conclusões definitivas erradas nos controles definidos; nenhuma fonte irrelevante usada como prova; nenhum resultado positivo obtido por ausência de detector. Casos com evidências suficientes precisam produzir a decisão esperada — fazer tudo ficar inconclusivo também não demonstra que a checagem funciona. Nos casos sem cobertura, inconclusivo é o resultado seguro.

Esses 30 casos verificam comportamento e limitações; **não autorizam divulgar porcentagem de precisão universal**. Não ajustar limiares no mesmo conjunto e apresentá-lo depois como avaliação independente.

Testar também os fluxos auxiliares: cadastro/login/logout/renovação, isolamento entre contas, histórico, PDF, selo de integridade e demonstração. O selo deve informar integridade dos bytes registrados, não autenticidade da cena. WhatsApp permanece identificado como simulação.

## 5. Usabilidade e acessibilidade

- [ ] Larguras de 320, 375, 768 e 1280 px; Modo Fácil ligado e desligado; zoom de 200%.
- [ ] Sem rolagem horizontal ou texto essencial cortado nos fluxos principais.
- [ ] Ações por teclado, foco visível, rótulos claros, contraste e erros compreensíveis.
- [ ] Animações respeitam movimento reduzido e não escondem informação.
- [ ] Botões principais com área confortável; não depender somente de cor para comunicar resultado.
- [ ] Pessoas leigas conseguem enviar, interpretar inconclusivo, consultar uma fonte e voltar.

Usar a [referência WCAG 2.2 do W3C](https://www.w3.org/WAI/WCAG22/quickref/) como checklist técnico. Os testes deste projeto não equivalem a uma declaração de conformidade integral.

## 6. Orçamento e contingência

**Conferir o Railway no primeiro dia.** Capturas anteriores mostravam teste/saldo limitado; o saldo e a data atuais ainda precisam ser conferidos. O trial tem limite de tempo e de créditos, portanto não presumir hospedagem contínua até a apresentação. Consulte a [documentação oficial do Railway](https://docs.railway.com/pricing/free-trial).

- Hive pago permanece pausado; não reutilizar automaticamente autorizações pontuais antigas.
- OpenRouter usa somente modelos gratuitos e limites definidos; sem rota alternativa paga.
- AssemblyAI/Sightengine: usar apenas créditos gratuitos previamente autorizados e dentro da disponibilidade real.
- Testes rotineiros usam simulações e controles locais; chamadas reais ficam concentradas na homologação.
- Nenhuma chave entra em README, Git, screenshot pública ou frontend. `.env.example` contém nomes e exemplos seguros, nunca segredos.
- Não publicar mídia privada para viabilizar busca reversa.
- Manter Docker local e uma apresentação com resultados gravados claramente identificados. Uma falha de rede não pode obrigar improvisar uma análise falsa.

## 7. Como decidir que terminou

A versão para apresentação/piloto está pronta quando:

- [ ] Os P0 do escopo escolhido estão fechados; nenhum bloqueador permanece sem alternativa segura.
- [ ] Testes/build passam na versão final; entradas principais foram verificadas no deploy correspondente.
- [ ] Matriz registra os sucessos, falhas e inconclusivos, sem ocultar limitações dos detectores.
- [ ] Relatório, histórico e PDF concordam e permitem consultar evidências.
- [ ] Não há vazamento entre contas/navegador nem fallback pago inesperado nos controles.
- [ ] Celular e Modo Fácil permitem executar as tarefas essenciais.
- [ ] Documentação, exemplos, versão, backup e apresentação de reserva estão prontos.
- [ ] Funções experimentais/simuladas estão identificadas, e serviços não validados não são anunciados como plenamente funcionando.

**Para uso público aberto, o pacote adicional de privacidade e operação também precisa estar concluído.** Se ele falhar, a entrega continua como apresentação/piloto efetivamente limitado, não como lançamento público homologado.

## 8. Responsabilidades e cortes de escopo

Desenvolvimento: corrigir bugs, criar testes, melhorar mensagens, consolidar documentação e verificar a entrega. Responsável pelo projeto: confirmar o tipo de entrega e disponibilidade diária, conferir saldos sem compartilhar chaves, fornecer exemplos autorizados, validar a interpretação das fontes e conseguir participantes para o teste de uso.

Regra de corte: se houver atraso, retirar primeiro novos efeitos visuais, novas APIs, WhatsApp real e funções avançadas de deepfake. Depois reduzir filtros e conveniências secundárias. **Nunca cortar honestidade do resultado, isolamento dos dados, controle de gastos ou teste do fluxo principal.**

Com 2–3 horas por dia, manter apresentação limitada, correções P0, uma matriz menor explicitamente descrita e documentação de reserva. Não prometer o mesmo escopo de lançamento público com metade do tempo.

Próximo passo: confirmar escopo/saldo, iniciar a matriz de 30 casos e corrigir leitura/checagem conforme as falhas reais. Histórico, limpeza no navegador e PDF já receberam a primeira rodada local; a homologação/publicação dessa revisão continua pendente.

## 9. Backlog rastreável e critérios de aceite

Responsáveis: **DEV** = desenvolvimento; **RP** = responsável pelo projeto/contas; **QA** = quem executa/verifica testes, podendo ser DEV; **PART** = participantes voluntários. Não são pessoas contratadas adicionais. A mesma pessoa pode ter vários papéis; cada tarefa precisa de dono nominal antes de execução.

Estados: **L** implementado/validado localmente, com repetição pendente; **P** pendente; **D** documentação produzida, reprodução/revisão independente pendente. Checkbox só deve ser fechado com evidência do ambiente exigido. Prioridade P0 exige fechamento para o escopo escolhido; P1 pode ser cortada conforme impacto; PUB é bloqueador adicional de público irrestrito.

### 9.1 Escopo, configuração e testes

| ID | Prioridade / dono / estado | Trabalho e critério de aceite | Depende de |
| --- | --- | --- | --- |
| ENT-01 | P0 / RP+DEV / P | Decidir apresentação/piloto/público, funções e acesso. Aceite: decisão escrita e controle de acesso efetivo se piloto, não só aviso. | — |
| ENT-02 | P0 / RP / P | Conferir saldo, expiração, cobrança automática, quotas/modelos. Aceite: inventário sanitizado e limite autorizado por fornecedor, sem novas contratações. | — |
| ENT-03 | P0 matriz / RP+QA / P | Fornecer cinco originais autorizados e criar três derivados. Aceite: oito casos com origem, termos esperados, transformações e resultado por dimensão. | ENT-01 |
| ENV-01 | P0 / DEV / P | Sincronizar template/configuração, incluindo DATABASE_URL, CORS e modelo explícito. Aceite: template sem segredo reproduz ambiente; backend/cliente não confundidos. | ENT-02 |
| ENV-02 | P0 se URL longa / DEV / P | Alinhar limite de URL recebida e persistida. Aceite: teste PostgreSQL de limite/excesso, erro compreensível e nenhuma análise perdida por falha tardia de banco. | QA-01 |
| ENV-03 | P0 / DEV / L | Construir imagem no contexto Railway escolhido e testar ferramentas/PORT/env ausente. Aceite: build limpo reproduzível, imagem sem chave/banco local, startup e `/ready` verificados. | ENV-01 |
| QA-01 | P0 / QA / L | Repetir suíte mais recente em SQLite e PostgreSQL descartáveis. Aceite: zero erros/skips/HTTP externo indevido, comandos/versão/contagem atuais registrados. | — |
| QA-02 | P0 / QA+DEV / L | Testar política literal: duas fontes elegíveis, duplicadas, irrelevantes, conflitantes, datas/negação/valores. Aceite: decisões corretas quando evidência suficiente; abstenção justificada nas demais. | QA-01 |
| QA-03 | P0 / QA / P | Homologar link HTTPS público autorizado e extração estática. Aceite: texto/final URL/limites corretos; DNS/TLS reais; fixture simulada não usada como prova. | ENV-01 |
| QA-04 | P0 corpus / QA / P | Completar imagem/áudio/vídeo de origem conhecida. Aceite: negativos/positivos legítimos, cobertura e erros preservados; inconclusivo não vira “humano”. | ENT-03 |
| QA-05 | P0 / DEV+QA / L | Conferência OCR/ASR em `/app` para três modalidades. Aceite: original e confirmado separados, negação/data/valor não corrigidos silenciosamente, nenhuma repetição de detector. | QA-04 |
| QA-06 | P0 serviços habilitados / RP+QA / P | Testar realmente cada serviço anunciado, com quota grátis autorizada. Aceite: parser, estado, modelo e caso documentados; Hive pago permanece pausado sem nova autorização. | ENT-02, QA-04 |
| QA-07 | P0 / QA / L | Falhas: sem chave, 401/403/429, timeout, JSON inválido, silêncio, bytes corrompidos, excesso. Aceite: nenhum erro vira conclusão falsa; custo/fallback seguro; UI orienta próximo passo. | QA-01 |

“Cada serviço anunciado” não significa contratar/testar todo serviço legado. Se não houver acesso, desabilitar/identificar a camada e ajustar a promessa. O conjunto de 30 casos exige entradas reais autorizadas; sem arquivos, não marcar a matriz inteira concluída.

### 9.2 Relatório, conta, privacidade e uso

| ID | Prioridade / dono / estado | Trabalho e critério de aceite | Depende de |
| --- | --- | --- | --- |
| REL-01 | P0 / DEV+QA / L | Explicação por afirmação/camada e fontes com motivo de inclusão/exclusão. Aceite: usuário distingue evidência factual, orientação, detector e falha; sem justificativa inventada. | QA-02/04 |
| REL-02 | P0 / DEV+QA / L | Histórico/painel: filtros globais, paginação, vídeo e índices. Aceite: duas contas/45 registros, filtros e totais coerentes; inconclusivo sem percentual/média falsa. | QA-01 |
| REL-03 | P0 / QA / L | PDF de texto/link/mídia/revisão/reabertura. Aceite: arquivo salvo e aberto em navegador real; mesma conclusão/fontes/versão, zero reanálises/quota extra, tokens não persistidos. | REL-01/02 |
| SEG-01 | P0 / DEV+QA / L | Isolamento de conta/navegador/abas/respostas tardias. Aceite: nenhum registro da outra conta em UI/API/exportação; cookies/tokens não expostos; preferências preservadas. | QA-01 |
| SEG-02 | P0 conforme acesso / DEV+RP / P | Definir orçamento e restrição de visitantes; resolver limites por processo se acesso ampliar. Aceite: teto coerente com orçamento testado ou acesso efetivamente limitado; não anunciar quota diária inexistente. | ENT-01/02 |
| SEG-03 | P0 público / DEV+QA / P | Auditar sessão/OAuth/conta inativa/senha/revogação. Aceite: política definida, achados relevantes corrigidos e regressão; risco residual limita entrega. | SEG-01 |
| SEG-04 | P1; achado crítico P0 / DEV / P | Auditar dependências/imagem/segredos. Aceite: relatório de risco e correções pertinentes; nenhum segredo versionado, nenhuma atualização geral sem regressão. | ENV-03 |
| UX-01 | P0 essencial / QA+DEV / L | 320/375/768/1280 px e Modo Fácil on/off. Aceite: enviar, conferir, entender resultado, consultar fonte e voltar sem cortes/overflow essencial. | REL-01 |
| UX-02 | P0 essencial / QA+DEV / P | Teclado/foco, zoom 200%, contraste, texto/erros e movimento reduzido. Aceite: tarefas acessíveis sem depender de cor/efeito; animação não bloqueia leitura. | UX-01 |
| UX-03 | P1 / RP+PART+QA / P | Tarefas com 3–5 leigos. Aceite: roteiro/observações sanitizadas, correções essenciais e limitações; se sem participantes, registrar ausência sem chamar teste substituto de validação com usuários. | UX-01/02 |

### 9.3 Reprodução, operação e entrega

| ID | Prioridade / dono / estado | Trabalho e critério de aceite | Depende de |
| --- | --- | --- | --- |
| CI-01 | P0 / DEV / L | Executar workflow no GitHub no SHA candidato. Aceite: checks SQLite/PostgreSQL/frontend/build sem segredo de fornecedor, zero skips inesperados. | QA-01, ENV-03 |
| CI-02 | P0 / RP+DEV / P | Conferir gate/autodeploy/promoção. Aceite: configuração observada impede divulgar versão não testada ou promoção é manual controlada; decisão registrada. | CI-01 |
| OPS-01 | P0 público; P1 apresentação / RP+DEV / P | Avisos sobre terceiros/contato e retenção. Aceite: telas condizem com dados enviados/guardados e ações realmente disponíveis. | ENT-01 |
| OPS-02 | P0 público/dados reais / RP+DEV / P | Backup/restauração em staging. Aceite: restore em banco novo, contagens/relações/fluxos corretos, tempo e responsável registrados. | ENV-03 |
| OPS-03 | P0 / DEV+QA / P | Ensaiar retorno de código/configuração sem apagar banco. Aceite: versão anterior conhecida, compatibilidade de schema/segredo e procedimento testado fora da produção. | OPS-02 ou ambiente fictício |
| DEP-01 | P0 / RP+DEV / P | Integrar trabalho local ao repositório de entrega, revisar, commit/push autorizados. Aceite: SHA identificável, trabalho preexistente preservado, sem chaves/artefatos privados. | QA-01, ENV-01 |
| DEP-02 | P0 / RP+DEV / P | Publicar backend/frontend autorizados. Aceite: contexto/banco/PORT/CORS/cookies/API URL corretos; SHA efetivo conferido em ambos. | DEP-01, CI-01/02 |
| DEP-03 | P0 / QA / P | Homologar no deploy cinco entradas e auxiliares. Aceite: login, revisão, fontes, histórico, PDF e falhas passam; custos/versão registrados, não só HTTP 200. | DEP-02, QA-03/04/06 |
| DOC-01 | P0 / DEV / D | Manual completo + plano integrado + índice. Aceite: caminhos/env/rotas coerentes, instruções sem segredos e histórico de falhas preservado. | — |
| DOC-02 | P0 / RP+QA / P | Outra pessoa reproduzir setup/roteiro. Aceite: lacunas corrigidas e confirmação de passos realizados; manual escrito sozinho não encerra reprodução. | DOC-01, ENV-03 |
| ENT-04 | P0 / RP+DEV / P | Apresentação e reserva local/gravada. Aceite: 5 min ensaiados, arquivos autorizados, indisponibilidade tratada honestamente. | DOC-02, DEP-03 ou reserva identificada |
| ENT-05 | P0 / RP+QA / P | Checklist e congelamento. Aceite: nenhum bloqueador aberto; público/piloto identificado; SHA/checks/evidências/limites entregues. | P0 do escopo |

## 10. Execução diária detalhada e orçamento de tempo

**Premissa:** 4 horas de trabalho efetivo por dia. Dias 1–12: 48 h; dias 13–14: 8 h de reserva. As divisões são estimativas de coordenação, não garantia de duração de bugs/fornecedores. Não colocar o pacote público inteiro “por cima” dessas horas: substituir P1/P2 ou ampliar prazo.

Atividades já implementadas localmente devem ser **revalidadas**, não refeitas sem motivo. No início de cada dia: conferir bloqueadores, saldo e último SHA; no fim: atualizar evidência/estado, sem marcar tarefa pela intenção.

### Dia 1 — 04/10: contrato de entrega e preparação

- 45 min: ENT-01, escopo e controle real de acesso; listar o que ficará experimental/simulado.
- 45 min: ENT-02, verificar trial/saldo/quotas/modelos privados e teto de teste, sem expor chave.
- 45 min: ENT-03, solicitar originais conforme matriz, consentimento e frases críticas; preparar destinos privados.
- 1 h 45: DOC-01 e backlog. Manual/plano consolidados nesta revisão; leitura independente ainda faltará.
- Saída: documento de escopo/orçamento + solicitação das cinco mídias + plano de contingência. Saldo/escopo não foram decididos só por escrever esta página.

### Dia 2 — 05/10: banco e fronteiras de conta

- 1 h 30: QA-01, suíte atual em PostgreSQL próprio e SQLite; coletar versão/contagem, sem usar produção.
- 1 h: ENV-02, URL 512/4.096; corrigir schema/limite com regressão e plano de migration se necessário.
- 1 h: SEG-01/REL-02, duas contas, 45 registros, busca/filtros, logout/abas/resposta tardia.
- 30 min: registrar achados e rever esforço. Se banco falhar, priorizar correção antes de corpus/cosmética.

### Dia 3 — 06/10: evidência factual e leitura

- 1 h: QA-02, controles elegíveis/refutados/duplicados/conflitantes; verificar que fontes pertinentes decidem e paráfrases não forçam conclusão.
- 1 h: QA-03, página HTTPS autorizada real; registrar título/negação, fonte final, truncamento e bloqueios.
- 1 h 30: QA-05, OCR/transcrição → original/editor/confirmação → nova análise, inclusive expiração/dono/token inválido.
- 30 min: guardar diferenças; não ocultar a alteração estrita OCR05 nem erros ASR anteriores.

### Dia 4 — 07/10: corpus real autorizado

- 30 min: verificar os cinco originais, consentimento/origem/termos esperados; criar três derivados sem alterar rótulo.
- 2 h: QA-04, oito pendentes e dimensões ausentes; registrar tempos/quadros/trechos/cobertura.
- 1 h: QA-06, chamadas gratuitas autorizadas concentradas; confirmar modelos/permissões; parar ao teto.
- 30 min: matriz atualizada e bugs ordenados. Sem arquivos, avançar offline, mas manter casos pendentes e decidir redução formal da matriz/apresentação.

### Dia 5 — 08/10: correções da matriz e relatório

- 2 h: corrigir apenas falhas essenciais descobertas; criar regressão mínima antes de ampliar implementação.
- 1 h: REL-01/QA-05, explicação por afirmação/camada, fonte/data/motivo; preservar original/revisado.
- 30 min: repetir controles afetados e casos vizinhos de negação/valor/data.
- 30 min: avaliar risco de prazo. Se necessário, cortar efeito visual/nova integração, não proteção ou honestidade.

### Dia 6 — 09/10: persistência, PDF e erros

- 1 h 30: REL-03, texto/link/imagem/áudio/vídeo/revisão/histórico; salvar e abrir PDF em navegador real.
- 1 h 30: QA-07, indisponibilidades, quota, body/file/token inválidos, silêncio, rede/timeout.
- 30 min: comparar original/histórico/PDF e ausência de novas chamadas externas/cobrança.
- 30 min: conferir expiração/dono/legados e manter mensagem compreensível quando exportação não for possível.

### Dia 7 — 10/10: orçamento e sessão

- 1 h 30: SEG-02, visitantes, falhas que custam, concorrência e limites por processo; implementar controle exigido pelo alcance ou restringir acesso.
- 1 h: SEG-03, sessão/OAuth/conta inativa e política de senha; corrigir achados críticos ou impedir abertura pública.
- 1 h: SEG-04, dependências/segredos/imagem; atualizar somente o necessário com regressões.
- 30 min: gate de segurança. Público só continua se houver capacidade real para pacote adicional; caso contrário, piloto restrito documentado.

### Dia 8 — 11/10: operação e privacidade

- 1 h: OPS-01, avisos sobre dados enviados/guardados, retenção/contato e funcionalidades ainda ausentes.
- 1 h 30: OPS-02, backup e restore em banco novo; comparar relações/contagens e fluxos.
- 1 h: pacote PUB selecionado ou plano de restrição efetiva ao piloto; não simular exclusão na UI sem backend.
- 30 min: decisão final de alcance. PUB não concluído impede lançamento irrestrito; não consome a reserva com funcionalidades novas.

### Dia 9 — 12/10: acessibilidade e compreensão

- 1 h 30: UX-01/02, resoluções, zoom, foco, teclado, contraste, erro e reduced motion.
- 1 h: UX-03, participantes com roteiro e conteúdo fictício, se disponíveis.
- 1 h: corrigir cortes/obstáculos essenciais; não introduzir redesign amplo.
- 30 min: repetir tarefas e registrar ausência de participantes, se houver; PDF não é automaticamente acessível.

### Dia 10 — 13/10: reprodução e candidato

- 1 h: ENV-01/03, template sem segredo e build do contexto de entrega; ferramentas/PORT/readiness.
- 1 h: QA-01 e frontend/build na versão candidata, registrar resultados atuais.
- 1 h: CI-01/02 e DEP-01, review/commit/push autorizados e checks remotos; gate observado.
- 1 h: OPS-03, retorno ensaiado e DOC-02 inicial; não publicar nova versão antes de testes críticos.

### Dia 11 — 14/10: deploy e homologação

- 1 h: DEP-02, publicação autorizada com envs/origens/contextos certos; verificar SHA efetivo e prontidão.
- 2 h: DEP-03, conta + cinco modalidades + revisão + fontes + histórico + PDF salvo/aberto + celular.
- 30 min: cenários de falha gratuitos/localmente controlados sem alterar chaves da produção às cegas.
- 30 min: registrar custo/limites e classificar bugs. P0 aberto bloqueia candidata; cortar polimento para corrigir.

### Dia 12 — 15/10: congelamento e apresentação

- 1 h: DOC-02, outra pessoa segue configuração/roteiro; ajustar somente lacunas verificadas.
- 1 h: ENT-04, ensaio 5 min e reserva local/gravada com rótulo correto.
- 1 h: ENT-05, checklist, SHA, modelos/configuração sem segredos, resultados e pendências explícitas.
- 1 h: correções pequenas/regressões ou margem de ensaio. Congelar funcionalidades; só bloqueadores depois.

### Dia 13 — 16/10: reserva, até 4 h

Corrigir bloqueadores, repetir regressões e smoke test dos fluxos afetados. Preservar versão funcional anterior. Se nada bloquear, usar tempo para ensaio e conferência, não para adicionar API/WhatsApp/redesign.

### Dia 14 — 17/10: entrega, até 4 h

Conferir versão/saldo/links, executar smoke test seguro, entregar artefatos/limites e apresentar. Se rede/quota falhar, usar reserva identificada. Relatar escopo realmente validado; não afirmar “todas as verificações certeiras”.

## 11. Dependências, caminho crítico e decisões de corte

```text
Escopo + orçamento + originais
             │
             ├── corpus + política + extração ── correções ── relatório/PDF
             ├── banco + conta + configuração ── Docker + CI
             └── privacidade + acesso + backup ── gate piloto/público
                                                  │
                                 commit candidato + publicação autorizada
                                                  │
                                  homologação no SHA publicado
                                                  │
                              freeze + documentação reproduzida + reserva
```

Se ENT-03 atrasar, não trocar mídia humana por sintética. Continuar regressões, configurar ambiente, revisar relatório/segurança; decidir formalmente apresentação com matriz incompleta identificada. Se ENT-02 indicar hospedagem insuficiente, preparar ambiente local antes do dia de apresentação.

Se CI/rede/build bloquear, registrar causa e tentar alternativas seguras (cache/runtime compatível, ambiente descartável, instalação autorizada). Não reutilizar banco produtivo para acelerar. Se não houver evidência do deploy, entregar como local/demonstração, não como homologação publicada.

Congelamento em 15/10: nenhuma função nova. Ordem de corte: efeitos extras → novas APIs → busca reversa avançada → WhatsApp real → deepfake/identidade avançados → conveniências P1. Nunca cortar isolamento, orçamento, fontes/limitações, revisão crítica ou teste de versão final.

## 12. Bloqueios externos e ações do responsável

| Bloqueio | Ação necessária | Trabalho que pode continuar |
| --- | --- | --- |
| Escopo/acesso indefinidos | RP escolher piloto limitado ou público; confirmar disponibilidade diária | Manual, regressão offline, revisão de risco |
| Saldo/trial/modelos desconhecidos | RP verificar painel privado e teto sem enviar chaves | Tests simulados, Docker e reserva local |
| Cinco arquivos originais ausentes | RP fornecer conteúdo próprio/autorizado segundo matriz | Demais dimensões, transformação após originais, UI/erros |
| Serviço sem crédito/acesso | RP confirmar plano; não contratar automaticamente | Desabilitar/identificar camada, testar erro/abstenção |
| Push/deploy depende de conta/autorização | RP autorizar workflow de entrega e disponibilizar acesso legítimo | Preparar diff, tests, release notes e candidato local |
| Participantes ausentes | RP procurar 3–5 voluntários ou registrar indisponibilidade | Checklist técnico, sem alegar validação com usuários |

Não são bloqueios resolvidos por pedir/colar segredo no chat. Dados privados devem permanecer no `.env` ignorado e nos painéis autorizados.

## 13. Pacote adicional obrigatório para lançamento público

| ID | Dono | Critério de aceite | Estimativa/risco |
| --- | --- | --- | --- |
| PUB-01 | DEV+RP | Retenção por categoria definida, exclusão de conta/histórico implementada e testada; tratamento de backups/caches explicado | 4–8 h; exige schema/fluxos |
| PUB-02 | DEV | Migrações versionadas de baseline/alterações, upgrade em staging com dados legados e plano de compatibilidade | 4–8 h; estado atual não é migration completa |
| PUB-03 | RP+DEV+QA | Backup restaurado em banco novo e fluxo/tempo verificados | 2–4 h, além da disponibilidade de ambiente |
| PUB-04 | DEV+QA | Auth/OAuth/conta inativa/segredos/isolamento auditados; achados críticos fechados | 4–8 h, variável conforme bugs |
| PUB-05 | DEV+RP | Orçamento/admissão adequado ao alcance, inclusive visitantes, falhas e workers; teste de abuso/custo | 4–8 h; armazenamento compartilhado pode ampliar escopo |
| PUB-06 | RP+DEV | Avisos corretos, contato, terceiros, operação/incidente/hardening e responsabilidades definidos | 2–4 h; não equivale a revisão jurídica |

Faixa agregada indicativa: 20–40 h; parte se sobrepõe a tarefas OPS/SEG e não deve ser somada duas vezes. A hipótese anterior de 2–4 dias só cabe com capacidade efetiva/sobreposição/cortes. Se os achados ampliarem esforço, adiar abertura pública, não prometer fechá-la em quatro horas do dia 8.

Nada deste pacote é marcado pronto apenas por documentação. Interface que promete “apagar meus dados” sem exclusão implementada precisa ser corrigida ou não oferecida.

## 14. Artefatos de entrega e aceite final

### 14.1 Pacote mínimo

- Repositório com SHA candidato identificável, sem chave/dado privado.
- Checks atuais e evidências sanitizadas por ambiente/modalidade.
- [Manual completo](DOCUMENTACAO-COMPLETA.md), [índice](README.md), configuração e este plano atualizados.
- Matriz real com estados por dimensão, origem/consentimento e falhas preservadas.
- Frontend/backend publicados ou entrega local explicitamente identificada; versão comprovada.
- Exemplos/PDFs/resultados educativos rotulados; apresentação e reserva ensaiadas.
- Responsáveis por operação, custo e correções pós-entrega; backlog P2 separado.

### 14.2 Registro de aprovação

```text
Data / responsável / modo: apresentação, piloto restrito ou público
SHA frontend / backend e configuração não secreta:
CI/testes/build/ambiente e arquivos de evidência:
Modalidades/serviços realmente homologados:
Matriz: completos / parciais / falhos / pendentes (não misturar dimensões)
Conta/revisão/fontes/histórico/PDF salvo/celular:
Acesso e orçamento:
Backup/rollback/reserva:
Pendências e impacto, funções desligadas/experimentais:
Decisão: aprovado para este escopo / bloqueado / escopo reduzido
```

Para afirmar “concluído”, as evidências precisam corresponder à versão entregue. Para afirmar “público homologado”, PUB-01–06 também precisam estar demonstrados. Precisão universal e vereditos infalíveis não fazem parte do critério de entrega.
