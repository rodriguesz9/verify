# Recuperação, espera e causas de inconclusivos — 22/10/2026

Revisão local. Não comprova publicação nem 80% de acerto. Plano e critérios em
[plano de acertos](PLANO-ACERTOS-2026-10-22.md). Dados da primeira rodada em
[JSON sanitizado](validation-recovery-2026-10-22.json).

## O que foi corrigido

1. **Leitura de páginas ao vivo:** fluxo explicitamente identificado conserva
   as atualizações, em vez de selecionar somente o artigo mais longo. Relógios
   continuam como contexto, não data do evento. Carrossel de “eventos principais”
   e conteúdo fora das entradas validadas não viram corpo factual.
2. **Referência legada BBC Mundo:** um parágrafo inteiro contendo apenas o widget
   XML escapado “Lea también” deixava aspas técnicas no contexto da notícia.
   Remoção exige estrutura íntegra e domínio/seção reconhecidos. Prosa, negação,
   citações, prefixos, sufixos e estruturas parciais permanecem.
3. **Descoberta bilíngue:** uma consulta editorial já existente pode usar termos
   conhecidos em inglês para instituição internacional explicitamente nomeada.
   Não acrescenta uma chamada, não traduz a afirmação avaliada nem cria fatos.
4. **Pesquisa orientada pela lacuna:** motivos fixos de rejeição dos trechos
   ajudam a buscar sujeito, intenção, data, valor ou contexto ausentes. Contagens
   são candidatos rejeitados, não votos/fontes nem revisão exaustiva.
5. **Relato esportivo espanhol:** construção completa pode distinguir país-sede,
   ano e vencedor. Sem tabela de campeões. Ficção, hipótese, atribuição, previsão,
   instruções e categorias incompatíveis impedem a leitura automática.
6. **Espera local Gemini:** a sexta tentativa em uma janela local de cinco por
   minuto era rejeitada imediatamente. Agora aguarda a liberação da janela,
   dentro do prazo já existente. Fila FIFO por modelo, até 32 pendentes por
   processo; cancelamento na fila não reserva chamada. Falha depois do envio
   continua contada. HTTP 429 mantém pausa e não ganha retry/rotação de modelo.
7. **Escopo da negação:** “não era uma cerimônia comum” não nega a entrega de um
   prêmio descrita depois. Refutação genérica por inversão exige enunciado
   completo correspondente, não uma negação solta na janela. Uma única data
   explícita idêntica pode mudar de posição; demais palavras/qualificadores
   permanecem. Caminhada humana e declaração legal preservam apenas os vínculos
   estruturais já validados, sem transformar prosa arbitrária em exceção.
8. **Silêncio em WAV:** PCM mono 16 kHz/16 bits já normalizado é inspecionado
   diretamente e reencodado sem metadados. Evita depender da inicialização do
   FFmpeg para esse formato. Outros formatos conservam o decodificador limitado;
   falha não é inventada como silêncio. Não autentica voz.

A primeira proposta do filtro de negação falhou em 15 regressões: descartava
leis válidas, datas deslocadas e fontes contrárias. Não foi aceita como pronta.
O ajuste preserva esses contratos e acrescenta controles de negação fora do
evento e de versões opostas presentes na mesma janela. A política documental
passa a `2026-10-22.1`; comparação continua `claim_source_review_v2`.

## Primeira rodada: separar resultado observado de medição válida

Vinte entradas públicas, uma tentativa cada, código congelado
`99300932f0f4e8ceb2fbf298262eaea970aad559cf54710d47a53ba17ae4fb94`.
Uma submissão pelo formulário, com relatório observado; 19 pela API local.
Todos os pedidos de análise retornaram HTTP 200/JSON/no-store. Isso não equivale
a vinte vereditos corretos nem a vinte testes pelo formulário.

| Conjunto | Respostas corretas | Inconclusivos | Conclusões erradas | Interpretação |
| --- | --- | --- | --- | --- |
| 12 controles conhecidos | 7 | 5 | 0 | **Não é medida válida da aplicação:** instrumento interferiu em três casos |
| Oito casos novos, preparados antes da implementação | 1/8 — 12,5% | 7/8 — 87,5% | 0 | Amostra pareada pequena, não representativa; abaixo da meta |

### Incidente no registrador de testes

