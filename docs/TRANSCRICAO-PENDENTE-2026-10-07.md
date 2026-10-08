# Transcrição pendente: retomada privada e relatórios claros

Registro de 07/10/2026. Alterações na revisão local, **sem commit, push ou deploy novo**. Esta etapa implementa a proteção limitada de SEM-08; não homologa fidelidade de fala nem todos os provedores.

## Resultado desta etapa

- Nova tentativa do mesmo áudio, pela mesma conta/aba, consulta a tarefa AssemblyAI já conhecida durante a janela de retenção, sem novo upload ou criação de transcrição.
- Requisições simultâneas compartilham uma operação; cancelamento do solicitante não destrói o checkpoint privado.
- Se o envio de criação teve resposta incerta, a aplicação bloqueia uma nova criação temporariamente, em vez de presumir que o pedido não chegou ao provedor.
- Relatório, demonstração e cobertura distinguem processamento, estado incerto, acompanhamento expirado e serviço ocupado. Esses estados não determinam falsidade, ausência de fala ou clonagem.
- PDF apresenta rótulos em português, mantendo o relatório original; controles de áudio e faixa de áudio de vídeo foram testados.
- Nenhuma chamada real/paga foi feita nesta etapa. Todas as respostas AssemblyAI descritas abaixo foram simuladas.

## Bug corrigido

O código anterior criava um upload e uma transcrição em cada chamada. O prazo de 25 segundos podia cancelar o polling e perder o identificador. Uma nova requisição repetia a criação. A frase anterior “sem reenvio” só descrevia aquela chamada, não protegia novas tentativas.

A API AssemblyAI separa [criação da transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/submit) de [consulta do identificador existente](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/get). O serviço local agora mantém esse checkpoint privado. Não foi inventado um cabeçalho de idempotência oferecido pelo provedor.

## Como a proteção funciona

1. A aplicação valida/normaliza a mídia. A observação local de silêncio continua anterior à chamada de transcrição.
2. Um contexto de requisição identifica a conta validada pelo servidor ou um nonce anônimo aleatório, restrito à memória da aba.
3. A chave interna combina contexto, hash dos bytes preparados, impressão da chave do projeto, modelo `universal-2`, idioma `pt` e versão das opções. Não contém áudio, telefone ou credencial em claro.
4. Criação do registro é atômica. Uma tarefa por chave faz upload/criação; guarda o ID antes da consulta. Rodadas seguintes fazem somente GET para esse ID.
5. O solicitante e o worker têm prazo de 25 segundos. Cancelar o solicitante não cancela a operação compartilhada; o worker continua limitado pelo seu próprio prazo.
6. Resultados públicos usam campos permitidos. ID remoto, URL de upload, namespace e chave nunca são retornados, incluídos no histórico/PDF ou registrados por este serviço.
7. A transcrição literal obtida segue o fluxo de conferência humana de `/app`; não é reutilizado um veredito de verdade/autenticidade.

Contas autenticadas têm precedência sobre o header anônimo. O nonce não concede autenticação e só permite reutilização com os mesmos bytes. Ele não é persistido em storage, nem enviado em URLs; saída, troca de conta e sinal de limpeza entre abas o descartam. Sem nonce válido, não há deduplicação entre requisições anônimas. Reload/nova aba também não conserva o nonce.

O contexto cobre `/upload`, `/verificar/completo`, `/verificar/audio-rapido`, `/whatsapp/simulate` e `/whatsapp/webhook`. O simulador nunca considera `from_number` uma prova de identidade. O webhook só usa receipt depois de autenticar o gateway. Eventos pendentes liberam a proteção de receipt para uma consulta posterior; não são salvos como concluídos nem executam TTS. Evento concluído continua protegido contra duplicação.

## Estados públicos

| Estado | Significado e apresentação | Não concluir |
| --- | --- | --- |
| `pending` / `in_progress` | Tarefa conhecida/rodada em andamento; “Em processamento” | Que já existe texto utilizável ou que a voz é sintética |
| `blocked_uncertain` | Criação não confirmada; “Estado não confirmado”; reenvio bloqueado temporariamente | Que o provedor criou ou não criou a tarefa |
| `blocked_expired` | Acompanhamento local terminou; “Acompanhamento encerrado” | Que a tarefa remota acabou ou que uma nova tentativa é livre de duplicação |
| `capacity_exceeded` | Serviço ocupado; nenhum novo pedido criado nesta tentativa | Que uma tarefa foi iniciada, que houve silêncio ou que o conteúdo é falso |
| `success` / `no_speech` | Texto literal utilizável ou ausência de fala transcritível informada pelo provedor | Autenticidade da voz, identidade ou verdade da fala |

