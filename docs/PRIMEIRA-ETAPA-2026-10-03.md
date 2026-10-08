# Verify — primeira etapa da entrega

Iniciada em **03/10/2026**, com fechamento/revisão de privacidade em **04/10/2026**, sobre a base `5db970da8f8a109472050ed96e3ab77d20e7f5e7`. Estas mudanças ainda não foram commitadas, enviadas ou implantadas. A produção e o banco de produção não foram alterados nesta etapa.

O trabalho antecipa as correções de histórico/privacidade e PDF do [plano de 14 dias](PLANO-ENTREGA-14-DIAS.md), com prazo de 17/10/2026. Não equivale a concluir todo o projeto nem a validar a precisão dos fornecedores.

## Entregue

### Histórico e painel

- Páginas de 20 registros e total calculado com os mesmos filtros da consulta.
- Busca em todo o histórico da conta, não apenas na página aberta. Pesquisa inclui resumo, consulta original, arquivo e link; `%`, `_` e `\` são tratados literalmente.
- Filtros de texto, link, imagem, áudio e vídeo. Links legados armazenados como texto com URL aparecem como links.
- Ordenação estável, busca com atraso curto e cancelamento de requisições antigas, erro visível com opção de tentar novamente.
- Relatório acessível por teclado; inconclusivos sem índice de veracidade inventado.
- IDs malformados recebem 422, em vez de erro interno; registros de outra conta não são expostos.
- Registros antigos com JSON nulo, texto ou lista não derrubam a página do histórico; há regressão para esses formatos.

### Dados no navegador

- Cache persistente automático de consultas/resumos retirado e registros legados removidos.
- Relatório atual apenas na sessão da aba, com formato versionado, limite de 1 MiB e dono confirmado. Se o navegador bloquear esse armazenamento, usa memória temporária.
- Saída/troca de conta limpa dados de análise; respostas antigas não reaparecem após a troca. Preferências de acessibilidade e dados de outros aplicativos permanecem.
- Sinal entre abas não contém nome, consulta ou token. Respostas da API usam `Cache-Control: no-store`.
- JSON técnico copiável não contém a credencial de exportação do PDF.
- Demonstração remonta seus controles privados ao receber o reset de sessão. Saída/entrada em outra aba descartou o rascunho do simulador no teste do navegador, mantendo o Modo Fácil e a aba selecionada. Relatório anônimo já exibido volta para a tela de envio quando limpo, sem ficar em branco.
- Streams de câmera/microfone são encerrados sem depender da referência DOM. Permissão resolvida depois de desmontagem/reset é parada imediatamente; callbacks de gravação, captura e resposta antiga são invalidados. Recursos/URLs existentes são liberados. Testado com recursos simulados, sem ligar câmera/microfone reais.

Não é isolamento contra extensões/scripts maliciosos. Arquivos já baixados não são apagados. Retenção/exclusão de histórico no servidor e exclusão de conta continuam pendentes.

### PDF consistente

- Exportação usa o relatório original assinado pelo servidor, preservando resultado, evidências, limitações, versão da política e data da análise.
- Não reenvia mídia, não consulta detectores, não cria outra análise e não consome a quota diária de análise. Limites de requisição/concorrência continuam ativos.
- Rejeita relatório arbitrário, reenvio antigo de arquivo, alteração da cópia assinada e exportação autenticada de outra conta.
- Validade de uma hora. Relatório compatível salvo no histórico recebe nova autorização de exportação ao ser aberto, sem nova análise. Análise anônima não fica salva no servidor; após expirar, não pode ser renovada pelo histórico.
- Estados traduzidos, textos longos distribuídos entre páginas, títulos e cabeçalhos preservados. Veracidade factual e origem da mídia continuam separadas.
- Falta de `HMAC_SECRET_KEY` forte/estável em produção desabilita apenas exportação, com motivo explícito. Rotação desse segredo invalida cópias antigas; coordenar com registros de integridade existentes.
- Token assinado não é criptografado e contém o relatório. Para anônimos, é uma credencial temporária bearer: não publicar, copiar para logs nem compartilhar.

PDF de texto/link e conversão de relatórios legados sem nome/hash originais não entram nesta etapa. Não são anunciados como funcionando.

### Explicação da leitura de mídia

A interface não afirma que houve transcrição quando não existe texto extraído. Distingue OCR de transcrição e informa ausência de leitura utilizável.

O simulador de WhatsApp informa que aceita mensagens de texto nesta tela, não envia ao WhatsApp real e pode ficar inconclusivo. Campos/ação de envio ganharam rótulos acessíveis. A rolagem acompanha somente a conversa, sem pular a página inteira ao remontar; no Modo Fácil/movimento reduzido, não usa animação de rolagem.

## Evidências dos testes

| Controle | Resultado |
| --- | --- |
| Backend, com SQLite descartável e credenciais externas desligadas | **212 testes + 141 subtestes aprovados**, nenhum ignorado |
| Backend, PostgreSQL 16.13 descartável em Docker | **212 testes + 141 subtestes aprovados** em 9,26 s; banco em tmpfs e porta apenas local, nenhum dado de produção |
| Interface, incluindo sessão/contas, busca, evidências, exportação e recursos de mídia simulados | **67 testes aprovados** em 10 arquivos; incluem 7 controles simulados de recursos e 5 regressões estruturais de demonstração |
| Compilação de produção da interface | Concluída sem erros |
| Docker da raiz, build/smoke offline | Aprovado; API/PDF, FFmpeg/ffprobe, Tesseract português/inglês e ExifTool presentes; `.env` ausente |
| Dockerfile isolado de `backend`, build offline | Bloqueado por cache de dependências insuficiente; instalação não terminou com rede desativada. Não é comprovação de erro do código; esse contexto ainda precisa de build homologado |
| HTTP local, aplicação real e banco fictício | **24/24 controles aprovados** |
| Navegador → API → banco → relatório/PDF | Login/saída, duas contas, 45 registros em 20/20/5, busca fora da primeira página, filtro de vídeo, abertura por teclado, upload de imagem com APIs desligadas e exportação conferidos |
| Modo Fácil em 320 × 800 px | Relatório e botão de PDF sem rolagem horizontal; largura útil 305 px, largura da página 305 px |
| PDF final | Exportado por HTTP e inspecionado visualmente; stress multipágina automatizado preservou finais de textos, OCR/transcrição e URLs extensos |

Registro sem credenciais/conteúdo pessoal: [24 controles HTTP](release-controls-local-2026-10-03.json). Os resultados inconclusivos fictícios do histórico não são resultados de detectores. No upload real local, APIs estavam desligadas: o resultado correto foi inconclusivo, sem fabricar autenticidade/falsidade.

Execuções finais SQLite/PostgreSQL tiveram um aviso de descontinuação do python-jose, sem falhas; uma execução anterior também avisou sobre AnyIO/Starlette. Usada imagem oficial `postgres:16-alpine` já local; contêineres descartáveis próprios removidos, sem volumes persistentes e sem alterar os serviços existentes. Não houve teste de fornecedores remotos, consumo de créditos ou instalação de dependências novas no host. Produção desta revisão ainda precisa de homologação; testes locais não comprovam o código novo implantado.

Build Docker usou `--network=none --pull=false` e cache local. Imagem raiz preservada: `verify-first-stage-root:20261004-pdf` (`a477aded1674`). Smoke sem portas/rede, com segredos fictícios e SQLite, carregou 29 rotas e ferramentas. O contexto isolado do backend perdeu o cache de instalação após `COPY requirements.txt`; com rede desativada, `pip` não conseguiu completar. Não foi liberada rede/baixada dependência para contornar isso. O intermediário próprio da falha e os contêineres de smoke foram removidos; serviços preexistentes ficaram intocados.

## Reproduzir sem chaves privadas

Use dependências já instaladas. Dentro de `backend`, execute a suíte apenas contra um banco **descartável**: os testes recriam tabelas.

```bash
TEST_DATABASE_URL=sqlite+aiosqlite:////tmp/verify-release-test.db python -m pytest -q
```

Em `frontend`:

```bash
npm test
npm run build
```

Controles ponta a ponta, em dois terminais dentro de `backend`:

```bash
python scripts/local_release_server.py --port 8026
```

```bash
python scripts/release_http_probe.py --base-url http://127.0.0.1:8026 \
  --output /tmp/verify-release-controls.json --pdf-output /tmp/verify-release-control.pdf