O observador `validation_ui_server.capture_search` não aceitava `language`.
Quando a aplicação pediu a consulta inglesa, um `TypeError` interrompeu a
recuperação de DART, OMS e Copernicus após a primeira onda. Não foi timeout da
API nem falha comprovada da aplicação em produção. Corrigido encaminhamento
transparente dos argumentos; dois controles exercitam a instalação real do
observador. Registros e consumo anteriores foram preservados, sem repetir só
os casos que falharam. Nova avaliação exige o conjunto completo de 12.

Os oito casos novos não acionaram essa opção inglesa e ficam registrados
separadamente, na versão inicial. Não se usa a amostra melhor para substituir
a pior, nem se divulga uma porcentagem combinada dos dois conjuntos.

### Serviços realmente chamados nessa rodada

- Gemini: 27 envios, 12 respostas HTTP 200 e 15 HTTP 503.
- OpenRouter: sete envios, sete HTTP 401; acesso não estava funcionando.
  Posteriormente o titular informou que a chave estava desabilitada, foi
  reativada e está no `.env` privado. Isso só será confirmado por nova resposta.
- Fact Check: 20 consultas HTTP 200. Resposta 200 pode conter zero checagens.
- Pesquisa: 91 respostas HTTP 200. Resultado de pesquisa é pista, não evidência.
- Leitura pública: 128 tentativas, incluindo redirecionamentos, recusas e
  interrupções; não são 128 fontes independentes ou completas.
- Hive e outros caminhos pagos de mídia: **zero** chamadas.

Não aumentar timeout para “resolver” credencial rejeitada. Conferir chave ativa
e reiniciar apenas o backend de teste para recarregar configuração. Não copiar
chaves para frontend, documentação, logs ou chat. O código mantém OpenRouter
gratuito/preço máximo zero.

## O principal limite revelado pelos casos novos

Oito frases pareadas, quatro temas: premiação científica, naufrágio, Jogos
Olímpicos e abertura do Muro de Berlim. Rótulos/referências ficaram fora do
servidor e só foram abertos depois das vinte respostas. Arquivos públicos
preservados sem alteração de hash:

- [Entradas](../backend/tests/fixtures/validation/text-holdout-2026-10-22.inputs.json).
- [Rótulos e fontes de referência](../backend/tests/fixtures/validation/text-holdout-2026-10-22.labels.json).

São quatro pares escolhidos por julgamento, não avaliação estatisticamente
representativa ou garantia de precisão em notícias gerais. Agora publicados,
devem ser tratados como controles conhecidos em futuras melhorias.

Diagnóstico dos oito pedidos: 80 tentativas de leitura; 51 concluídas, 29 falhas.
Foram 47 corpos não vazios e quatro respostas HTML vazias do BCB. Não houve
truncamento ou timeout de fetch nessa amostra. Em sete casos, a comparação nem
iniciou por não haver duas famílias elegíveis — apesar de haver páginas lidas.

Três problemas estruturais permanecem prioritários:

1. **Correspondência ainda estreita:** nome, data, categoria e local podem estar
   distribuídos em enumerações ou sentenças consecutivas. Tradução, pronomes e
   múltiplos prêmios/datas precisam de vínculos de campos, não soma de palavras.
2. **Refutação de datas tem escopo limitado:** nascimento/morte e construções
   tipadas já delimitadas não se generalizam a qualquer prêmio, naufrágio ou
   abertura. Outra data de um evento repetível não refuta automaticamente a
   data alegada. Ampliar relações exige prova de identidade/unicidade, não uma
   lista de respostas históricas ou permissão para o modelo decidir de memória.
3. **Descoberta desperdiça slots:** filtros primários genéricos podem procurar
   instituições sem relação com o assunto. Ranking precisa considerar
   pertinência, corpo legível e diversidade editorial antes de consumir as
   leituras; páginas legadas em tabelas precisam de extração estrutural segura.

Alguns trechos pareciam elegíveis apenas porque continham negação de outro
evento. Isso foi identificado como risco, não ganho de cobertura; corrigir pode
reduzir elegibilidade aparente sem piorar a correção factual.

## Nova rodada conhecida após as correções — concluída

[Dados sanitizados desta execução](validation-wait-recheck-2026-10-22.json).
Código congelado `6662dabdf2d933ea37fc0b37722a7bd61c1c346ca011d0aa4adcc99639276d33`,
instrumento corrigido, uma tentativa por entrada e os mesmos 12 controles completos.
Limites: Gemini 30, Fact Check 20, pesquisa 70, leitura pública 140, OpenRouter
até duas novas tentativas. Os 38 envios conservadores anteriores do OpenRouter
continuam registrados; não há reposição do teto ao mudar o dia UTC. HTTP 401
interrompe novas tentativas OpenRouter; recusas de uma página pública não são
confundidas com credencial global desse serviço. Mídia paga permanece desligada.

