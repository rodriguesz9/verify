# Vereditos, inconclusivos e responsividade — 17/10/2026

## Situação da entrega

Revisão local sobre `70394f7`, na branch `entrega/banca-2026-10-08`. Não é confirmação de publicação na Vercel ou no Railway. O checkout original com alterações do usuário foi preservado; as correções e os testes ocorreram na cópia revisada.

A interface foi corrigida e o cruzamento de documentos recebeu melhorias reais. **A checagem factual ainda não está homologada para uso geral.** A ausência de erros conclusivos observados neste conjunto pequeno não demonstra precisão de 100%. Há controles conhecidos que continuam sem conclusão.

Os registros de [16/10](CORRECAO-CHECAGEM-2026-10-16.md), [interface anterior](VALIDACAO-INTERFACE-2026-10-16.md) e [APIs de 14/10](VALIDACAO-APIS-2026-10-14.md) permanecem históricos. Não substituir resultados antigos por uma tentativa posterior mais favorável.

## Por que Gemini e OpenRouter não garantiam conclusões

O caminho é: entrada literal → busca → leitura segura das páginas → seleção de trechos correspondentes → comparação assistida por modelo → validação das evidências → relatório.

Várias falhas estavam **antes da comparação**: páginas sobre outro ano, fonte bloqueando a leitura, data só no cabeçalho, evento e data distribuídos em sentenças separadas ou nenhum trecho completo elegível. Nesses casos, o modelo de comparação nem era chamado. Ter duas chaves não recupera automaticamente um documento ausente.

Os serviços exercem funções diferentes:

| Serviço | Função no caminho textual | O que não comprova |
| --- | --- | --- |
| OpenRouter gratuito | Extração auxiliar de pistas de busca; alternativa à comparação quando o provedor principal falha | Concordância entre modelos não é evidência independente |
| Gemini | Comparação estruturada de trechos dos documentos recuperados | Memória do modelo não é prova documental |
| Google Fact Check | Localizar checagens já publicadas | Zero resultados não significa falsidade |
| Busca de referências | Localizar documentos e pistas de origem | Títulos e resumos não recebem voto de verdade |
| Leitor público | Recuperar o corpo com limites e proteção contra acesso a redes privadas | Não executa o JavaScript da página nem contorna bloqueios |

A rodada registrou comparação real por Gemini e, em uma falha HTTP 503 anterior, comparação alternativa real por OpenRouter. Isso valida esses caminhos de integração, **não** todos os modelos, mídias ou conteúdos possíveis. Não houve comparação controlada com a versão inicial que usava apenas Gemini: uma resposta mais confiante daquela versão não demonstra maior acerto.

## Correções implementadas

### Recuperação e leitura

- Pesquisa literal original preservada; recuperação neutra não troca a afirmação que será julgada.
- Data de divulgação separada do período descrito. Uma divulgação em 2025 sobre o PIB de 2024 não deve priorizar somente notícias sobre o PIB de 2025.
- Consultas brasileiras ao IBGE/Copom mantêm vocabulário em português; referências internacionais podem usar a ponte lexical explícita já cadastrada.
- Leads ainda não lidos ordenados por período e assunto; trimestre/semestre não solicitado perde prioridade. Isso ordena leitura, nunca decide verdade.
- Recuperação de até duas referências primárias efetivamente citadas em parágrafos visíveis de documentos curados já lidos. Sem URLs inventadas, navegação recursiva ou votos por links.
- Permanecem até três buscas de recuperação, seis tentativas cumulativas de página e 45 segundos. Falhas também gastam o limite; não são repetidas ou reembolsadas silenciosamente. Até três documentos são selecionados para comparar.
- Referências citadas continuam passando pelo leitor com validação DNS/IP, TLS, redirecionamentos, tamanho e prazo. Não foram removidas proteções para reduzir inconclusivos.

### Correspondência e comparação

