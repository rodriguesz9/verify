# Reduzir inconclusivos sem aumentar conclusões erradas

**Correção local após a queda, 24/10:** [causas e recuperação limitada](CAUSA-QUEDA-E-RECUPERACAO-2026-10-24.md), [auditoria comparativa](diagnostic-decline-2026-10-24.json). Quatro acertos perdidos e um ganho explicam 75%→50% nos mesmos doze; os 30% incluem oito novos inconclusivos. Pesquisa prioriza formatos legíveis e a comparação pode recuperar um Gemini 503 dentro do mesmo prazo/quota, sem repetir julgamentos. 1.469 testes backend, 22 arquivos frontend e build passaram. Sem nova chamada remota ou nova porcentagem; última medição permanece 50%/0% nos grupos 12/8, sem homologar 80% ou deploy.

**Última rodada, segunda revisão de 24/10:** [pesquisa e diagnóstico](PESQUISA-LACUNAS-2026-10-24.md), [vinte resultados sanitizados](validation-research-gaps-2026-10-24.json). **Conhecidos: 6/12 corretos (50%), seis inconclusivos; novos: 0/8 corretos, oito inconclusivos.** Nenhuma conclusão errada observada, nenhum erro HTTP; piora em relação aos 75% anteriores preservada. Quatro submissões pela interface e dezesseis HTTP; mídia não revalidada. 1.448 testes backend e 22 arquivos frontend/build passaram. Treze inconclusivos antes da comparação, um por falhas remotas; não há ganho de precisão ou 80% demonstrado. Os oito novos agora são controles conhecidos; versões anteriores abaixo são históricas.

**Atualização de 24/10:** [correções e limites](VINCULOS-E-REVISAO-2026-10-24.md), [resultados sanitizados](validation-bindings-2026-10-24.json). **9/12 corretos (75%), três inconclusivos, zero conclusões erradas observadas**, contra 6/12 na rodada anterior. Uma submissão visual e onze HTTP; mídia não revalidada. 1.430 testes backend e 22 arquivos de testes frontend passaram, com build concluído. Recuperação/leitura ainda bloqueia DART, Copa e Artemis; 80% gerais não demonstrados. Registros anteriores abaixo são históricos, não o estado mais recente.

Última medição de 23/10: [6/12 corretos (50%)](RESILIENCIA-RECUPERACAO-MIDIA-2026-10-23.md), seis inconclusivos. Modelos responderam; insuficiência de famílias impediu comparação nesses seis. Raiz WHO/Europe corrigida posteriormente, sem apagar contexto; vínculo de evento/data ainda insuficiente. Quatro mídias revalidadas na UI com cota própria, sem homologar precisão geral. OpenRouter respondeu, mas omitiu um dos dois pares de fonte no diagnóstico separado. Recuperação EBC/Webb, corpos completos DART/OMS e matriz completa dos modelos são prioridades. Meta 80% não alcançada; registros seguintes são históricos.

Atualização de 23/10: [implementação central e resultado](CAUSA-CENTRAL-2026-10-22.md). A rodada completa mais recente foi **7/12 corretos (58,3%), cinco inconclusivos**, não 80%. Equivalências delimitadas de relatos de competição e lançamento foram implementadas depois, com testes offline. Próximas prioridades são falha dos modelos com duas fontes já prontas, leitura completa de intenção/data do DART, recuperação acessível da OMS e avaliação independente da versão final, incluindo mídias. Não corrigir esses casos apagando qualificadores, promovendo legenda a prova ou reduzindo o denominador. Toda alteração posterior exige nova avaliação separada. O estado inicial abaixo é histórico.

Implementação e medição desta etapa: [recuperação, espera e diagnóstico](RECUPERACAO-ESPERA-2026-10-22.md).
O estado inicial descrito abaixo é histórico. A primeira execução de 12 teve
interferência do registrador e não vale como precisão; os oito casos novos
obtiveram 1/8 naquela versão. Nova rodada conhecida, com o instrumento corrigido,
é registrada separadamente. Não há precisão geral de 80% demonstrada.

