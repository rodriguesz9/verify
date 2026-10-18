# Recuperação contextual e vínculos de evento — 18/10/2026

## Situação desta revisão

Melhorias locais posteriores a `c3e6865`, com política `2026-10-18.1`. Não há nova medição de precisão com APIs reais nesta etapa. A última rodada completa continua sendo **5/12 textos corretos (41,7%) e 7/12 inconclusivos (58,3%)**, preservada no [registro de 17–18/10](QUALIDADE-CHECAGEM-2026-10-17.md). Meta de 80% ainda não comprovada.

O objetivo é recuperar evidências utilizáveis e compará-las corretamente, não diminuir abstenções aceitando títulos, legendas, memória dos modelos ou confirmações parciais. Nenhum novo serviço, dependência, chave ou gasto pago foi adicionado. Gemini/OpenRouter continuam nos papéis já existentes; não foram revalidados com chamadas reais nesta etapa. O saldo Hive autorizado anteriormente está esgotado para novos testes.

## O que mudou

### Corpo do artigo separado da autoria

Contêineres HTML aninhados podiam juntar autoria/data/local ao primeiro parágrafo. O leitor agora preserva suas fronteiras, mesmo sem um `p` intermediário. No HTML EBC capturado, autoria e publicação de 2015 permanecem como contexto; o parágrafo sobre a promulgação em 1988 fica separado como corpo literal. Não apagamos a data de 2015 nem corrigimos silenciosamente a CNN que trazia 1888 no corpo.

Títulos, legendas, citação de boato, simulação e instruções continuam incapazes de fornecer prova factual. Testes incluem estrutura DOM equivalente com outras datas, autores e eventos; não existe regra específica para uma URL ou ano.

### Lançamento, missão e data

Novo comparador puro reconhece construções delimitadas de lançamento concluído: identidade explícita da missão/voo, programa, identificador numérico/romano e data completa ligada ao lançamento. Normaliza apenas equivalências declaradas de grafia/identificador; não consulta uma tabela de eventos conhecidos.

- Data diferente só refuta quando o trecho identifica o mesmo lançamento de missão, sem perder qualificadores de tripulação, sucesso, lugar ou horário alegados.
- Datas de anúncio, planejamento, retorno, tentativa e modelo de foguete reutilizável não são intercambiáveis.
- Formas nominais diretas e descrições históricas já suportadas permanecem cobertas. Descrições por veículo/carga admitem apenas apoio com a mesma data; não demonstram unicidade para refutar outra data.
- Afirmações com qualificadores não reconhecidos ficam dentro do escopo de revisão, sem escapar pela comparação lexical genérica.
- Uma janela de até três sentenças consecutivas de corpo pode recompor uma data separada por `a.m.`. Não cruza títulos ou legendas.

### Resultado de competição

Novo comparador vincula competição, edição, categoria e vencedor do título. O vencedor não pode ser inferido apenas de placar, lista de finalistas ou menção a uma final.

A categoria convencional de “Copa do Mundo” em português é futebol masculino principal de seleções; menção explícita a outra modalidade/categoria veta essa leitura. Inglês genérico “World Cup” exige identificação adicional. Não há tabela de campeões por ano. Categorias não reconhecidas abstêm, não são convertidas à categoria padrão.

O contexto só pode vetar uma interpretação; não fornece vencedor ou ano ausente no próprio trecho. Em uma construção de duas sentenças, a afirmação de título precisa vir imediatamente após a final da edição identificada. Outra edição, torneio ou ator interposto não pode herdar o ano anterior. O caso CNN capturado exige a janela que contém final e título, não sua introdução isolada.

### Descoberta de referências editoriais

Chamadas editoriais explícitas em contêineres de destaque — por exemplo, “Read the Story” e “Leia a reportagem” — agora podem fornecer uma URL real para leitura. É necessário um único título local anterior e um único link associado. Anúncios, navegação, conteúdo oculto, legendas e cartões de links ambíguos são excluídos.

O título serve **apenas como pista de recuperação**, nunca como prova ou substituto do corpo. A identidade deve estar no título, não somente no endereço. Referências com identidade literal no título são priorizadas sobre âncoras genéricas cujo caminho apenas menciona o tema. Preservados os limites de 200 âncoras/12 referências por página, duas pistas prioritárias e orçamento cumulativo de leitura; falhas consomem tentativa. Validação HTTPS, famílias curadas e proteção SSRF permanecem.

No HTML NASA/Webb já capturado, isso recupera uma chamada para uma matéria de lançamento antes ignorada por estar fora de parágrafo. **A matéria vinculada não foi consultada nesta revisão.** O pipeline ainda procura essas referências após a primeira onda; se a página só chega depois, a pista não ganha uma rodada extra automática.

### Seleção assistida e explicação

O pedido à IA agora explicita que introdução/contexto não comprova o predicado; ela deve escolher o ID da passagem que contém a evidência. A IA não cria citações ou URLs e não recebe autorização para substituir as regras do servidor. O relatório identifica o alcance do vínculo de lançamento ou título esportivo e mantém as citações literais.

Traduções explícitas `telescope`/`space` foram adicionadas, sem trocar identidade, data ou evento. Isso **não resolveu sozinho** o controle Webb: o corpo NASA usa “Webb” com data e nome completo sem data, separados por outra passagem/título; o trecho completo com data é legenda. A seleção corretamente não usa essa legenda como prova textual.

## Segurança e regressões

A revisão independente encontrou e fechou riscos durante a implementação:

- Emprestar o ano de uma final ao título da edição seguinte.
- Atribuir um título ao primeiro time citado quando outro ator aparece antes da conquista.
- Ignorar “É falso que”/“Ao contrário” após aceitar um vínculo tipado.
- Aceitar como concluída uma edição futura em inglês porque o parser genérico tratava o ano como número, não data.
- Perder qualificadores de tripulação, primeiro lançamento ou tentativa fracassada ao cair no comparador genérico.
- Rejeitar duas formas legítimas de lançamento já cobertas pelos testes antigos; ambas foram preservadas sem alterar seus testes.

Continuam obrigatórios origem literal, corpo recuperado, ausência de ambiguidade e duas famílias elegíveis para o caminho genérico. As exceções anteriores de registro institucional original continuam delimitadas e não foram ampliadas por estes comparadores. Sucesso HTTP não é confirmação factual.

## Evidências e limites dos testes

Fechamento: **957 testes backend, zero falhas/skips, 15,566 s**, em Docker sem rede e SQLite descartável; **22 arquivos de teste frontend, zero falhas/skips, e build passaram**. São 85 novos métodos backend sobre a base de 872, não 957 amostras de notícias. PostgreSQL, produção, disponibilidade das APIs e novas mídias não foram revalidados.

Índice congelado do código da aplicação: `d1e1632adc73fbb5f18b5193d8738f3bd52182b88153b9244ec5e794ba651af8`, inalterado durante os dois replays finais. Abrange Python do backend e JS/JSX/CSS do frontend, não congela bibliotecas, ferramentas ou provedores externos.

[Resumo sanitizado desta revisão](validation-recovery-2026-10-18.json) registra identificação do código, suíte e replay de seleção. O replay usa os mesmos conjuntos de URLs/HTML públicos capturados anteriormente: não faz novas buscas, chamadas a modelos ou leituras externas. Seus números são de **elegibilidade de comparação**, não de novos vereditos corretos. Rótulos esperados não são usados para selecionar fontes.

O replay separado dos cinco resultados conclusivos anteriores remapeia somente as citações já aceitas. É teste de regressão, não nova medição de precisão. Não somar com a rodada real nem extrapolar ao conteúdo que continuava inconclusivo.

Resultado desse replay: **cinco status e nove citações literais preservados**, zero transporte externo. No replay de seleção das mesmas URLs, Constituição passa de uma para duas famílias elegíveis após reprocessar o HTML; Artemis passa de zero para uma, ainda insuficiente. Copa passa de três candidatos genéricos para uma família com vínculo literal de título, excluindo introduções sem prova. Webb, DART, PIB e Copom continuam sem cobertura capturada suficiente. Esses resultados não autorizam converter seis comparações elegíveis em seis acertos.

Testes de API executam rota real → pipeline → guardas/citações → explicação → persistência simulada → snapshot assinado. Recuperação e seleção de IDs do provedor são simuladas; não validam quota, disponibilidade ou comportamento atual dos fornecedores.

### Interface local

Dois controles funcionais com fontes/seleção simuladas chegaram a relatório: lançamento sintético corroborado e título esportivo contradito. A tela exibiu as citações e o motivo específico do vínculo. A limitação aberta informa explicitamente que o ensaio é offline, sem consulta às URLs de controle. Não são dois novos acertos de notícias reais.

Durante a preparação, o instrumento descartável teve dois defeitos próprios: usuário anônimo indevidamente aceito na rota de perfil e concatenação de um motivo nulo ao aviso de simulação. Ambos foram corrigidos no instrumento, sem atribuí-los às APIs nem omitir as tentativas falhas. Não integram o código de produção.

A solicitação de PDF mostrou “PDF preparado” e nenhum erro de console; o navegador não confirmou evento/arquivo baixado em 15 s. **Salvamento/abertura do PDF pela interface permanece pendente.** O teste automatizado valida o snapshot e seu conteúdo, não essa última fronteira do navegador. Não houve novo ensaio de mídias ou homologação visual responsiva completa.

## Próxima validação necessária

1. Repetir uma vez o manifesto textual inteiro com código congelado, APIs realmente disponíveis e inconclusivos/erros no denominador. Preservar os resultados, inclusive os piores, e comparar os mesmos casos separadamente de casos inéditos.
2. Testar descoberta da referência editorial antes de esgotar as dez tentativas. Não presumir que a página vinculada contém prova suficiente ou que retorna 200.
3. Melhorar recuperação de períodos do PIB e leitura de fontes do Copom/DART. Manter vínculo entre divulgação, período, direção, unidade e valor, sem inserir datas corretas conhecidas nas consultas.
4. Medir em corpus novo e independente. Os controles de desenvolvimento atuais não sustentam uma promessa geral de 80%.
5. Revalidar as modalidades de mídia separadamente quando houver autorização e materiais adequados. Não reenviar Hive com o teto consumido. Voz humana e vídeos de câmera autorizados continuam necessários.
6. Identificar a revisão, revisar os resultados e só então publicar conforme autorização. Commit local, push, deploy, configuração e funcionamento de APIs são estados distintos.

## Publicação e configuração

Nenhuma variável privada foi alterada e nenhuma variável nova é necessária para estas correções. Não houve push/deploy, acesso ao banco ou alteração de Railway/Vercel nesta rodada. O [guia de retomada](REATIVAR-RAILWAY-2026-10-13.md) continua aplicável, condicionado à revisão identificada e à validação correspondente. O instrumento descartável e seus tokens não devem ser copiados para produção ou para o repositório.