- Janelas de até três sentenças consecutivas do corpo permitem ler uma afirmação distribuída entre frases. Não atravessam cabeçalhos, legendas, autoria ou outras fronteiras de contexto.
- Pronomes de morte/nascimento exigem antecedente sem outra pessoa ambígua, inclusive nomes introduzidos após vírgula. Uma mãe, esposa ou pessoa citada não empresta sua data a outra pessoa.
- Datas de publicação são metadados tipados separados. Atualização, criação, elementos ocultos, navegação e cartões de vídeo não fornecem data de publicação.
- Expressão relativa explícita do corpo, como “hoje (8)”, só pode usar publicação compatível com dia/mês/dia da semana quando aplicável. Data de consulta nunca vira data do evento.
- Legendas de imagem, inclusive classes comuns de CMS, são contexto e não corpo factual.
- Afirmação de impacto **intencional** exige esse qualificador no próprio trecho de apoio. Apenas dizer que houve colisão não comprova a intenção.
- Valor, unidade, direção e período-base de uma medição precisam estar ligados à mesma comparação, tanto para apoio quanto para refutação. Números espalhados no parágrafo não bastam.
- Modelo seleciona IDs de fonte/trecho; o servidor recupera a citação literal. IDs inventados, citações alteradas e envelopes inválidos são rejeitados. Não há reparo semântico repetido até obter a resposta desejada.
- Provedor principal e alternativa compartilham o mesmo prazo de comparação. O principal não consome todo o prazo antes de dar oportunidade à alternativa. Resposta válida, mas sem evidência, não é reenviada a outra IA para buscar concordância.

### Registro original: exceção explícita, não confiança irrestrita

Há diferença entre verificar o que um instituto publicou e certificar o fenômeno descrito. A política permite leitura de um único registro original em construções delimitadas: informe do IBGE sobre PIB, relatório atribuído ao Copernicus e pronunciamento de classificação da OMS em sua seção de discursos.

Continuam obrigatórios domínio/família/tipo primário compatíveis, trecho correspondente, data de publicação quando alegada e validação do evento, números e negação. Página enviada pelo usuário e material de agência não recebem essa exceção. Ela não se aplica genericamente a notícias, recomendações médicas/financeiras/jurídicas ou a qualquer página oficial.

O relatório identifica **“Confirmada/Contradita no registro original”**, explica que há uma única fonte primária e não inventa duas confirmações independentes. O controle climático é esse caso. A confirmação da OMS nesta rodada também reuniu CNN e pronunciamento original.

### Interface e acessibilidade

- “Não determinado” sem largura fixa de desktop, barra fictícia ou porcentagem inventada.
- Título e indicador empilhados até haver espaço de desktop; título longo pode quebrar com segurança. Cabeçalho do compartilhamento pode ocupar outra linha.
- Veredito sustentado por documentos mostra “Veja as evidências”, sem um segundo “Não determinado” que pareça contradizê-lo.
- Pesquisa de reprodução literal sem correspondências fica recolhida e claramente separada da checagem factual. Checagens publicadas e documentos usados no cruzamento também são distinguidos.
- Falta de reprodução literal não vira rejeição factual no título principal: o relatório diz “Análise inconclusiva”.
- Animação continua até o alvo real, sem ultrapassá-lo; zero permanece zero. Modo Fácil e preferência de movimento reduzido interrompem também a animação JavaScript do indicador.
- Relatório real medido a 320 px: largura do documento 305 px no Modo Fácil e 310 px no normal, sem rolagem horizontal. Verificações adicionais a 414, 768 e 1280 px; a 768 px, título/indicador empilhados; a 1280 px, duas colunas. Preferência de tamanho temporária do navegador restaurada ao final.

## Como interpretar a medição

O manifesto fixou oito afirmações públicas antes das requisições, quatro verdadeiras e quatro falsas. Houve repetições durante correções. É um **conjunto de desenvolvimento**, não um teste independente, aleatório, abrangente ou congelado em uma só revisão.

- Primeira tentativa: primeira linha do caso, sem escolher a melhor.
- Resultado mais recente: última tentativa do mesmo caso, mesmo se regredir.
- Conclusão correta: `supported` para verdadeiro ou `refuted` para falso.
- Inconclusivo permanece no denominador; não conta como acerto.
- Precisão entre conclusivas é uma métrica separada. Não apresentar “todas as conclusivas corretas” como “100% de acerto do sistema”.
- Repetições do mesmo assunto não são novas amostras independentes.
- Exportação PDF não é outra checagem nem outro caso de verdade.

O [resumo numérico e a sequência integral de tentativas](validation-verdicts-summary-2026-10-17.json) devem ser lidos junto com as limitações e pendências abaixo.

## Resultados fechados

