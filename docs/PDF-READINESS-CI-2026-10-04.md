# Verify - PDF, conectividade do banco e CI

Rodada local de **04/10/2026**. Base Git `5db970da8f8a109472050ed96e3ab77d20e7f5e7`, com mudanças locais desta revisão e etapas anteriores. **Sem commit, push, publicação ou alteração do banco de produção.** Trabalho na cópia `verify-reviewed`; o checkout original, com alterações próprias, foi preservado.

Esta etapa melhora apresentação/robustez e reprodução dos testes. **Não valida novamente APIs reais nem mede precisão dos detectores.** Situação das integrações continua em [validação pela interface](VALIDACAO-INTERFACE-2026-10-04.md); conferência humana de OCR/transcrição, em [etapa anterior](CONFERENCIA-TEXTO-2026-10-04.md).

## PDF: ausência não é zero

O gerador convertia campos opcionais nulos em `None`, inclusive pontuações faciais e sinais IA. Agora:

- Ausências ficam como “Não disponível”/“Não informada”, conforme o campo. Zero real continua zero.
- Sinais exibidos exigem número finito entre 0 e 1; booleanos, strings e números fora da escala não são pontuações válidas.
- Escala e limites são explicados uma vez, sem apresentar os sinais como probabilidade de verdade ou precisão.
- Conteúdo aguardando revisão, ausência de texto/fala e campos sem data/avaliação ficam explícitos.
- Assinatura, finalidade, validade, conta e cópia original da exportação permanecem iguais. Renderização não altera o JSON assinado, não repete a análise e não consome quota diária de análise.

Controles automáticos incluem campos nulos, zero, valores inválidos, fontes incompletas, integridade do relatório e extração de texto por Poppler. O controle visual fictício foi exportado pela rota real em `TestClient`, renderizado em **duas páginas**, conferido sem cortes/sobreposição e sem tokens/`None`. Tem **5.679 bytes**, SHA-256 `e35973ed5d571cdb21cf17fcbbe1fdb6aed27f2298751c7ed1c6611c97961d4d`. É **fixture de apresentação**, não análise de um conteúdo real. Exportação de texto/link e compatibilidade com relatórios legados continuam limitadas conforme a etapa anterior.

## Saúde: três informações diferentes

| Rota | O que informa | O que não comprova |
| --- | --- | --- |
| `/health` | Processo respondendo, HTTP 200 | Banco, APIs, qualidade dos resultados |
| `/ready` | `SELECT 1` no banco: 200 se responder, 503 se falhar/timeout | Schema/migrações, permissões de escrita, quotas, APIs ou precisão |
| `/api/capabilities` | Presença de configurações e ferramentas; operação `not_tested` | Credencial válida, crédito disponível ou detector validado |

`/ready` tem deadline de 2 s, cache de resultados concluídos por 2 s e coalescência de consultas simultâneas por processo. Erros/hosts/URLs do driver nunca entram na resposta. Timeout não se torna sucesso; cancelamento libera a conexão. As rotas de saúde têm `Cache-Control: no-store`; o cache interno curto não é cache HTTP.

Nove controles específicos cobrem conexão SQLite real, consulta read-only, fechamento, simultaneidade, cache negativo/recuperação, timeout de conexão/consulta, resposta inesperada, cancelamento e contrato HTTP. A suíte de queries também testa conexão ao banco descartável configurado, inclusive PostgreSQL.

Controle adicional com PostgreSQL local real, pela rota HTTP em processo:

- Banco temporário ligado: `/ready` **200**, `database=ok`; `/health` **200**.
- Após remover apenas esse banco temporário: `/ready` **503**, `database=unavailable`; `/health` continua **200**, sem detalhes da conexão.

