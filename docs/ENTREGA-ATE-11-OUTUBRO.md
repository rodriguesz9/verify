# Verify — fechamento de 07 a 11/10/2026

**Checkpoint de 10/10:** [diagnóstico e correções dos inconclusivos](INCONCLUSIVOS-2026-10-10.md): consultas literais, atribuição limitada de fontes e diagnóstico útil de mídia; 554 backend/169 frontend e build locais aprovados. Hive foi autorizado com saldo existente e limites de imagem/áudio; a linha “pausado” abaixo é estado histórico de 07/10, não configuração atual. Voz/vídeos humanos, precisão independente e demais gates de lançamento continuam pendentes.

Prazo informado nesta rodada: **terminar nesta semana**, interpretado como domingo, 11/10/2026. Este roteiro antecipa o plano de 14 dias; não apaga seus riscos, critérios de aceite ou evidências anteriores.

**Meta viável sem novas contratações:** candidato estável para apresentação/piloto limitado, com funções verificadas, serviços gratuitos limitados, relatórios claros e comportamento seguro quando faltar evidência. Lançamento irrestrito só depois dos critérios adicionais de operação, privacidade e orçamento. A escolha do público ainda precisa ser confirmada pelo responsável.

Não prometer “100% de vereditos certos”. API que respondeu, teste automático verde, conta com chave presente e precisão do detector são quatro coisas diferentes. O produto deve saber concluir **não determinado**, sem transformar uma indisponibilidade em falsidade nem ausência de sinais em autenticidade.

## 1. Prioridade e definição de pronto

1. Corrigir bugs que distorçam resultado, sessão, armazenamento ou privacidade.
2. Fechar o caminho interface → backend → serviço/banco → relatório → histórico → exportação.
3. Ensaiar controles com origem conhecida e registrar erros, abstenções e cobertura; não somente acertos.
4. Publicar uma revisão identificável e executar os mesmos controles críticos no ambiente publicado.
5. Preparar apresentação, documentação, limites e recuperação.

Uma tarefa só muda para concluída se houver evidência verificável. “Implementei”, “HTTP 200”, “deploy SUCCESS” e “há uma chave” não bastam para homologar uma função.

## 2. Calendário acelerado

| Data | Trabalho de fechamento | Critério de saída |
| --- | --- | --- |
| Qua 07/10 | Sessão/Google, URLs, estados de APIs, formato da voz, C2PA conservador, vídeo visual versus áudio, regressão e corpus de imagens | Código local sem regressões; chamadas reais e falhas registradas separadamente; nenhum segredo exposto |
| Qui 08/10 | Diagnóstico Gemini, quotas/modelos gratuitos, ASR pendente, OCR/transcrição com negações/datas/valores e conferência humana | Serviços essenciais com sucesso real reproduzível ou desativação/fallback explicitamente informado; nenhuma cobrança/repetição automática para mascarar erro |
| Sex 09/10 | Vídeos/voz humanos autorizados quando fornecidos; controles transformados; responsividade, Modo Fácil, privacidade entre contas e PDF | Matriz com resultado e limitação por caso; nenhum sinal acústico atribuído às imagens; ensaio mobile/idosos compreensível |
| Sáb 10/10 | Integração das alterações sem perder o repositório original; candidato versionado; ambiente de homologação PostgreSQL; commit/push/publicação se gates passarem | SHA/revisão identificados em cada plataforma; fluxos críticos passando no candidato; caminho de rollback e backup definido |
| Dom 11/10 | Smoke final publicado, ensaio de apresentação, documentação/evidências finais e congelamento | Entrega do escopo aprovado, lista explícita de exclusões e contatos/instruções de operação; sem bugs críticos conhecidos |

Orçamento inicial de trabalho restante: aproximadamente 20–30 horas, a revisar conforme os testes reais. Dependências externas (quotas, acesso a modelos, arquivos do responsável) não têm prazo garantido pelo código. Não contar com a ativação de serviços pagos para cumprir esta estimativa.