Estado inicial desta etapa: revisão local, sem publicação. A última medição real
concluída continua sendo **8/12 corretos (66,7%), quatro inconclusivos, zero
conclusões erradas**, no conjunto de desenvolvimento conhecido. Os testes
automatizados não são uma nova medida de precisão. A meta de 80% ainda não foi
demonstrada. Resultados desta revisão serão registrados separadamente após
congelar o código.

## Diagnóstico: onde a evidência se perde

Uma chave configurada não garante uma resposta utilizável. O caminho completo é:
afirmação original → pesquisa → página acessível → corpo correto → trecho que
cubra todos os detalhes → fontes independentes → comparação → relatório.
Falhar em qualquer parte pode impedir uma conclusão, mesmo com Gemini e
OpenRouter disponíveis. Concordância entre modelos, sozinha, não é evidência.

Nos quatro inconclusivos da rodada anterior, a recuperação esgotou as dez
tentativas de página; não foram quatro timeouts. Foram recuperados corpos de
páginas, mas faltaram trechos admissíveis de duas famílias independentes:

| Controle conhecido | Lacuna observada | Ação desta revisão |
| --- | --- | --- |
| DART | Data completa e intenção da missão não aparecem juntas em vários corpos recuperados | Consulta editorial em inglês no lugar de uma consulta existente; orientar a busca pelo detalhe rejeitado |
| PIB | Legenda de vídeo unida à notícia acionava rejeição por incerteza | Correção estreita de legenda já feita em `473f1dd`; medir novamente, sem contar replay como novo acerto |
| Copa do Mundo | Relato completo em espanhol não era reconhecido; referência técnica adjacente contaminava contexto | Gramática fechada em espanhol, barreiras de ficção/categoria e remoção estritamente estrutural de referência legada |
| Artemis | Leitor escolhia uma atualização antiga de página ao vivo e perdia outras | Recuperar o fluxo explicitamente identificado, mantendo relógios como contexto e sem unir atualizações |

Mesmo após corrigir a leitura, uma notícia que só diz “segunda-feira” ou “dia
16” não fornece automaticamente ano/mês do evento. Data de publicação, título e
endereço da página não devem preencher silenciosamente detalhes ausentes.

## Prioridades e critérios de aceite

### 1. Recuperação e leitura — implementar primeiro

- Usar inglês apenas para temas internacionais explicitamente reconhecidos,
  preservando a afirmação enviada e os limites existentes de pesquisa.
- Enviar ao planejador motivos fixos de rejeição dos trechos, para buscar o
  detalhe faltante. Esses motivos não são votos nem uma revisão exaustiva.
- Ler todas as atualizações de um fluxo ao vivo explicitamente identificado,
  mantendo barreiras entre entradas, contexto visível e limite de tamanho.
- Remover referência técnica legada somente quando o parágrafo inteiro for uma
  estrutura de “leia também” reconhecida. Prosa, negação e citações permanecem.

Aceite: nenhuma ampliação automática de quotas; sem inventar texto; casos
adversariais não perdem qualificadores; artigos comuns mantêm o comportamento.

### 2. Comparação factual — ampliar compreensão, não relaxar prova

- Reconhecer uma forma completa de relato esportivo em espanhol, com país-sede,
  edição e campeão em campos distintos. Não cadastrar tabela de campeões.
- Bloquear contexto de ficção, hipótese, previsão, atribuição, instrução e
  categoria esportiva incompatível, inclusive quando a frase isolada é positiva.
- Manter citações literais, procedência, data válida, famílias editoriais,
  cobertura por afirmação e rejeição de versões contraditórias.

Aceite: exemplos inventados de teste não recebem voto factual quando estão
marcados como ficção; categoria de veteranos não vira seleção principal; título
ou resumo de pesquisa não substitui corpo de notícia.

### 3. Avaliação congelada — medir antes de ajustar novamente