```

O servidor cria seu próprio banco temporário, ignora `.env` privado, desliga provedores e escuta somente em `127.0.0.1`. Contas/senhas são fictícias e estão no script; não é configuração de deploy. Reiniciar gera segredos e banco novos. Ao terminar, encerre o servidor; arquivos temporários permanecem para conferência.

Para testar a interface nesse servidor, execute dentro de `frontend`:

```bash
VITE_API_URL= VITE_API_PROXY_TARGET=http://127.0.0.1:8026 \
  npm run dev -- --host 127.0.0.1 --port 5176 --strictPort
```

`VITE_API_URL=` evita que um `.env` local aponte os testes ao backend de produção.

## Próxima etapa

1. Executar a [matriz de 30 casos preparada](MATRIZ-VALIDACAO-30-CASOS.md): todos permanecem pendentes nesta rodada. Cinco arquivos conhecidos disponíveis; 15 arquivos/HTML propostos ainda faltam, além de checagens factuais reais. Obter origem autorizada e fixar expectativa antes de testar; variantes não contam como amostras independentes.
2. Validar fornecedores disponíveis apenas dentro dos créditos gratuitos autorizados. Hive pago permanece pausado; HF continua experimental, sem voto.
3. Corrigir falhas de leitura/checagem encontradas e oferecer conferência de OCR/transcrição quando insuficientes.
4. Definir apresentação/piloto restrito ou lançamento público; no segundo caso, priorizar exclusão/retenção no servidor, migrações, backup e avisos de processamento.
5. Conferir saldo/expiração Railway, concluir o build do contexto `backend` e homologar o deploy candidato antes de publicar. Docker raiz e PostgreSQL local desta etapa já foram validados; isso não comprova banco/migrações em produção.

Não há garantia de vereditos 100% certeiros. Estes testes demonstram controles e coerência dos fluxos cobertos, não precisão universal.