## 3. Lista rastreável de fechamento

Checkpoint histórico de 07–08/10, preservado para rastreabilidade. Não representa o deploy atual: a publicação, os serviços e os controles posteriores estão no [registro de 10/10 com retomada em 11/10](INCONCLUSIVOS-2026-10-10.md). Em especial, SEM-06 teve inspeção Lite respondendo, e SEM-14 teve publicação confirmada em ambas as plataformas. Isso não encerra os critérios de precisão, voz/vídeo humano, sessão/PDF e operação.

| ID | Prioridade | Trabalho | Aceite | Situação no checkpoint histórico |
| --- | --- | --- | --- | --- |
| SEM-01 | P0 | Bloquear login de conta inativa, verificar identidade Google e associação segura | Sem cookie/mutação em falha; email verificado booleano; conflitos falham fechado | Correção e regressões locais prontas; Google real pendente |
| SEM-02 | P0 | Alinhar URL de entrada/final com coluna de 512 | Excesso retorna 422 antes de análise/persistência; não truncar; contar protocolo automático | Implementado e testado localmente; fluxo PostgreSQL publicado pendente |
| SEM-03 | P0 | Separar sinais de imagem e áudio de vídeo | JSON, título, explicação e PDF não atribuem voz sintética às imagens | Correção local com regressões; controles humanos pendentes |
| SEM-04 | P0 | Não certificar C2PA sem homologação | Marcadores/comentários não votam; ações/URI exatas; confiança runtime não validada | Inspeção conservadora implementada; corpus/CLI real pendentes |
| SEM-05 | P0 | Corrigir voz educativa | WAV válido ou PCM16LE correto, sem cabeçalho duplicado/beep; falha explícita; limites e timeout | Formatos/regressões offline prontos; fidelidade TTS real pendente |
| SEM-06 | P0 | Diagnosticar Gemini real | Texto e OCR controlados respondem ou causa/estado fica documentado; sem retry/fallback pago | Prazos corrigidos; 3.8 respondeu ao controle de texto; OCR/inspeção 503. OCR local passou pela UI; nuvem ainda não homologada |
| SEM-07 | P0 | Homologar OpenRouter gratuito por modalidade | Texto literal com modelo real registrado; visão/OCR precisa endpoint gratuito compatível | Texto respondeu; fallback OCR falhou/indisponível nesta rodada |
| SEM-08 | P0 | Evitar ASR pendente criar jobs duplicados em nova tentativa | Retomada/idempotência limitada e privada, ou fluxo que explique pendência sem incentivar reenvio imediato | Implementado/testado localmente por conta/aba e janela/processo; UI simulada 1 criação/2 consultas. Checkpoint durável/réplicas e ASR humano ainda pendentes; ver registro de retomada |
| SEM-09 | P0 | Testes reais de fala | AUD04/AUD06 com negação, valor, data; original comparado manualmente | Aguardando arquivos humanos autorizados |
| SEM-10 | P0 | Testes reais de vídeo | VID02/VID04 e cópias comprimidas; verificar áudio, quadros, tempos e limites | Aguardando arquivos; vídeos programáticos não substituem os humanos |
| SEM-11 | P0 | Conferir relatório/PDF/histórico | Mesmo resultado original; isolamento entre contas inclusive troca durante refresh; sem chamadas extras no PDF | Replay de POST/conta antiga corrigido em 08/10, 18 regressões locais; cookies tardios/ownership servidor e homologação de sessão continuam pendentes. Salvamento PDF no browser pendente; [candidato](ENTREGA-BANCA-2026-10-08.md) |
| SEM-12 | P0 | Contenção de custo e falhas de providers | Somente modelos gratuitos permitidos; limite inclui falha; serviço indisponível não declara sucesso | Guardas locais implementadas; limites por processo não são quota global persistente |
| SEM-13 | P0 | Banco/deploy | PostgreSQL descartável + fluxos de app em homologação; migrations/rollback antes de alterações de schema | Consultas de histórico/stats/readiness passaram em banco isolado; toda aplicação PostgreSQL ainda não homologada |
| SEM-14 | P0 | Integrar Git e publicar | Preservar mudanças do original; diff revisado, testes/build, commit/SHA, Vercel + Railway e smoke | Candidato `entrega/banca-2026-10-08` preparado com original preservado; 424/142 e build passaram. Confirmar SHA/checks remotos antes de promover; sem homologação nova Vercel/Railway |
| SEM-15 | P1 | Corpus de imagens com procedência | Foto de fonte primária + imagem IA declarada, hashes e rótulos separados | NASA/IA preparados; dois controles passaram pelo upload real nesta rodada |
| SEM-16 | P1 | Não declarar inspeção por JSON vazio nem ausência de matches em erro | Contrato de Vision validado; erros TinEye/Wayback não parecem sucesso | Corrigido com regressões offline; serviços pagos não habilitados |
| SEM-17 | P1 | Entitlement Sightengine e detectores adicionais | Documentar modalidades acessíveis; imagem não prova acesso a fala/faceswap | Imagem respondeu nos controles; fala/face-swap não homologados |
| SEM-18 | P1 | Responsividade/Modo Fácil | Mobile, zoom 200%, teclado, texto grande, movimento reduzido, sem corte de conteúdo | Revisões anteriores existentes; ensaio completo no candidato pendente |
| SEM-19 | P1 | Manual final e apresentação | README/manual coerentes com código, limites reais e roteiro de contingência | [Roteiro da banca](ROTEIRO-BANCA.md) e [status/configuração atuais](STATUS-VERIFICACOES-2026-10-08.md) prontos; ensaio no candidato ainda necessário |
| SEM-20 | P0 público | Retenção/exclusão/backup/restore e sessão | Política efetiva, exclusão de conta/histórico e recuperação ensaiada; revogação/associação OAuth explícita | Pendente; impede considerar lançamento aberto 100% concluído |

