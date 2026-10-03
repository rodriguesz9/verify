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
