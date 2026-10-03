# Continuação da revisão — 2 de outubro de 2026

Alterações locais. Sem push ou deploy. A cópia revisada é a entrega; o disco externo não foi sincronizado.

## Relatório, animação e rolagem

- Explicação estruturada visível nas duas visões: sinais, trechos encontrados, referências retornadas, lacunas e como conferir o original.
- Regras de golpe incluem o trecho efetivamente encontrado. A ocorrência de padrão não comprova identidade, fraude nem falsidade de todas as afirmações.
- Referências cadastradas de segurança (Banco Central/Correios) são rotuladas separadamente de checagens recuperadas por API. Citações sugeridas por um modelo não são exibidas como consultas reais.
- Vídeo informa quadros e timestamps; áudio separa transcrição/risco do discurso de autenticidade da voz.
- Indicador cresce de zero até o valor recebido, sem ultrapassar 100. Movimento reduzido desliga a animação. Sem evidência/resultado inconclusivo não recebe porcentagem inventada.
- Scrollbar personalizada preserva rolagem nativa, teclado e toque; contraste forçado usa cores do sistema.
- Extensão de domínio isolada não produz mais veredito de golpe; a URL é analisada pelo hostname, não por uma ocorrência na query.

## Segurança e operação

- Consulta de links fixa a conexão ao IP público validado; mantém TLS/SNI do domínio original. Downloads têm limites de bytes, tempo e redirecionamentos.
- Webhook exige segredo forte antes de ler o corpo; rejeita configuração incompleta. Eventos próprios/outros tipos são ignorados, base64 é validada e mídia não cai na análise de texto.
- Proteção em memória contra repetição de IDs por dez minutos, incluindo processamento em andamento. Falhas liberam nova tentativa. Não é uma garantia de entrega e não é compartilhada entre réplicas.
- Controle de solicitações, concorrência e envio. Origens de escrita não autorizadas são recusadas; wildcard CORS não vira acesso para todos os projetos Vercel.
- Nenhum JWT assinado com fallback público conhecido. Produção exige segredo configurado; desenvolvimento sem segredo usa chave efêmera.
- Histórico de WhatsApp opcional e HMAC do remetente. Mensagens continuam potencialmente pessoais, portanto não se promete anonimato.
- Inicialização/encerramento usa lifespan, incluindo encerramento do pool do banco.
- Contexto de autenticação separado da fronteira de componentes: corrigida uma falha observada durante Fast Refresh no desenvolvimento, sem mascarar ausência de provider.

## Verificação

- Backend: **92 testes e 48 subcasos passaram**, sem skipped; três avisos de depreciação permanecem.
- Interface: **12 testes passaram**; build Vite concluído.
- HTTP local: **25 controles de funcionamento** e **13 controles de segurança/webhook passaram**. Artefatos: [funcionamento](audit-continuation-local-2026-10-02.json) e [segurança](audit-security-http-2026-10-02.json).
- O servidor de smoke teve limites locais elevados para executar os controles consecutivos sem mascarar seus resultados. Limites 429, tamanho, concorrência e timeout foram exercitados separadamente pelos testes do middleware; não foi um teste de carga em produção.
- Consulta HTTPS real a example.com: documento recebido com TLS e hostname original preservados.
- Navegador: texto → relatório com trecho real/orientação oficial; largura de celular 390 px sem overflow horizontal; scrollbar com cores personalizadas. Vídeo → relatório com três tempos reais (0,3/1,5/2,7 s), cobertura e limitações. Houve erro de contexto durante atualização de código; foi corrigido e a carga limpa final não registrou novos erros.
- Controle visual fictício de 90: preenchimento observado crescendo e terminando em `scaleX(0.9)`; zero e “Não determinado” também exibidos corretamente. Isso é teste de animação, não resultado de uma análise.

Os testes locais não usam provedores pagos e não medem precisão de detecção. As provas visuais ficam em [relatório no celular](report-details-mobile.jpg) e [controle da animação](score-animation-90.jpg).

Controles de mídia usam uma imagem gerada e um MP4 estático curto. Não substituem benchmark rotulado de face-swap, lip-sync ou voz clonada.

## Ainda prioritário

1. Publicar a revisão com CORS, cookies HTTPS, segredos e FFmpeg configurados; repetir os fluxos no deploy efetivamente ativo.
2. Restaurar provedores com erros de acesso/quota; medir cobertura e custo. Um teste passando com mocks não certifica credenciais reais.
3. Limites/repetição compartilhados antes de múltiplas réplicas. Orçamento por usuário/provedor e proteção no proxy/WAF.
4. Retenção/exclusão de conta, histórico e mensagens; canal de contato e tratamento de dados.
5. Fila assíncrona para vídeos e análises demoradas, com progresso real/cancelamento; ampliar amostragem sem prometer perícia temporal.
6. Conjunto rotulado/licenciado, calibração separada e métricas por modalidade (falsos positivos/negativos/inconclusivos).
7. Testes reais de login Google/cookies entre domínios, acessibilidade e dependências.
8. Provisionar Evolution e testar recebimento/descriptografia/envio com um número de teste. JSON de resposta sozinho não envia mensagem.

## Referências usadas

- [HTTPX: conexão por IP com Host e SNI](https://www.python-httpx.org/advanced/extensions/).
- [FastAPI: lifespan](https://fastapi.tiangolo.com/advanced/events/).
- [Vite React: exports consistentes para Fast Refresh](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md).
- [Evolution: eventos de webhook](https://github.com/evolution-foundation/docs-evolution/blob/main/v2/en/configuration/webhooks.mdx). Configuração e suporte a headers precisam ser conferidos na versão instalada.
- [Banco Central: golpes envolvendo seus serviços](https://www.bcb.gov.br/meubc/faqs/p/golpes-envolvendo-o-meu-bc).
- [Correios: segurança](https://www.correios.com.br/falecomoscorreios/seguranca).