## 4. APIs: manter orçamento e alcance claros

| Serviço | Papel autorizado | Não confundir com | Condição para esta semana |
| --- | --- | --- | --- |
| Google Fact Check | Buscar checagens publicadas | Falta de match ≠ afirmação falsa | Manter política de correspondência e duas famílias editoriais; evidências exibidas |
| Serper | Buscar notícias relacionadas | Notícia relacionada ≠ checagem correspondente | Contexto apenas; crédito gratuito limitado |
| OpenRouter gratuito | Selecionar trechos literais/auxiliar OCR quando há modelo compatível | LLM não decide verdade | Preço máximo zero; modelos gratuitos e falhas observáveis; não contratar endpoint pago |
| Gemini | Extração/inspeção/transcrição/voz auxiliar | Explicação de IA não é prova | Modalidades testadas separadamente; não substituir palavra/valor/negação sem conferência |
| AssemblyAI | Transcrição | Voz humana, identidade ou fato verdadeiro | Somente créditos gratuitos; pendências de job/idempotência e voz humana a fechar |
| Sightengine | Sinal de IA/manipulação no modelo acessível | Score não é probabilidade calibrada de falsidade | Imagens reais/sintéticas controladas; fala/facial precisam testes próprios e acesso |
| Hugging Face | Sinal experimental não votante | Token/HTTP 200 não calibram o modelo | Manter fora do veredito, sem porcentagem de certeza; modelos anteriores erraram controles |
| Hive v3 | Detector de imagem/áudio com crédito | Um projeto não garante todas as modalidades | Pausado; não habilitar tráfego pago nem recarregar. Autorização antiga de US$ 0,01 não é orçamento de produção |
| SerpAPI | Busca reversa de URL pública | Busca não realizada ≠ sem correspondência | Só URL pública autorizada; não publicar uploads privados para ativar busca |
| C2PA/ExifTool/FFmpeg/Tesseract | Inspeção/procedência/decodificação/extração local | Metadata não prova verdade; ferramenta instalada não homologa confiança | Sem API paga; campos e limites precisam ser interpretados corretamente |

