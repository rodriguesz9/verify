# Landing e Modo Fácil — revisão de 3 de outubro de 2026

## Correções

- Preferência única de acessibilidade, inicializada antes da renderização, compartilhada entre páginas e sincronizada entre abas.
- Migração das preferências antigas conflitantes; desligar o modo remove a ampliação e o estado ativo de fato.
- Letras ampliadas uma vez, sem multiplicação em elementos aninhados. Botões maiores, menu com rótulo e fechamento por Escape, retorno de foco e perguntas com estado expandido acessível.
- Navegação compartilhada pela landing e pela aplicação, com links corretos de termos/privacidade e disposição adaptada ao espaço disponível.
- Demonstração com mensagem, sinais de atenção e próximo passo. Sem três colunas estreitas, texto truncado ou porcentagem fictícia.
- Cartões e seções reorganizados responsivamente. Campos de arquivo operáveis pelo teclado, espaços internos menores no celular e seletores de conteúdo sem ocupar cinco linhas enormes.
- Entrada suave de seções e estados de interação; nenhuma animação decorativa no Modo Fácil. CSS respeita `prefers-reduced-motion`; a abertura animada também é omitida quando essa preferência já está ativa ao carregar.
- Conteúdo explicita limites: IA não equivale a falsidade e ausência de detecção não comprova autenticidade.

## Verificação local

Build de produção aprovado. 21 casos frontend aprovados (6 de acessibilidade, 2 de contexto de autenticação, 13 de relatório), além da execução agrupada por arquivos.

Navegador: landing em 320, 390, 768, 1024 e 1440 pixels, modo normal e Fácil; rechecagem após os ajustes finais. Medidas de elementos/textos e inspeção visual para detectar transbordamento, não apenas `body` sem barra horizontal. Na tela de checagem foram conferidos os cinco seletores, menu, tamanhos de controles e áreas de envio. Persistência confirmada em navegação, recarga de `/app` e recarga de `/login`. Modo Fácil desligado retorna a 16 px; ajustes normais de texto resultam em 17,6 e 19,2 px, sem crescimento acumulado.

Escape fecha o menu e devolve foco ao controle. Perguntas abrem/fecham sem recorte. Animações computadas das seções e transições são `none` no Modo Fácil. Console sem erros JavaScript nos fluxos locais; avisos conhecidos de migração futura do React Router continuam presentes.

**Escopo:** esta etapa visual usou uma resposta local de sessão não autenticada, sem chaves/fornecedores externos. Não testou login real, vereditos por API, cobrança, reprodução de voz externa ou todos os estados possíveis de relatório/painel. O navegador disponibilizou alteração de viewport, não emulação de `prefers-reduced-motion`: essa preferência foi conferida no CSS e na inicialização, mas não foi emulada. Não é uma certificação completa WCAG nem uma medida de precisão.

Setup e limites operacionais estão em [ATIVAR-DETECTORES.md](ATIVAR-DETECTORES.md). Push/build/deploy não comprovam precisão dos detectores; esses testes devem ser repetidos com controles reais autorizados depois da configuração.

## Retorno ao azul/ciano — mesma data

A pedido do responsável, os destaques da landing e da navegação retornaram a `#00D4FF`. Layout, conteúdo, animações e comportamento de acessibilidade foram preservados. Cores semânticas de alerta/resultado não foram substituídas pela cor da marca. Variáveis compartilhadas em `index.css` mantêm botões e links consistentes.

Build aprovado novamente. Os 21 casos existentes e os 3 novos de `landingTheme.test.js` passaram, totalizando 24 casos frontend. Os novos testes cobrem paleta, contraste de texto dos botões/links/estado ativo e preservação do aviso e das salvaguardas de movimento.

Prévia de produção local conferida no navegador em 1440 px e em 320 px com Modo Fácil: azul computado `rgb(0, 212, 255)`, nenhuma largura de texto excedendo os respectivos controles inspecionados, fonte raiz de 20 px e animação `none` no Modo Fácil. Landing sem overlay de erro e sem erros JavaScript capturados. Essa conferência não repetiu o fluxo de análise nem testou login/backend.

Configuração com orçamento zero: [APIS-SEM-CUSTO.md](APIS-SEM-CUSTO.md). Nenhum detector foi contratado ou certificado por esses testes visuais.