Foram **24 verificações reais de texto pela interface**, dos mesmos oito controles, e uma exportação PDF separada. A continuação final acrescentou oito verificações aos 16 registros anteriores; nenhum registro antigo foi apagado. Todas as verificações textuais tiveram resposta HTTP 200, mas isso não significa veredito conclusivo ou correto.

| Recorte | Conclusões corretas | Inconclusivos | Conclusões erradas observadas |
| --- | --- | --- | --- |
| Primeira tentativa de cada caso | 1/8 — 12,5% | 7/8 — 87,5% | 0/8 |
| Última tentativa de cada caso | 4/8 — 50% | 4/8 — 50% | 0/8 |
| Todas as tentativas, incluindo repetições | 7/24 — 29,17% | 17/24 — 70,83% | 0/24 |

**Os 50% não são um benchmark da revisão final congelada.** As tentativas ocorreram ao longo de correções; a Rainha com data verdadeira foi concluída na tentativa 11 e não repetida depois do último ajuste. A aprovação da OMS na tentativa 17 também antecede ajustes posteriores de recuperação. As duas checagens finais, clima e Rainha com data falsa, preservaram as respectivas refutações depois dos últimos ajustes.

| Controle | Esperado | Última tentativa | Resultado observado |
| --- | --- | --- | --- |
| Elizabeth II morreu em 08/09/2022 | Corroborar | 11 | Corroborada; duas famílias elegíveis |
| Elizabeth II morreu em 09/09/2022 | Refutar | 25 | Refutada; Reuters e UOL. Reprodução Reuters em outro veículo não virou terceira família |
| Impacto intencional DART/Dimorphos em 26/09/2022 | Corroborar | 20 | Inconclusiva; só uma evidência aceita. Houve sucesso anterior em 3 e regressão em 16, ambos preservados |
| Classificação da COVID-19 como pandemia pela OMS em 11/03/2020 | Corroborar | 17 | Corroborada; pronunciamento original e CNN |
| IBGE divulgou crescimento do PIB de 3,4% em 2024, em 07/03/2025 | Corroborar | 19 | Inconclusiva; registro correto bloqueou leitura e nenhum trecho completo foi elegível |
| Copom reduziu Selic de 10,75% para 10,50% em 18/09/2024 | Refutar | 22 | Inconclusiva; corpo/data/transição completos não recuperados |
| Copernicus publicou que 2024 ficou 1,60°C abaixo da referência 1850–1900 | Refutar | 23 | Contradita no registro original; uma fonte primária, explicitamente identificada |
| Artigo 1º da Lei nº 3.353 não extinguiu legalmente a escravidão | Refutar | 21 | Inconclusiva; apenas LexML elegível, sem segunda família |

Entre os quatro controles verdadeiros, dois foram corroborados e dois ficaram inconclusivos. Entre os quatro falsos, dois foram refutados e dois ficaram inconclusivos. Não houve um par de revisões idênticas em condições congeladas para atribuir toda a diferença às mudanças de código: a busca pública também variou.

Imagem, áudio e vídeo: **sem nova porcentagem de acerto nesta rodada**. Os testes históricos de integração e as pendências permanecem nos registros anteriores, sem transferência automática da métrica textual.

### Transporte real e exportação

Contadores cumulativos conferidos com a soma de chamadas atribuídas às verificações; a tabela abaixo contém somente o acréscimo desta sequência, não o consumo histórico total:

| Destino | Chamadas novas | Respostas observadas |
| --- | --- | --- |
| OpenRouter gratuito | 25 | 25 HTTP 200; uma resposta auxiliar de pistas não passou no contrato e usou fallback Gemini |
| Gemini | 11 | 10 HTTP 200, um HTTP 503; alternativa OpenRouter demonstrada na tentativa DART anterior |
| Google Fact Check | 24 | 24 HTTP 200; ausência de correspondência não confirmou nem refutou |
| Busca de notícias/referências | 92 | 92 HTTP 200; descoberta, não evidência por resumo |
| Leitor público de páginas | 126 | 102 HTTP 200, dez 403, um 401, dez redirecionamentos e três tentativas sem status final |
| Hive, Sightengine e AssemblyAI | 0 | Nenhuma chamada nova nesta sequência textual |

