# Continuação — HTML, OCR degradado e vídeo com áudio

Executado em 04/10/2026 na cópia **verify-reviewed**, sobre `5db970d`, com mudanças locais não commitadas. Não houve push/deploy, acesso ao banco de produção, chave privada usada ou nova chamada a provedor. Não é benchmark de precisão nem homologação das APIs.

## Resultado

- Corrigida a extração de links que apagava `<header>` do artigo, incluindo negações no título, e incluía textos ocultos na página.
- Corrigido `text/plain` sendo interpretado como HTML e perdendo caracteres/trechos literais.
- Relatório informa leitura estática, truncamento em 5.000 caracteres e limite de visibilidade CSS/JavaScript; não afirma verificar o site inteiro.
- Vídeo mantém status/motivos de fornecedores indisponíveis, contagens por quadro e falhas de cobertura parcial. Resposta apenas do detector facial conta como cobertura do fornecedor, sem inventar pontuação de geração por IA.
- Interface distingue presença de faixa de áudio de transcrição/detecção da voz. Mostra o motivo de indisponibilidade e “serviço não configurado” quando aplicável.

Não foram alterados limiares de OCR/detector, corrigidas palavras por suposição nem promovido HF a detector decisivo.

## Controles executados

| Controle | Observado | Limite |
| --- | --- | --- |
| LNK10 | Cabeçalho “Não pague…”, R$ 123,45 e 03/10/2026 preservados. Menu, scripts, template e valores/datas em elementos ocultos excluídos. Resultado `unverified`, sem alerta de pedido financeiro afirmativo. | HTTP simulado de arquivo local, inclusive pela UI. **Não valida uma URL HTTPS pública** nem fonte factual real. |
| OCR05 | Imagem rotacionada 3,5°, contraste 0,20, JPEG 55. Tesseract retornou quatro linhas, preservando “Nao”, valor e data. Leu **“Valor” como “valor”**. | Diferença literal registrada como falha na comparação estrita; não normalizada após observar o resultado. Não demonstra OCR universalmente fiel. |
| Revisão OCR05 na UI | Upload aguardou conferência. Capitalização editada explicitamente, confirmação marcada, nova análise textual gerada. Leitura original preservada; histórico mostrou imagem e texto como dois registros separados. | Confirmar a leitura não confirma sua fidelidade/verdade. Sem fontes neste ambiente, resultado inconclusivo. |
| VID-AUX01 | MP4 6,959002 s, imagem sintética em sequência e TTS eSpeak. FFmpeg extraiu três quadros e WAV de 6,966 s. UI informou tempos aproximados 0,7/3,5/6,2 s e áudio separado. | ASR/detectores desligados: texto vazio e resultado inconclusivo. **Não é acerto de detecção/transcrição**, captura humana, clone, face-swap ou lip-sync. Não substitui VID04. |

Arquivos e hashes/receitas em `backend/tests/fixtures/validation/extended/manifest.json`; procedência em [README das fixtures](../backend/tests/fixtures/README.md). O HTML está em `validation/links/pagina-controle.html`. São variantes de grupos existentes, não novos originais independentes.

O runner local executou **19 controles**, dos quais **18 cumpriram a comparação estrita**. OCR05 falhou apenas pela diferença de caixa; por isso o runner termina com código **1**, deliberadamente. Isso é distinto da suíte de regressão, que passou. Registro íntegro: [validation-extended-controls-2026-10-04.json](validation-extended-controls-2026-10-04.json).

## Verificação ponta a ponta

História testada: arquivo/link → API local → leitura e política → conferência quando necessária → registro no banco → relatório na interface.

- Backend descartável em Docker, Python 3.11, Tesseract português/inglês e FFmpeg/ffprobe reais. Frontend Vite exclusivo em localhost, sem usar contêineres existentes do usuário.
- `validation_ui_server.py`: `.env` vazio, nenhuma chave, nenhum provedor selecionado, transporte externo bloqueado. Hive permaneceu desativado. Banco SQLite/auth criados só para esta validação.
- Duas sessões descartáveis: primeira com imagem + texto revisado; segunda, após reinício controlado, com link + vídeo. Quatro registros fictícios conferidos por consulta read-only. Nenhum token de revisão/PDF foi persistido nesses registros.
- `--local-page-control` intercepta **apenas** a URL fictícia `https://example.test/controle.html`. É simulação HTTP explícita de QA, não configuração de deploy. Demais URLs continuam pelo fetch com defesa SSRF; testes confirmam isso e os limites de tamanho/tipo. Sem esse flag, não há interceptação.
- Interface confirmou a leitura negada do link, o aviso de leitura estática e a separação entre áudio/quadros/transcrição. Histórico confirmou os registros; checagens sem fontes/detectores ficaram inconclusivas.
- Modo Fácil em viewport 390 × 844: documento de 375 px de largura (barra de rolagem), sem overflow horizontal nos fluxos de conferência OCR e relatório de vídeo. Capturas conferidas. Sem erros de console; avisos preexistentes de flags futuras do React Router v7. Não é uma auditoria completa de acessibilidade/navegadores.

Evidência sanitizada da UI/banco e configuração: [validation-extraction-ui-2026-10-04.json](validation-extraction-ui-2026-10-04.json). Não contém credenciais/cópias assinadas. Os contêineres e servidor temporários desta rodada foram encerrados; serviços existentes do usuário preservados. Nenhum dado real foi excluído.

## Regressões e reprodução

Antes da correção, quatro novos testes reproduziram: título perdido/texto oculto incluído, região principal oculta selecionada, ocultação aninhada e marcações literais de `text/plain` removidas. Depois:

| Verificação | Resultado |
| --- | --- |
| Backend Docker/Python 3.11, SQLite descartável, rede `none` | **265 testes aprovados**, zero falhas/skips |
| Frontend Node 22.21.1 | **82 testes aprovados**, zero falhas/skips |
| Build Vite | **Aprovado**, 1.974 módulos |
| `git diff --check` | Sem erros |

Backend, em ambiente com dependências/FFmpeg/Poppler: `python -B scripts/run_offline_tests.py`, dentro de `backend/`. Frontend: `npm test` e `npm run build`, dentro de `frontend/`. Não aceitar saída que conte apenas arquivos em vez dos 82 testes individuais: nesta máquina foi necessário executar o runner Node fora da limitação de subprocessos do sandbox.

Controles locais: `python -B scripts/offline_validation_matrix.py --output /tmp/verify-controles.json`, dentro de `backend/`, com Tesseract/FFmpeg e **rede desativada**. Ignora dotenv e remove credenciais herdadas. Ainda retorna 1 pela divergência literal de OCR05. Não usar o runner de provedores remotos para reproduzir esta etapa.

## O que falta

A [matriz](MATRIZ-VALIDACAO-30-CASOS.md) passou de 20/10 para **22 executados em ao menos uma dimensão / 8 pendentes**: AUD04/05/06, IMG01/04 e VID02/03/04. Não são 22 acertos de classificação. URL HTTPS pública de LNK10 continua pendente como dimensão de integração.

Para avançar, obter originais próprios/autorizados, sem dados pessoais: foto de objeto/planta, vídeo curto desse objeto e gravações humanas dos roteiros da matriz; variantes editadas devem conservar referência/hash do original. As mídias sintéticas disponíveis não substituem esses controles.

Continuam pendentes: ASR com palavras críticas nas amostras reais; checagens factuais reais correspondentes recuperadas e revisadas; validação independente dos detectores; permissões/cotas e operação por API; C2PA com confiança configurada; CI remoto e publicação da revisão. HF permanece experimental. Não há garantia de vereditos 100% corretos.