**4/12 corretos (33,3%), oito inconclusivos (66,7%), zero conclusões erradas
observadas e zero erros terminais de análise. Meta de 80% não atingida.**
É pior que os 8/12 de 21/10; esse resultado não foi ocultado nem substituído
pela melhor rodada. Páginas, respostas dos fornecedores e tetos declarados
variam entre execuções: não isolam o efeito causal de cada alteração do código.

Uma submissão pelo formulário, com relatório inconclusivo observado; onze pela
API local. Doze respostas HTTP 200/JSON/no-store. Mediana do pipeline 27,12 s,
mínimo 12,13 s, máximo 93,13 s. Não é latência de produção.

| Controle | Resultado | Lacuna quando inconclusivo |
| --- | --- | --- |
| Data correta da morte de Elizabeth II | Inconclusivo | Uma família elegível após dez tentativas |
| Data falsa da morte de Elizabeth II | Inconclusivo | Comparação expirou; Gemini indisponível e OpenRouter sem resposta no prazo |
| Impacto intencional DART | Inconclusivo | Zero famílias elegíveis após dez tentativas, mesmo com pesquisa planejada com sucesso |
| Declaração de pandemia pela OMS | Inconclusivo | Uma família elegível; planejamento também limitado |
| Crescimento do PIB informado pelo IBGE | Verdadeira nas fontes — correto | — |
| Redução falsa da Selic | Falsa nas fontes — correto | — |
| Anomalia negativa falsa de temperatura | Falsa nas fontes — correto | — |
| Negação do texto da Lei Áurea | Inconclusivo | Comparação indisponível/limite de fallback |
| Lançamento James Webb | Inconclusivo | Duas famílias elegíveis, mas comparação indisponível/limite de fallback |
| Data de promulgação da Constituição | Inconclusivo | Uma família elegível após dez tentativas |
| Brasil campeão da Copa de 2014 | Falsa nas fontes — correto | — |
| Ano falso do lançamento Artemis I | Inconclusivo | Uma família elegível após dez tentativas |

Transporte real: Gemini 16 envios (seis HTTP 200, nove HTTP 503, um incompleto);
OpenRouter dois (um HTTP 200, um incompleto); Fact Check 12 HTTP 200; pesquisa
56 HTTP 200; leitura pública 82 tentativas, 69 HTTP 200. Sem HTTP 429 registrado
nos transportes desta rodada. `rate_limited` na cobertura pode refletir limite
local/QA, não quota externa efetivamente retornada pelo fornecedor.

**OpenRouter revalidado:** a pesquisa de DART recebeu resposta válida do modelo
gratuito `dots-studio/dots-3-note-preview:free`. A outra tentativa expirou na
comparação. A reativação da chave resolveu o bloqueio observado anteriormente,
mas não garante resposta de todos os modelos/pedidos. Após duas tentativas,
o teto conservador do teste bloqueou novas chamadas; não é uma recomendação
de configurar produção com duas chamadas nem prova de quota externa esgotada.

### Depois da medição

Reforço adicional exige um único predicado de caminhada na exceção delimitada.
“Pisou na Lua, mas não pisou em outro lugar” não pode virar negação da caminhada
na Lua. Regressão offline adicionada; nenhuma nova chamada remota ou taxa de
acerto atribuída a esse reforço. A impressão digital medida acima permanece
registrada, distinta do código após esse ajuste.

Validação antes da medição: 1.263 testes backend, 22 arquivos de teste frontend
e build passaram. **Após o reforço: 1.264 testes backend passaram**, zero skips
e zero HTTP real na suíte offline. Fonte final: `591890cdba158e6f0dfe47938fa434b8964344e8878d0a3483a7d13d6b13349d`.
O frontend não mudou entre esses checkpoints. Nenhuma nova precisão remota foi
atribuída ao ajuste posterior.

## Limites e publicação

Testes offline verificam funcionamento e segurança, não precisão no mundo real.
Imagem, voz e vídeo não receberam nova homologação remota nesta etapa. Ausência
de sinal não comprova origem humana; OCR/transcrição não certificam fidelidade.
Nova taxa de 80% ainda precisa ser demonstrada em amostra mais ampla, separada
das usadas para corrigir o código, com erros e inconclusivos no denominador.

Sem recarga, contratação, alteração de produção, push ou deploy nesta etapa.
Commit local e revisão testada não significam que Vercel/Railway já os executam.