Avisos têm texto explícito, anúncio acessível e não expõem motivos/IDs brutos. Não há atualização automática do relatório. Texto legado válido prevalece sobre um marcador pendente antigo; vídeo declarado sem áudio não recebe aviso fictício de transcrição.

## Limites, retenção e o que NÃO foi resolvido

- **Uma instância/processo, janela finita.** Não há garantia após reinício, outra réplica/worker, perda do contexto ou remoção do registro. Configuração efetiva de réplica no Railway ainda precisa ser conferida.
- Máximo de **64 registros** e **8 workers** de transcrição; fila cheia recusa novo trabalho, sem expulsar uma tarefa ativa para abrir espaço. Isso limita operações, não estabelece um teto absoluto de RAM de toda a aplicação.
- Pendência/criação incerta: **30 minutos desde a criação**, sem renovação por leitura. Depois, marcador de expiração por mais **5 minutos**; após remoção, uma nova tentativa pode criar outra tarefa.
- Resultado concluído: **5 minutos desde a conclusão**. Falha determinística: **60 segundos**. Depois da remoção, pode haver nova criação. A proteção não é um cache permanente.
- Timers removem texto/ID do cache ASR mesmo em serviço ocioso; desligamento cancela workers/timers e limpa esses registros. Isso não apaga histórico no banco, relatórios da aba, PDFs ou cópias já exportadas. Áudio e chave não são guardados nos registros; objetos de resposta/credenciais temporários são descartados pelo worker.
- A limpeza é **local**. Não remove artefatos nos servidores AssemblyAI nem implementa uma política completa de retenção/exclusão. Ver [orientação oficial de retenção](https://support.assemblyai.com/articles/2240096256-does-assemblyai-offer-zero-data-retention).
- ASR pendente/incerto/expirado ou sem capacidade não dispara fallback Gemini automático naquela passagem pelo AssemblyAI. Quando Gemini é preferido, pode ser tentado antes; isso não é deduplicação global de todos os provedores.
- Nova análise pode consultar outros detectores novamente. A proteção é de transcrição AssemblyAI, não de todas as camadas, histórico, quotas ou fatos.
- Para operação pública/múltiplas réplicas: checkpoint durável compartilhado, limites globais, política de exclusão/retenção e testes de reinício/falha ainda são gates.

## Testes automáticos

Resultado final: **424 backend**, zero skips/falhas/HTTP inesperado. Executados em Python 3.11, Docker QA não-root, filesystem read-only e rede externa desabilitada.

A mesma suíte passou no modo PostgreSQL descartável. Não são 848 testes distintos: somente três testes exercitam integração real PostgreSQL (histórico, estatísticas e prontidão); os restantes permanecem SQLite/mocks. Cadastro/login/upload/revisão/PDF com banco PostgreSQL real continuam pendentes.

**124 frontend**, zero skips/falhas; build passou, **1.976 módulos**. Novos testes de UI renderizam também os componentes reais com estado inicial controlado, sem API ou browser storage.

Novas regressões desta etapa:

- 23 de operação ASR: sequência, concorrência, cancelamento durante criação/polling, timeout ambíguo, HTTP 503 no polling, chave/projeto/contexto, validade, capacidade, expiração ociosa, respostas inválidas, campos permitidos e fallback.
- 18 de contexto/rotas: conta versus nonce, contexto sem escopo, reset após erro/cancelamento, herança nas tarefas de vídeo, cinco entradas, simulator e webhook pendente → concluído → duplicado, resposta/histórico/snapshot sem identificadores internos.
- Uma regressão PDF com dez subcontroles de estado/modalidade; renderização visual adicional de duas páginas, sem texto cortado ou sobreposto. É um PDF simulado, não exportação final observada pelo navegador.
- 19 de apresentação e quatro de nonce na interface. A suite anterior tinha 101 testes frontend; esta tem 124, não uma taxa de acerto de detectores.

## Ensaio pela interface: somente transporte simulado

Harness: `backend/scripts/local_asr_pending_server.py`. Cria SQLite descartável, ignora dotenv, desabilita chaves reais e bloqueia transportes HTTP externos. MockTransport controla apenas os endpoints AssemblyAI esperados. Entrada: tom WAV gerado de um segundo, **não voz humana**. A frase abaixo foi fornecida pelo mock; não foi reconhecida do áudio.

Controle do arquivo: SHA-256 `9e2c610d9b40fbfe83c6de65590d815834bfd2669e493c58ec526874222ec545`.

| Passagem pela interface final | Resultado observado | Contador simulado acumulado |
| --- | --- | --- |
| Primeiro upload na mesma aba | Relatório inconclusivo, cobertura “Em processamento” e aviso de pendência | 1 upload, 1 criação, 1 consulta |
| Modo Fácil | Aviso ampliado legível, sem tratar pendência como ausência de fala; captura desktop | Sem nova chamada de transcrição |
| Nova checagem do mesmo arquivo, mesma aba | Texto retornado abre a conferência humana | **1 upload, 1 criação, 2 consultas** |

Texto controlado mostrado no editor: “CONTROLE SIMULADO. Não envie dinheiro. Valor R$ 123,45. Data 03/10/2026.” Negação, valor e data retornados pelo mock foram preservados na UI. A confirmação de fidelidade não foi marcada: o áudio de entrada era um tom, não aquela frase. Este ensaio valida retomada e transporte/apresentação, **não reconhecimento de fala ou precisão**.

Na primeira passagem de verificação foi encontrado um rótulo contraditório de cobertura (“Não disponível” para pendente). Foi corrigido e o ensaio final foi reiniciado. Só a sequência final acima compõe os contadores preservados. Não somar a tentativa anterior como mais um acerto.

Evidências:

- [Contagens e limites do ensaio](evidencias-2026-10-07/asr-resume-summary.json).
- [Pendência normal](evidencias-2026-10-07/ui-asr-pending.png).
- [Pendência em Modo Fácil](evidencias-2026-10-07/ui-asr-pending-easy.png).
- [Texto controlado na conferência](evidencias-2026-10-07/ui-asr-resumed-review.png).

Ensaio desktop parcial; não fecha o checklist mobile/zoom/teclado/movimento reduzido de SEM-18. Salvamento e abertura de um PDF pelo navegador integrado ainda não foram comprovados.

## Próximos gates de fechamento

**Atualização de 08/10:** a guarda de reenvio no interceptor abaixo foi corrigida e coberta por 18 controles locais; [registro do candidato](ENTREGA-BANCA-2026-10-08.md). O achado histórico permanece documentado. Cookies tardios, pedidos já despachados e homologação de sessão/servidor continuam pendentes.

1. Corrigir/testar reenvio automático após renovação de sessão: não reenviar POST antigo, validar contexto antes/depois de refresh e antes de logout, e invalidar contexto antes de login/cadastro/Google mudar cookies. Não confundir isolamento do cache ASR com proteção completa de todas as corridas de sessão.
2. Preservar/integrar alterações legítimas do original num candidato revisado. Original e revisão estão sujos e partem de HEADs diferentes; não copiar a pasta inteira nem publicar master cegamente.
3. Construir a imagem final efetivamente usada no Railway; revisar execução root, conteúdo de build e contexto. A imagem QA anterior não valida automaticamente o Dockerfile candidato.
4. Ampliar integração PostgreSQL real para sessão, URL, upload, conferência, histórico e PDF/isolamento; preparar migração e recuperação.
5. Executar CI no SHA candidato antes de promover/publicar, e depois smoke identificável em Vercel/Railway.
6. Homologar Gemini/OpenRouter por modalidade e fala/vídeos humanos autorizados; manter indisponibilidade/inconclusivo explícitos até haver evidência.

Auditoria adicional de sessão, somente leitura/adapter Axios simulado: o interceptor 401 de `frontend/src/services/api.js` reexecuta a requisição original sem verificar se conta/epoch mudou durante a renovação. Um controle offline modelou A → 401 → refresh suspenso → troca B → refresh concluído e observou dois uploads apesar do contexto original inválido. Também há caminho de logout antigo sem essa guarda. **Não foi comprovado incidente ou gravação real no histórico de B**: a rota `/upload` atual usa autenticação opcional, e cookie expirado normalmente vira anônimo, não 401. O controle comprova a lacuna do interceptor, não um exploit completo da aplicação. Correção e regressões de troca de conta ficam como gate P0 de SEM-11, antes de publicar o candidato.

Gemini OCR/inspeção continuou **não homologado** pelos resultados reais anteriores (HTTP 503). Esta etapa não fez novas chamadas para retestá-lo. Não afirmar que todas as APIs funcionam nem que os vereditos são 100% corretos.