**Consequência importante:** no perfil sem novas contratações, pode faltar um segundo detector independente homologado. Um sinal de 99% de um detector continua sendo **um sinal**, não uma certeza de IA ou falsidade. Não ligar o Hugging Face ao voto apenas para obter mais conclusões.

## 5. Arquivos solicitados ao responsável

Caixa de entrada local criada: `/mnt/externo/IMPORTANTES/mostra/arquivos-para-validacao/`, com subpastas `videos`, `audios` e `fotos`. Nada é enviado automaticamente. Orientações de consentimento e frases fictícias ficam no README da pasta. Não commitar esses arquivos nem credenciais.

O responsável informou que ainda não consegue fornecer arquivos nesta rodada. Fotos públicas de fonte identificada e geração de IA foram autorizadas como controles complementares. Isso **não fecha** a homologação de áudio humano, vídeo humano, identidade, clonagem ou sincronização labial.

## 6. Gates de publicação

- [ ] Escopo confirmado: piloto/apresentação ou público aberto.
- [ ] Código local integrado com alterações legítimas do repositório original.
- [ ] Suíte final sem skips/falhas e build final registrados na mesma revisão.
- [ ] Caminho PostgreSQL da aplicação em homologação, incluindo autenticação, URL, upload, histórico e PDF.
- [ ] Credenciais/quotas/entitlements reais dos serviços habilitados verificados sem expor valores.
- [ ] Voz e vídeos humanos recebidos/ensaiados ou removidos explicitamente da promessa de validação.
- [ ] Gemini/OpenRouter por modalidade homologados ou apresentados com fallback/indisponibilidade explícitos.
- [ ] Sem claims de “100% preciso”, porcentagem calibrada, certificado C2PA ou ausência de matches quando uma API falhou.
- [ ] Commit/push identificados; Railway/Vercel publicam a revisão pretendida; CORS/cookies/configuração conferidos.
- [ ] Smoke público, recuperação/rollback e roteiro de apresentação registrados.
- [ ] Se lançamento aberto: retenção/exclusão/backup-restauração/sessão e limites compartilhados implementados e testados.

## 7. Como avaliar “bons vereditos”

Guardar, por caso: origem, transformação, SHA-256, resultado esperado, camada que respondeu, estado real, modelo, indicação e resultado da política. Não incluir chaves, URLs com token, cookies, IDs de usuário ou tokens assinados nos relatórios públicos.

Apresentar separadamente:

- **Cobertura:** quantos casos produziram evidência utilizável; quantos abstiveram e por quê.
- **Erros:** falsos positivos/negativos por detector e modalidade, incluindo casos em que os serviços divergem.
- **Veracidade factual:** conclusões corroboradas/refutadas exigem fontes correspondentes; triagem de golpe não é refutação universal da mensagem.
- **Origem da mídia:** sinal sintético não torna a informação falsa; ausência do sinal não comprova captura humana.
- **Extração:** conferir negações, datas e valores literalmente antes de checar o texto.

Dois controles exploratórios não autorizam afirmar uma precisão estatística. Testes automatizados comprovam regras/fluxos sob condições definidas, não verdade universal do conteúdo enviado.

## 8. Referências locais

- [Manual completo](DOCUMENTACAO-COMPLETA.md)
- [Plano original de 14 dias — backlog e critérios](PLANO-ENTREGA-14-DIAS.md)
- [Evidências e alterações de 07/10](FECHAMENTO-2026-10-07.md)
- [Retomada privada de ASR e suíte final 424/124](TRANSCRICAO-PENDENTE-2026-10-07.md)
- [Matriz de 30 casos](MATRIZ-VALIDACAO-30-CASOS.md)
- [Corpus publicado NASA](../backend/tests/fixtures/validation/internet-real-2026-10-07/README.md)
- [Controle de origem sintética conhecida](../backend/tests/fixtures/validation/generated-2026-10-07/README.md)