Os dois `railway.toml` **locais** apontam agora para `/ready`. Não alteramos o painel remoto. No próximo deploy, conferir qual arquivo/configuração está efetivamente em uso. O healthcheck de implantação do Railway não substitui monitoramento contínuo após a publicação, conforme a [documentação oficial](https://docs.railway.com/deployments/healthchecks).

## Runner offline e workflow

Execução dentro de `backend`, com `requirements.txt` e FFmpeg/ffprobe/Poppler instalados:

```bash
python -B scripts/run_offline_tests.py
```

O runner cria e remove seus próprios SQLite temporários, ignora as URLs de banco herdadas e `.env`, gera segredos de teste independentes, desliga credenciais de fornecedores e bloqueia transportes HTTP reais. Tentativa inesperada bloqueada também reprova a execução, mesmo se o código da aplicação capturar a exceção. Teste pulado reprova; não vale contar skip como verificação concluída. Mocks e o transporte em processo de `TestClient` seguem funcionando. Não é uma sandbox para código arbitrário; no controle Docker usamos também `--network none`.

PostgreSQL é opt-in:

```bash
python -B scripts/run_offline_tests.py --postgres-test-url postgresql+asyncpg://verify_test:local-ci-test-only@127.0.0.1:55436/verify_ci_test
```

Esse exemplo usa **credencial fictícia**, somente para um contêiner descartável previamente criado para testes. O runner aceita apenas loopback, driver asyncpg, nome contendo `test` e URL sem parâmetros extras. **A suíte recria as tabelas: nunca usar um banco real, mesmo se local, nem túnel para produção.** Essas variáveis/credenciais não devem ser copiadas para Railway/Vercel.

`.github/workflows/tests.yml` prepara:

- Backend em Python 3.11 com matriz SQLite/PostgreSQL 16 descartável e ferramentas de mídia/PDF.
- Frontend em Node 22, `npm ci`, 79 testes e build.
- Permissão `contents: read`, checkout sem persistir credenciais, Actions fixadas por SHA, prazo máximo e cancelamento de execuções substituídas.
- Sem `secrets`, pull de variáveis remotas, testes pagos ou deploy. Instalar dependências usa rede; isso não equivale a permitir chamadas reais nos testes.

YAML analisado localmente, refs das Actions conferidas nos repositórios oficiais e comandos executados. **O workflow ainda não rodou no GitHub.** Antes de anunciar que ele bloqueia deploys, publicar em branch de revisão, conferir todos os checks e exigir sua aprovação nas regras da branch/integrações. Autodeploy não foi inspecionado/alterado. Referências: [sintaxe de workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [serviço PostgreSQL descartável](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers), [checks de branches protegidas](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

## Resultados registrados

| Controle | Resultado |
| --- | --- |
| Backend, SQLite, Docker/Python 3.11, rede desligada | **256 testes aprovados**, zero skips/tentativas inesperadas de HTTP, 6,747 s |
| Backend, PostgreSQL 16 descartável, Python 3.12 | **256 testes aprovados**, zero skips/tentativas inesperadas de HTTP, 7,781 s |
| Frontend | **79 aprovados**, zero falhas/skips |
| Build frontend | **Aprovado**, 1.974 módulos, 3,13 s |
| PDF fictício: extração + duas páginas inspecionadas | **Aprovado**, sem alterar cópia assinada |
| Readiness PostgreSQL ligado/removido | **200/503**, liveness **200/200** |
| Workflow YAML e Actions | **Verificação estática local**, execução remota pendente |

São repetições da mesma suíte em ambientes diferentes, **não 512 amostras independentes de precisão**. JSON resumido em [validation-pdf-readiness-ci-2026-10-04.json](validation-pdf-readiness-ci-2026-10-04.json).

A imagem local de QA `verify-ci-runtime:20261004` acrescenta Poppler ao runtime local já existente. A primeira tentativa exigiu essa correção e não foi contada como sucesso: faltavam `pdftotext`/`pdftoppm`. Poppler é ferramenta de QA, não requisito para emitir PDF via ReportLab; Dockerfiles de produção não foram alterados nesta rodada. Contêineres de execução e banco fictício foram removidos; os seis serviços anteriores permaneceram em execução. Imagem de QA permanece local, sem publicação.

## Próximos bloqueadores de entrega

1. Fechar os **10 casos pendentes da matriz**, com mídia própria/autorizada e expectativa documentada. Corrigir/retestar erros reais de transcrição; não apagar os achados anteriores.
2. Consolidar seletivamente a cópia revisada com as alterações do checkout original, conferir segredos/diff e identificar a versão candidata. Não sobrescrever tudo nem publicar alterações não revisadas.
3. Rodar CI remoto e homologar conta, upload, revisão, relatório, histórico e PDF no **deploy dessa versão**, incluindo Modo Fácil/celular e indisponibilidade.
4. Fechar pacote de privacidade/operação antes de abrir ao público: retenção, exclusão de histórico/conta, aviso de terceiros, migrações e backup/restauração. Nesta etapa não foram implementados.

**Nenhuma chamada nova a APIs de análise; nenhum crédito consumido. Não existe comprovação de que todos os serviços/vereditos estejam corretos nem garantia de 100% de precisão.**
