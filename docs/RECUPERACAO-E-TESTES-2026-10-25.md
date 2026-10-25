# Recuperação de fontes e nova rodada — 25/10

Código da melhoria: `c6b8712`, após `d7ba408`. Não é publicação em produção.

## Dois mecanismos corrigidos

### Repetições não ocupam toda a leitura

Com oito tentativas já utilizadas, duas referências indicadas pela IA, ambas do mesmo grupo BBC já utilizável, ocupavam os dois espaços restantes; uma Reuters pertinente ficava sem leitura. O defeito foi reproduzido sem modelos ou rede.

A seleção agora considera formato, identidade/assunto e incompatibilidades explícitas de período antes da indicação da IA/citação. Dentro da mesma faixa de qualidade, cada família ainda não utilizável recebe uma oportunidade antes das repetições. Uma fonte sem pertinência não sobe na fila apenas por ser de outro grupo.

Preservados: página submetida primeiro, famílias reais após créditos/dependência editorial, leitura estática segura, falhas cobradas, teto cumulativo e nenhum reenvio/reembolso de tentativa. A ordem da fila não é evidência nem voto.

### Links de notícias já consultadas também podem ser lidos

O pipeline já buscava notícias em paralelo, mas seus links não eram reaproveitados pela recuperação dos documentos. Agora a recuperação pode aguardar essas mesmas tarefas e reutilizar somente URL HTTPS de fonte curada e título, com deduplicação e limites de três consultas/cinco resultados cada.

Resumos, datas, nomes de fontes e campos arbitrários da busca não fornecem prova. Cada URL ainda precisa de leitura real do corpo e passa pelos mesmos filtros de contexto, datas, números, citações e independência. O status original da busca web é preservado; uma notícia não apaga erro/quota nem autoriza nova busca.

Não há mais consultas Serper nem aumento de tentativas de página por causa desse reaproveitamento: continuam três/seis leituras sem pesquisa assistida e até dez com ela. O prazo de 145 s e o restante global continuam compartilhados. O pipeline mantém a propriedade das tarefas de notícias e as encerra em cancelamento; a recuperação não inicia trabalhos separados.

## Verificação local

- 1.515 testes backend passaram, sem rede, `.env` privado ou skips. São 22 novos controles nesta revisão.
- 205 testes frontend passaram; build compilou 1.977 módulos, com endereço de API relativo explícito para a rodada local.
- Novos controles exercitam repetição/citação/família dependente, URL submetida, leitura falhada sem reembolso, espera real das notícias, cancelamento, URL insegura, teto cumulativo e resumo sem valor de prova.
- Os critérios finais de verdade/falsidade não foram relaxados. Não houve implementação de uma nova gramática legal apenas para fazer ECA/LDB passarem.

## Protocolo da rodada real

Doze textos conhecidos, os mesmos da última medição de 6/12 (50%). Seis têm rótulo esperado verdadeiro, seis falso; rótulos e referências não são passados à aplicação. São controles de desenvolvimento já conhecidos, não teste cego nem estimativa de precisão geral.

Fonte congelada SHA-256 `383cf9b24cff299b297fa2712ca1a161e8a7190c02811dd6d5abe2e87c12f475`. Compilação frontend, código do instrumento, entradas e limites também foram congelados antes dos envios. Nenhum código de aplicação ou instrumento pode ser alterado durante a rodada.

Autorização humana: até 16 chamadas Gemini, 12 OpenRouter, 60 buscas Serper; Fact Check limitado a 12 e leitura pública a 120 envios, incluindo redirecionamentos. Sem Hive, mídia, modelos pagos, recarga ou contratação. OpenRouter exige `openrouter/free` e todos os preços máximos zero; Gemini usa o acesso gratuito informado pelo usuário e o modelo configurado `gemini-3.1-flash-lite`, sem rotação de chave/modelo.

A janela anterior de 48 reservas conservadoras OpenRouter permanece intacta e fixada por hashes. A autorização nova permite até 12 adicionais, no máximo 60 conservadoras cumulativas registradas. Nenhum reinício, falha ou mudança de data repõe os limites. Reservas são persistidas antes da rede; erros de autorização/quota impedem novo envio do fornecedor na janela.

Banco/auth descartáveis. Quatro nomes de credencial são selecionados antes do parse dotenv; não são importados banco, senha ou segredos de autenticação privados. Nada é impresso nos resultados. Corpo público e relatórios diagnósticos locais são limitados e sanitizados; capacidades PDF/revisão, cookies e respostas brutas de modelos não entram no relatório versionado.

Planejado: uma submissão pela interface e onze por HTTP comum, em ordem fixada com seed 20261024. Cada texto recebe uma única tentativa; um controle já concluído na interface é preservado, não reenviado pelo runner HTTP. Inconclusivos e erros ficam no denominador da avaliação planejada, com contagens separadas. Resultados HTTP não são apresentados como testes visuais.

## Resultado

[Doze resultados e contadores sanitizados](validation-recovery-2026-10-25.json). Todos terminaram: uma submissão pelo formulário, com relatório observado, e onze por HTTP comum. O registrador confirmou 12 POST/200; HTTP bem-sucedido não equivale a conclusão factual correta. Nenhuma tentativa foi refeita.

**5/12 corretos (41,7%), sete inconclusivos e nenhuma conclusão errada observada.** A última rodada dos mesmos doze havia dado 6/12 (50%). Portanto esta revisão não demonstrou aumento de precisão nem atingiu 80%; os 75% históricos também não são a taxa atual.

