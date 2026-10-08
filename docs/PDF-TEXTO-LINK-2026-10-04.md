# PDF de texto/link - revisão local de 04/10/2026

## Entrega e escopo

Novas análises de texto, link, lote e texto conferido podem exportar seu resultado original. Não repetem extração, consulta de fontes, modelos ou detectores. Esta etapa foi realizada na cópia `verify-reviewed`; o checkout original com mudanças do usuário foi preservado. Não houve commit/push/deploy ou chamadas novas a provedores.

Texto/link recebem tipo explícito e timestamp UTC da análise. Link preserva URL enviada, URL final, texto efetivamente analisado e método/limites da extração. O histórico já guarda esses dados e renova a capacidade de exportar somente para relatórios compatíveis da conta. Não refaz uma página para preencher informação ausente em registros antigos.

O PDF textual apresenta resultado factual, entrada, avaliações por afirmação, fontes correspondentes, fontes excluídas/motivos, cobertura e limitações. Não mostra EXIF/Hive como camadas de um texto nem atribui autenticidade de mídia a uma afirmação corroborada. Explica que precisão não é calibrada e índice não é probabilidade.

Conferência humana preserva separadamente leitura automática original, texto confirmado, arquivo/hash de origem e data da revisão. O hash identifica bytes; a edição não comprova correspondência ao arquivo ou autenticidade. A exportação não consome o token de revisão nem executa outra análise.

## Segurança

- Mesmo formato HMAC `vpdf1`, finalidade específica, uma hora e controle da conta original. Anônimo: capacidade bearer, não criptografia.
- Assinatura/autorização verificadas antes da renderização. Reenvio de arquivo, JSON não assinado, adulteração, expiração e token de revisão usado como PDF são recusados.
- Tokens anexados somente à resposta após commit; não entram no banco. Uma resposta de lote com erro fica sem PDF.
- Timestamp sem fuso, entrada/versão/avaliações ausentes ou resultado legado incompleto não geram uma reconstrução inventada.
- Em produção exige `HMAC_SECRET_KEY` forte/estável. Exportação sem assinatura fica indisponível, sem interromper a análise.
- Respostas de exportação usam `Cache-Control: no-store`. Detalhes técnicos copiáveis e snapshots não incluem `text_review_token`.

## Evidências

| Fronteira | Resultado observado |
|---|---|
| Backend offline | 274 testes, zero falhas/skips, Python 3.11 em Docker sem rede/chaves, SQLite descartável |
| Frontend | 84 testes individuais, zero falhas/skips; Node 22 |
| Build | 1.974 módulos; build concluído |
| Texto na interface | Controle fictício → inconclusivo sem provedores → exportação PDF/200 |
| Link na interface | Página fictícia por HTTP simulado no harness → inconclusivo → PDF/200 |
| Histórico | Dois registros; link reaberto e exportado sem nova análise → PDF/200 |
| Persistência | JSON/hash dos dois registros idênticos antes/depois de exportar e reabrir; nenhum token persistido |
| UI | Aviso acessível `role=status`: “PDF preparado”; zero erros de console. Dois avisos de futura mudança do React Router, não erros |
| PDF de exemplo | 2 páginas, 4.539 bytes; todas renderizadas e inspecionadas, sem cortes/sobreposição |
| Salvamento do navegador | **Não comprovado**: evento de download não entregue pelo navegador integrado; API/cliente responderam sem erro. Repetir em navegador de usuário |

Os testes controlam também os estados corroborado/refutado/discordante/não verificado com fontes **fictícias**, fidelidade do texto, URLs muito longas, procedência da conferência humana, exportação anônima, expiração e conta incorreta. Não são evidência de precisão real dos detectores.

Na primeira tentativa, o teste de uma URL longa falhou porque Poppler inseriu uma quebra de linha dentro do marcador final. O teste exige o marcador inteiro removendo apenas whitespace de layout; outras evidências continuam exigidas literalmente. Nenhum texto foi truncado para fazê-lo passar.

O exemplo entregue foi renderizado diretamente do relatório fictício persistido pelo controle de link, com o mesmo renderer da API. Não é apresentado como arquivo recuperado de um download que o navegador não confirmou. Poppler host emitiu aviso de cache Fontconfig sem escrita; renderização concluiu e as duas imagens foram conferidas.

Registro estruturado: [validation-text-pdf-2026-10-04.json](validation-text-pdf-2026-10-04.json). O harness não registra corpo/query/cookies/tokens. Foram usados dois processos descartáveis de UI: o primeiro tinha um registro de texto; o segundo, instrumentado, tinha dois registros e três respostas PDF. Comparação de persistência refere-se ao segundo processo.

## Reproduzir

Com dependências de backend e FFmpeg/ffprobe/Poppler instalados, rodar de `backend`:

```bash
python -B scripts/run_offline_tests.py
```

De `frontend`, com Node/dependências:

```bash
npm test
npm run build
```

O harness `validation_ui_server.py` permite ambiente sem chaves com `--providers ''` e arquivo `.env` vazio próprio, `--local-page-control` e porta exclusiva em localhost. `--container` exige publicação apenas em `127.0.0.1`. Não reutilizar banco/conta/segredos de produção para esses controles. Em ambiente com restrição a subprocessos do Node, conferir que o resultado enumera 84 testes, não somente arquivos.

Na aplicação local: conta fictícia do harness → texto fictício → PDF; nova checagem → Link `https://example.test/controle.html` → PDF → Histórico → reabrir link → PDF. Essa URL só existe como simulação explícita do harness, não como integração pública homologada. Nenhuma chave privada foi lida.

## Ainda pendente antes da entrega

1. Confirmar salvamento do PDF em Chrome/Firefox e no candidato implantado, não somente resposta da API.
2. Revisar/integrar o diff com as mudanças do checkout original, executar CI remoto e homologar Vercel/Railway.
3. Completar os oito controles da matriz que dependem de mídias originais autorizadas e acesso público. Matriz permanece 22 parcialmente executados / 8 pendentes.
4. Homologar os provedores pendentes dentro do orçamento autorizado; erros reais de ASR/LLM/HF anteriores não são resolvidos por exportação PDF.
5. Fechar retenção/exclusão, acessibilidade do escopo final e contingência de hospedagem. PDF atual não é tagged PDF: `role=status` na interface não certifica acessibilidade integral do documento.

Sem promessa de vereditos 100% certos. Nenhuma alteração de limiar ou divulgação de precisão foi feita nesta etapa.
