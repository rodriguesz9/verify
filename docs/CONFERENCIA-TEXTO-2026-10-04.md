# Conferência de OCR/transcrição antes da checagem — 04/10/2026

Implementada na **cópia revisada local**, base Git `5db970da8f8a109472050ed96e3ab77d20e7f5e7` mais alterações não commitadas. Não publicada em Vercel/Railway nesta rodada.

## Comportamento

1. A tela `/app` envia imagem, áudio ou vídeo com `review_text=true`.
2. O backend valida/analisa a mídia e extrai texto, mas **não consulta fontes para checar as afirmações extraídas**. Camadas de origem da mídia e triagem preliminar da fala continuam separadas. Outros clientes que não pedem conferência mantêm o fluxo anterior.
3. Quando há leitura de 10 a 5000 caracteres e assinatura disponível, a interface mostra o arquivo local, a leitura e um editor. Negação, números e datas não são corrigidos automaticamente. Editar desmarca a confirmação.
4. “Checar texto conferido” cria **nova análise de texto**, sem reenviar a mídia ou repetir detectores. Usa o limite diário normal de texto. A origem assinada mantém leitura original, método, provedor, SHA-256, nome e data; a edição/confirmação e sua data ficam identificadas no novo relatório.
5. “Ver só sinais da mídia” abre o relatório original; as afirmações permanecem não checadas. Sem leitura utilizável, nenhuma palavra é inventada. Sem assinatura, não há conferência vinculada; uma nova checagem textual manual continua possível.

Não há relatório combinado nem substituição retroativa de resultado. Para usuário autenticado, histórico guarda mídia original e novo texto separadamente. O novo resultado textual ainda não tem exportação PDF. O PDF da mídia original continua sendo cópia assinada, sem nova inferência.

**Confirmar a leitura é uma declaração do usuário, não certificação da fidelidade ao arquivo nem da verdade.** Isso mitiga erros como “Faz” → “Faço” e “Pix urgente” → “pic surgente”; não elimina erros ASR, não calibra detectores e não amplia a cobertura factual.

## Segurança e privacidade

- Nova rota `POST /api/check-extracted-text`: recebe apenas `text` e `review_token`; campos de origem/veredito não assinados são recusados.
- Vínculo HMAC com domínio/finalidade distintos de PDF/JWT, validade de 15 minutos e mesma conta quando autenticado. Reutilização não evita quota/admissão. Nenhum banco de tokens ou mídia é criado.
- Origem/assinatura/expiração verificadas antes de quota e chamadas externas. Corpo limitado a 64 KiB, texto literal até 5000 caracteres, marcação HTML recusada, requisições sem cache. Operadores `<`/`>` e `&` não viram entidades HTML na afirmação confirmada; nenhuma palavra é removida silenciosamente.
- Em produção requer `HMAC_SECRET_KEY` estável, forte e com pelo menos 32 caracteres. Chave ausente desabilita apenas o vínculo; reinício em desenvolvimento invalida tokens quando a chave temporária muda.
- Token de conferência não é gravado em histórico, aninhado no token PDF nem exibido no JSON técnico copiável. No frontend fica em memória durante a conferência, removido ao abrir o resultado original; logout/troca de conta e saída da tela limpam a revisão. URL local de prévia é revogada ao desmontar o componente.
- Credenciais anônimas são bearer e não criptografadas; não divulgar, registrar em logs ou usar como autenticação. A assinatura comprova procedência da leitura no servidor, não autenticidade da cena.

## Validação desta rodada

- **242 testes backend passaram**, sem skips, com SQLite descartável, chaves externas desligadas. Inclui 17 novos controles de assinatura, finalidade, expiração, conta, tamanho, validação/literalidade, quota e pausa pré-checagem, além de dois controles de agregação do histórico. Áudio/vídeo nessa etapa usam extrações controladas/simuladas nos testes; isso não é novo teste real dos provedores ASR.
- **79 testes frontend passaram**, sem skips; build Vite passou (1974 módulos; JS 398,40 kB / gzip 121,30 kB). `git diff --check` passou.
- Navegador: upload real de `impresso-base.png` → Tesseract real → editor → confirmação → relatório novo. Leitura original preservou quatro linhas; edição retirou o cabeçalho de controle e acrescentou acento em “Não”, mantendo R$ 123,45 e 03/10/2026.
- Botão inicialmente bloqueado; marcar e depois editar desmarcou a confirmação. Novo relatório identificou a edição e manteve resultado inconclusivo, sem indício de golpe na advertência negada. APIs de fontes desligadas ficaram explicitamente indisponíveis.
- Histórico autenticado exibiu dois registros distintos; abrir a mídia original mostrou as quatro linhas inalteradas e a checagem factual ainda pendente. Não houve atualização retroativa da análise.
- Segundo controle, `afirmativo.png`: “Ver só sinais da mídia” abriu o resultado original e manteve afirmações pendentes, sem atribuir verdade/falsidade ao conteúdo não checado. Após carregar a API de estatísticas corrigida, histórico com esse único inconclusivo mostrou índice “Não determinado”, não 50/100.
- Tela de conferência sem rolagem horizontal em 320, 375, 768 e 1280 px, com Modo Fácil ligado/desligado. Botões principais com pelo menos 48 px de altura nos oito controles. Viewport e preferência originais restaurados. Não equivale a auditoria WCAG integral nem teste de zoom de 200%.
- Sem tela vazia/overlay Vite ou erro de renderização; avisos existentes de migração futura do React Router continuam.
- A primeira tentativa anônima falhou porque o backend descartável encerrou; proxy registrou `ECONNREFUSED`, e a interface manteve a edição. Causa externa do encerramento não estabelecida. Ambiente reiniciado em segundo plano, sem mudar política da aplicação, seguido de repetição autenticada bem-sucedida.
- Servidor descartável sem chaves privadas, sem conexão ao Postgres de produção e com transporte externo bloqueado. **Nenhuma nova chamada de API externa** nesta rodada; OCR executado localmente. Containers preexistentes não foram alterados.

### Índice médio do painel

Durante o teste, dois relatórios inconclusivos apareciam no painel como média 50/100, a partir de placeholders legados. Corrigido: a API calcula média somente de registros `partial` com semântica de índice declarada e valor entre 0 e 100. Inconclusivos/registros não versionados não entram; ausência de base vira `null` e “Não determinado”, não zero ou 50. A quantidade de índices usados acompanha a média. Índice zero real é preservado. Isso continua **sem medir probabilidade de verdade nem precisão**, mesmo com base disponível.

Evidência visual: `verify-conferencia-texto-2026-10-04.jpg` e `verify-relatorio-conferido-2026-10-04.jpg` no diretório de artefatos da revisão. Controles anteriores e falhas ASR/HF permanecem em [VALIDACAO-INTERFACE-2026-10-04.md](VALIDACAO-INTERFACE-2026-10-04.md).

## Continua pendente

- Os 10 casos restantes da matriz, originais autorizados e testes ASR/deepfake independentes.
- Recuperação de fontes realmente correspondentes para afirmações verdadeiras/falsas; um resultado inconclusivo seguro não demonstra classificação correta.
- Detalhes cosméticos do PDF (`None`), retenção/exclusão e readiness do banco, conforme escopo de apresentação/piloto versus uso público.
- Integração da revisão na demonstração/WhatsApp, que seguem fluxo anterior; exportação PDF textual e revisão a partir de histórico não foram acrescentadas.
- Homologação autenticada no deploy candidato e publicação. Nenhum commit, push ou deploy nesta rodada.