O PDF foi acionado pela interface na linha 24: HTTP 200, cabeçalho `%PDF` válido e **zero novas chamadas de análise**. A interface informou “PDF preparado”; o navegador integrado não emitiu evento de download durante a espera. Portanto, arquivo salvo e inspeção visual do PDF **não foram confirmados** nesta passagem. Esse registro não entrou nos denominadores de veracidade.

## Pendências que impedem declarar o projeto pronto

1. **DART:** os resultados de busca variam; uma tentativa anterior corroborou e outra regrediu. Na última checagem houve só uma evidência aceita. A legenda e a ausência do qualificador de intenção identificadas nessa passagem receberam guardas adicionais depois dela; o controle completo ainda exige uma rodada congelada com o leitor final.
2. **PIB/IBGE:** o ranking passou a selecionar a publicação correta, mas ela bloqueou a leitura segura. Uma notícia de anúncio não comprova o número publicado; a alegação inclui data de divulgação e comparação anual. É necessário recuperar um registro original acessível ou notícias independentes com todos esses campos vinculados.
3. **Copom/Selic:** páginas oficiais dependentes de JavaScript e trechos com data, variação e taxa anterior dispersas não forneceram correspondência completa. Implementar leitor de um recurso público oficial documentado ou ligação segura desses campos, com controles negativos para anos e transições trocados.
4. **Lei Áurea:** a recuperação melhorou em relação à primeira tentativa sem corpos utilizáveis, mas não reuniu duas famílias elegíveis. Não tratar negação, artigo de lei e narrativa histórica como equivalência lexical automática; ampliar o leitor/fontes e cobrir numeração/escopo antes de flexibilizar decisão.
5. **Avaliação independente:** congelar a revisão, separar controles de desenvolvimento e teste, ampliar temas/datas/negações/valores e repetir com fontes conhecidas. Registrar conclusividade, erros e inconclusivos por classe e modalidade, com denominadores explícitos.
6. **Mídias:** imagem, áudio e vídeo não receberam nova avaliação de precisão nesta rodada textual. OCR, transcrição e detecção de origem são dimensões diferentes; não herdam a porcentagem obtida em texto. O limite pago Hive anterior já havia sido consumido; nenhuma nova chamada paga foi feita nesta continuação.
7. **Produção:** publicar somente a revisão revisada, preservar as mudanças originais do usuário e fazer smoke no ambiente reativado. Testes locais não verificam o estado futuro do Railway.

## Testes técnicos e limites operacionais

Suíte final: **792 testes backend aprovados, sem skips**, em contêiner sem rede e com SQLite descartáveis; **22 arquivos de testes frontend aprovados**, sem skips; build frontend aprovado; revisão de espaços/diff aprovada. Avisos de recursos de streams de teste foram emitidos, sem falha de teste. Isso verifica regressões automatizadas, não mede precisão geral dos vereditos.

Comandos de reprodução do projeto:

```sh
cd backend
python -B scripts/run_offline_tests.py
```

```sh
cd frontend
npm test
npm run build
```

A execução desta rodada usou a imagem de runtime existente, testes sem rede, `DATABASE_URL` e `TEST_DATABASE_URL` apontando para SQLite descartáveis. O harness de interface é isolado, com credenciais privadas por lista permitida e banco/usuário descartáveis; não é configuração de deploy. Não importar seu banco, limites ou contadores para produção.

Gemini usou `gemini-3.1-flash-lite`; OpenRouter, `openrouter/free`, com filtro de preço zero já existente. Os tetos locais de QA gratuitos foram ampliados explicitamente na continuação, preservando contadores históricos. Tetos/reservas de Hive e demais mídias não foram zerados nem ampliados. Erro de quota real não autoriza troca de chave ou tentativas para contorná-lo.

Para retomada de produção, seguir [o guia Railway](REATIVAR-RAILWAY-2026-10-13.md). Esta revisão não precisa de novas chaves para corrigir seleção/leitura de fontes. A configuração pública relevante continua sendo `SOURCE_CROSSCHECK_ENABLED`, `SOURCE_CROSSCHECK_PRIMARY_PROVIDER`, `SOURCE_CROSSCHECK_TIMEOUT_SECONDS` e `SOURCE_CROSSCHECK_SEARCH_LIMIT`, além das chaves privadas dos provedores já integrados. Não colocar segredos no frontend, no README ou no Git.