1. Encerrar alterações da aplicação e gravar impressão digital dos arquivos.
2. Executar os 12 controles conhecidos e oito entradas novas preparadas antes
   desta implementação, uma tentativa por entrada.
3. Não disponibilizar rótulos esperados à aplicação. Rótulos novos ficam fora
   do servidor e só são consultados depois de todas as respostas.
4. Registrar correto, errado, inconclusivo e erro em cada conjunto. Todos entram
   no denominador. Informar quantidade de conclusões e tempo de resposta.
5. Separar formulário observado de pedidos HTTP. Não chamar toda a rodada de
   “testes pela interface” se parte foi executada diretamente pela API local.
6. Sem alterações de código durante a rodada; eventual correção posterior tem
   outra versão e não herda os números da versão medida.

Limites desta rodada: somente serviços gratuitos/créditos autorizados; Hive e
outros caminhos pagos desativados. Orçamento máximo reservado: Gemini 60,
OpenRouter nove novas chamadas (31 já registradas como histórico conservador),
Fact Check 40, pesquisa 110, leitura pública 240. São tetos, não metas de uso.
HTTP 402/429 interrompe novas chamadas ao fornecedor na rodada; sem troca de
chave para contornar quota, recarga ou contratação. Os limites menores internos
por análise continuam válidos.

Aceite: suíte offline sem acesso externo e sem testes ignorados; frontend
testado e compilando; métricas reproduzíveis por versão. Oito casos novos são
uma amostra pequena, não certificam 80% para qualquer notícia.

### 4. Próxima rodada, condicionada ao diagnóstico medido

- Se faltar leitura: corrigir o extrator do formato concreto, com regressão de
  visibilidade, contexto e limite; não remover contexto para fabricar conclusão.
- Se faltar correspondência: ampliar somente construções completas e testadas,
  preservando números, negações, datas e identidade do evento.
- Se faltar fonte independente: melhorar descoberta neutra e referências
  editoriais. Duas páginas do mesmo grupo não contam como duas provas.
- Se o modelo falhar: registrar timeout, quota, saída inválida e indisponibilidade
  separadamente. Aumentar prazo só quando o registro mostrar resposta tardia
  recuperável; não resolve página sem o detalhe necessário.
- Se houver conclusão errada: tratar como bloqueante antes de perseguir maior
  cobertura. Não escolher somente exemplos fáceis para divulgar precisão.

## Mídia e publicação: pendências separadas

Após a avaliação inicial foram implementados espera delimitada do Gemini,
escopo da negação e leitura direta de WAV normalizado, com regressões offline.
A simples presença de mais APIs não resolve a correspondência ainda estreita
de evento, data, categoria e local. Próximo ciclo deve priorizar vínculos desses
campos e corpus novo, em vez de mais chamadas ou de reduzir a exigência de prova.

Esta rodada textual não revalida imagem, voz ou vídeo. Ausência de sinal de IA
não prova mídia autêntica; um detector pode indicar geração sem provar que a
legenda ou a notícia é falsa. OCR lê texto na imagem; transcrição lê fala. Ambos
precisam de conferência antes de usar o conteúdo reconhecido como afirmação.

Para uma medida de mídia defensável ainda é necessário corpus autorizado com
origem conhecida, diversidade de resolução/compressão/idioma e rótulos por
dimensão (geração, alteração facial, fala, veracidade da mensagem). Medir cada
modalidade separadamente, com inconclusivos e falsos positivos explícitos.

O limite pago Hive anterior já foi consumido. Não reaproveitar autorizações
antigas. Sem nova autorização, repetir apenas controles offline/gratuitos.

Antes de publicar: revisar migrações em PostgreSQL descartável, configuração e
limites do ambiente Railway, origens/cookies, variáveis e disponibilidade real
dos fornecedores; validar a revisão exata no ambiente de destino. Commit local
não é push; push não prova deploy. Esta etapa não autoriza nova publicação.