| Controle conhecido | Resultado desta rodada |
| --- | --- |
| OMS, classificação da pandemia | Verdadeira nas fontes, correto |
| Brasil campeão da Copa de 2014 | Inconclusivo |
| Copernicus, temperatura abaixo da referência | Inconclusivo |
| Copom, redução da Selic alegada | Falsa nas fontes, correto |
| Lei Áurea, negação do artigo 1º | Falsa nas fontes, correto |
| Webb, data do lançamento | Inconclusivo |
| Artemis I, ano do lançamento | Inconclusivo |
| Elizabeth II, data verdadeira | Inconclusivo |
| PIB, divulgação do IBGE | Verdadeira nas fontes, correto |
| Elizabeth II, data falsa | Falsa nas fontes, correto |
| DART, impacto intencional | Inconclusivo |
| Constituição, promulgação | Inconclusivo |

Entre os seis rótulos verdadeiros, 2/6 receberam apoio correto (33,3%); entre os seis falsos, 3/6 receberam refutação correta (50%). Não retirar os sete inconclusivos para apresentar “100% dos conclusivos” como se fosse acerto geral.

OMS e PIB ganharam conclusões corretas; Copa, Copernicus e Constituição perderam conclusões em relação à rodada de 50%. Os sete restantes não mudaram. Busca pública e respostas dos modelos variaram; a mudança de código não foi isolada num teste A/B com resultados de busca idênticos.

### Causas observadas

- Seis dos sete inconclusivos pararam antes da comparação: Copa/Artemis/Elizabeth/Webb tinham uma família elegível; Copernicus/DART, zero. As fontes corretas/independentes ou os vínculos explícitos necessários não chegaram à comparação. Texto lido sem vínculo suficiente não vira prova.
- Constituição reuniu duas famílias elegíveis, mas Gemini respondeu 503 duas vezes, incluindo a única recuperação permitida. OpenRouter respondeu HTTP 200, porém seu resultado foi considerado `invalid_response`. Não foi aceito como veredito. O diagnóstico disponível não permite afirmar se a resposta foi truncada, malformada ou falhou em outro requisito do cliente.
- O limite autorizado de **60 buscas** foi atingido durante a pesquisa adicional da Constituição. Uma operação foi bloqueada localmente, sem envio. Isso interferiu no alcance da recuperação, mas não explica sozinho o inconclusivo: já havia duas famílias e a comparação também falhou. O teto da rodada foi menor que o pior caso de 12 buscas de notícias mais até 60 buscas web. Essa limitação de planejamento do teste é registrada, não atribuída à IA nem removida do denominador.
- O reaproveitamento de notícias encontrou um candidato no caso Webb, mas não completou a cobertura. A reprodução sintética comprovou a correção do mecanismo; a rodada não demonstrou ganho factual por ele.

Mediana da análise: 24,169 s; percentil 95 por posto mais próximo: 55,248 s. Nenhum caso chegou perto dos 420 s globais. Mais espera não corrigirá por si só esses seis bloqueios anteriores aos modelos.

### Consumo e disponibilidade

Usadas 149 reservas: Fact Check 12, Serper 60, leituras públicas 63, Gemini 13 e OpenRouter 1. Todos os tetos preservados, inclusive falhas. A reserva conservadora cumulativa OpenRouter passou de 48 para **49**, não para 60; o restante não autoriza textos extras fora destes doze.

- Fact Check: 12 respostas 200. Ausência de uma checagem correspondente não comprova falsidade.
- Serper: 60 respostas 200; o teto local bloqueou a consulta adicional. Não se observou quota remota 429 nesta rodada.
- Gemini: 11 respostas 200 e duas 503. A recuperação transitória foi exercitada, mas não recuperou o serviço naquela comparação.
- OpenRouter: uma resposta 200, resultado inválido para uso. Rota gratuita respondeu; comparação remota não homologada.
- Leituras públicas: 51 respostas 200, quatro 403, três 401, uma 404, três redirecionamentos e um transporte incompleto. `blocked_or_unavailable` também pode representar bloqueio anterior ao envio pelo controle de segurança do instrumento; não significa que todas essas tentativas receberam erro do site remoto.

Nenhuma chamada de mídia ou detector pago, recarga, contratação ou rotação de chave/modelo. A aplicação e o instrumento permaneceram congelados até os doze registros terminais. O servidor descartável foi encerrado normalmente; registros persistentes foram consolidados offline.

## Limites e próximas lacunas

Mais tempo e mais candidatos não garantem prova utilizável. A gramática atual de leitura legal não reconhece genericamente atribuições por nome da norma + artigo + “considera-se”/“prevê”; aumentar espera não corrige isso. Uma evolução segura precisará vincular nome literal na ementa visível do corpo ao artigo exato, preservando condições, exceções, vigência e contexto. Título/URL não podem fornecer o conteúdo legal ausente.

Próximos trabalhos: recuperar páginas independentes realmente legíveis do período pertinente; investigar falsas rejeições semânticas com exemplos adversariais; melhorar o diagnóstico estruturado de resposta inválida OpenRouter e planejar o orçamento da avaliação contra o pior caso de consultas. Nenhuma dessas pendências é resolvida com concordância livre entre modelos ou reenvio até conseguir uma conclusão.

Imagens, áudios e vídeos não fazem parte desta rodada autorizada. Nenhum resultado textual homologa seus detectores, nem autoriza anunciar 80% gerais, precisão de mídia ou funcionamento em produção.
