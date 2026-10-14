# Verify — reativação segura do Railway

Guia de 13 de outubro de 2026, horário de Brasília. Preparado após o usuário informar expiração do Railway. Não houve contratação, recarga, alteração de variáveis da conta, leitura do `.env` privado ou confirmação de recuperação do banco durante a elaboração deste guia.

Revisão de configuração de **14/10/2026**: atualiza a ordem Gemini/OpenRouter e a recuperação documental limitada; não altera nem substitui os resultados históricos de 13/10. Os controles atuais e suas pendências ficam no [registro de validação de APIs de 14/10](VALIDACAO-APIS-2026-10-14.md). Railway continua expirado; testes locais não comprovam retorno da produção, e testes pela interface ainda precisam de registro específico.

Objetivo: recuperar o backend existente, preservar contas/histórico e validar o fluxo Vercel → Railway → PostgreSQL → fornecedores → relatório. Renovação da hospedagem não garante disponibilidade de todas as APIs nem precisão universal dos vereditos.

## 1. Antes de renovar: preservar dados e identificar a interrupção

1. Entre no workspace correto do Railway e abra o projeto existente. Confirme o ambiente de produção, o serviço do backend e o PostgreSQL associado. Não crie outro projeto para substituir o atual antes de localizar os dados.
2. Confira a mensagem exata em Billing/Usage: fim de Trial, créditos esgotados, limite de consumo, fatura pendente e pagamento recusado são causas diferentes. Compare data da suspensão com os avisos recebidos.
3. Verifique se o serviço PostgreSQL, o volume anexado e os backups ainda aparecem. Anote somente nomes, IDs e datas; não copie senhas ou URLs completas de conexão para mensagens, prints ou documentação pública.
4. Não apague/recrie PostgreSQL, volume, ambiente ou projeto. Não restaure backup sobre produção sem comparar sua data, preservar o estado atual e aprovar a perda potencial de dados posteriores.
5. Quando houver acesso ao banco novamente, confirme contas e histórico existentes e faça backup protegido antes de alterações estruturais. Uma restauração precisa ser testada em destino separado; a existência de um botão de backup não comprova recuperação.

Retenção não é ilimitada: a documentação informa 30 dias após expiração para Free/Trial, 60 após cancelamento para Hobby e 90 para Pro. São políticas publicadas, não confirmação de que este volume específico esteja íntegro ou recuperável. Se volume/backups estiverem ausentes ou o prazo estiver próximo, procure suporte antes de qualquer reconstrução. [Política de retenção Railway](https://docs.railway.com/pricing/plans), [retenção do Trial](https://docs.railway.com/pricing/free-trial#data-retention).

Railway dispõe de backups de volumes, inclusive para bancos, mas criação/restauração e armazenamento podem ter limites e custo. Este guia não habilita backup pago nem executa restauração. [Backups oficiais](https://docs.railway.com/volumes/backups).

## 2. Resolver a hospedagem sem contratar nada automaticamente

O titular da conta deve escolher como resolver a causa indicada no painel e conferir preço, consumo incluído, cobranças adicionais e orçamento antes de confirmar pagamento. Não assumir que saldo Hive ou créditos de uma API pagam a hospedagem Railway.

A documentação descreve redeploy automático quando a causa da suspensão é resolvida dentro de 30 dias; depois desse período pode ser necessário redeploy manual. Mesmo dentro da janela, confirme o retorno real do PostgreSQL e do backend. Não confunda deploy antigo marcado como bem-sucedido com serviço atualmente acessível. [Serviços interrompidos — FAQ Railway](https://docs.railway.com/pricing/faqs).

Revise alertas de consumo e limites já existentes, sem removê-los apenas para fazer uma apresentação funcionar. Um limite rígido de Compute pode colocar os serviços offline ao ser atingido; alerta por e-mail não impede consumo. Limites Railway não controlam cobranças em Hive, Gemini, Serper ou outras APIs externas. [Controle de custos Railway](https://docs.railway.com/pricing/cost-control).

## 3. Conferir PostgreSQL e a referência do backend

No serviço **backend**, `DATABASE_URL` deve referenciar o PostgreSQL do mesmo projeto/ambiente pela rede privada. Se o serviço se chama exatamente `Postgres`, o valor de referência é:

```text
${{Postgres.DATABASE_URL}}
```

Se o nome for diferente, selecione a referência correspondente pelo painel; não copie literalmente o nome deste exemplo. Não substitua as variáveis originais do próprio serviço PostgreSQL. A sintaxe de referências e a conexão entre serviços são documentadas pelo Railway. [Variáveis e referências](https://docs.railway.com/variables#reference-variables), [conexão PostgreSQL](https://docs.railway.com/databases/postgresql#connect).

Não colocar em produção:

- `sqlite+aiosqlite:///./verify-local.db`, `sqlite+aiosqlite:///./verify.db` ou outro SQLite de exemplo;
- `localhost`, `127.0.0.1` ou o nome de container `db` do Compose local;
- credencial de outro ambiente ou banco de testes;
- `DATABASE_PUBLIC_URL` como primeira opção para comunicação entre backend e banco do mesmo projeto.

O código converte URLs `postgres://` e `postgresql://` para o driver assíncrono `postgresql+asyncpg://`. Não é necessário fabricar outra URL nem expor senha no Git. A inicialização cria tabelas ausentes e adiciona valores compatíveis de enum; não substitui migrações completas, backup ou validação do schema existente. **Nunca executar o runner de testes PostgreSQL contra produção: ele recria tabelas.**

Se o PostgreSQL voltar vazio, pare a validação de recuperação. O backend pode iniciar com tabelas novas e `/ready` responder 200, mesmo sem contas/histórico anteriores. Isso não comprova preservação dos dados.

## 4. Build, diretório, início e prontidão

Este repositório possui dois layouts coerentes. Preserve o já utilizado pelo serviço, conferindo se todas as opções pertencem ao mesmo layout:

| Configuração | Repositório como contexto | Backend como contexto |
| --- | --- | --- |
| Root Directory | `/` | `/backend` |
| Railway Config File | `/railway.toml` | `/backend/railway.toml` |
| Dockerfile no contexto de build | `Dockerfile` da raiz, que copia `backend/` | `Dockerfile` do backend, que copia seu diretório |
| Builder | `DOCKERFILE` | `DOCKERFILE` |
| Processo | CMD do Dockerfile | Comando de `backend/railway.toml` |
| Healthcheck | `/ready` | `/ready` |
| Prazo de healthcheck neste repo | 120 segundos | 120 segundos |

Não misture Root Directory `/backend` com o Dockerfile raiz que procura `backend/requirements.txt`. O caminho do arquivo Railway é configurado a partir do repositório, não automaticamente relativo ao Root Directory. [Build configuration](https://docs.railway.com/builds/build-configuration), [monorepo](https://docs.railway.com/deployments/monorepo).

O servidor precisa ouvir em `0.0.0.0` e na porta fornecida pelo Railway. O Dockerfile já possui CMD compatível; não exige Vite, reload, outro servidor ou porta fixa local. Se houver override de Start Command, confira sua expansão de `PORT`:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

O build Docker inclui FFmpeg/ffprobe, ExifTool e Tesseract português/inglês. Não substitua pelo Compose de desenvolvimento. `c2patool` é opcional e não é instalado por esses Dockerfiles; ativar sua variável não cria o executável nem homologa autenticidade.

Confira branch/commit do deploy desejado após a revisão e os testes. Evite redeploy de uma revisão antiga com configurações antigas apenas porque aparece primeiro na lista.

`/health` verifica processo vivo; `/ready` executa consulta simples ao banco, com prazo curto. `/ready` não comprova escrita, schema completo, preservação do histórico, API externa ou veredito correto. Healthcheck Railway é usado na entrada do deploy, não é monitoramento contínuo. [Healthchecks Railway](https://docs.railway.com/deployments/healthchecks).

## 5. Variáveis de produção: revisar, não copiar o `.env` inteiro

`.env.example` é um catálogo público com valores de desenvolvimento e opções desligadas; não é arquivo pronto para colar integralmente em produção. O `.env` privado contém segredos e pode ter opções locais/antigas. Confira nomes no exemplo da revisão que será publicada; preserve valores já válidos no Railway.

Ao usar o Raw Editor, não sobrescreva segredos existentes com campos vazios, SQLite local ou exemplos. Preencha apenas variáveis escolhidas, no **backend de produção**. Railway prepara alterações pendentes; revise antes de aplicar/deploy. [Variáveis Railway](https://docs.railway.com/variables).

### Base obrigatória para produção

| Nome no backend | Configuração esperada | Cuidado |
| --- | --- | --- |
| `APP_ENV` | `production` | Ativa exigência de segredo JWT forte. |
| `DATABASE_URL` | Referência privada ao PostgreSQL existente | Nunca publicar o valor resolvido. |
| `JWT_SECRET` | Segredo aleatório independente, mínimo 32 caracteres | Preservar valor forte existente; troca invalida sessões. |
| `HMAC_SECRET_KEY` | Outro segredo aleatório, mínimo 32 caracteres | Preservar valor forte existente; troca invalida cópias assinadas de relatório/conferência. |
| `COOKIE_SECURE` | `true` com HTTPS | Não corrigir autenticação desligando proteção. |
| `COOKIE_SAME_SITE` | `none` para frontend Vercel/API Railway em sites distintos | Precisa `COOKIE_SECURE=true`; testar restrições do navegador. |
| `CORS_ORIGINS` | Origem exata do frontend, por exemplo `https://verifybr.vercel.app` | Sem caminho, barra final ou `*`; vários domínios próprios separados por vírgula. |
| `CORS_ORIGIN_REGEX` | Vazio, se origens exatas bastam | Não liberar todos os clientes `vercel.app`. |

Não reutilizar segredo de API como JWT/HMAC nem usar o mesmo segredo nos dois campos. Não gerar segredos novos por ocasião de todo deploy. Só rotacionar deliberadamente se ausentes, fracos ou comprometidos, considerando sessões/tokens afetados.

Cookies cross-site podem ser restringidos pelo navegador mesmo com flags corretas. Depois da retomada, testar login, renovação, logout e histórico pelo frontend, não apenas endpoint isolado. Não mover JWT para armazenamento JavaScript como atalho.

### Texto, busca e leitura — sem novas contratações

| Variáveis | Utilidade e limites |
| --- | --- |
| `GOOGLE_FACT_CHECK_KEY` | Recupera checagens editoriais existentes; sem resultado não significa notícia falsa ou API quebrada. |
| `SERPERAPI_KEY` | Busca de notícias/páginas para recuperar referências. Créditos e limites da conta continuam valendo. |
| `OPENROUTER_API_KEY`, `OPENROUTER_ENABLED=true`, `OPENROUTER_MODEL=openrouter/free` | Extração auxiliar, fallback de OCR e alternativa gratuita de comparação documental; API/modelos podem ficar indisponíveis. Não vota por conhecimento próprio. |
| `OPENROUTER_DAILY_LIMIT=40` | Limite local por processo, inclui tentativas com falha; não aumenta limite externo nem é controle financeiro global. |
| `OPENROUTER_FALLBACK_MODELS` | Manter vazio ou usar somente variantes específicas `:free` aceitas pelo código; não `openrouter/auto`. |
| `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `GEMINI_MEDIA_MODEL_NAME` | Preservar os modelos explícitos escolhidos no último deploy; o usuário havia configurado `gemini-3.1-flash-lite`. Confirmar acesso/cota atual, sem trocar modelos automaticamente na retomada. |
| `GEMINI_REQUEST_TIMEOUT_SECONDS=60` | Prazo total por chamada, permitido 10–90; aumentar prazo não resolve falta de cota nem pagamento. |
| `GEMINI_LOCAL_ADMISSION_ENABLED=true`, `GEMINI_LOCAL_REQUESTS_PER_MINUTE=5`, `GEMINI_RATE_LIMIT_COOLDOWN_SECONDS=60` | Proteção de rajadas por processo/modelo; escolher RPM não maior que o disponível na conta. Não contornar quota trocando modelos/contas. |
| `GEMINI_FALLBACK_MODELS` | Manter vazio se não houver modelo alternativo explicitamente habilitado e testado. |
| `LOCAL_OCR_ENABLED=true` | Tesseract local lê texto de imagens sem API. OCR não detecta falsidade nem comprova origem. |

Não confundir `SERPERAPI_KEY` com `SERPAPI_KEY`: são fornecedores distintos. A segunda não substitui a primeira na busca textual deste pipeline. Gemini/OpenRouter auxiliam leitura, pesquisa e comparação de corpos efetivamente recuperados; concordância entre respostas não é prova factual.

### Novo cruzamento fundamentado

A implementação iniciada em 13/10 reutiliza as APIs existentes, sem nova contratação. Depois de publicar a revisão correspondente, conferir no backend:

```text
SOURCE_CROSSCHECK_ENABLED=true
SOURCE_CROSSCHECK_PRIMARY_PROVIDER=gemini
SOURCE_CROSSCHECK_TIMEOUT_SECONDS=60
SOURCE_CROSSCHECK_SEARCH_LIMIT=3
```

`SOURCE_CROSSCHECK_ENABLED` controla a camada adicional; o default da revisão é `true`. `SOURCE_CROSSCHECK_PRIMARY_PROVIDER` aceita somente `gemini` ou `openrouter`, com **Gemini como padrão**. No perfil acima, OpenRouter continua a extração auxiliar de afirmações/termos literais e Gemini compara as afirmações originais com citações dos corpos recuperados. Se essa comparação ficar indisponível por transporte, quota ou ausência de configuração, OpenRouter gratuito pode servir de alternativa. Configuração inválida, JSON inválido ou resposta incompleta não acionam outra tentativa para reparar a conclusão.

O prazo de comparação é único, compartilhado entre o provedor primário e eventual fallback, com limite permitido de 10–60 segundos; não é prazo por tentativa nem garantia de resposta. A busca/leitura usa `SERPERAPI_KEY`. Gemini preserva o `GEMINI_MODEL_NAME` explícito já escolhido; OpenRouter preserva `openrouter/free`/variante específica `:free` e preço máximo zero. Falha de ambos não se transforma em voto factual. A opção `openrouter` apenas inverte essa ordem de comparação, sem transformar as duas IAs em fontes independentes.

`SOURCE_CROSSCHECK_SEARCH_LIMIT` aceita 1, 2 ou 3 (default 3):

1. A primeira busca usa a afirmação literal inteira elegível, sem cortar datas, valores ou negações. Até três páginas são inicialmente tentadas.
2. Se faltarem duas famílias **com corpos utilizáveis** e a busca responder com sucesso/sem resultados, pode haver recuperação em sites curados. Com limite 3 e construções reconhecidas, duas consultas neutras separam fontes oficiais e explicações editoriais/biográficas; com limite 2, há uma consulta combinada. Para outras construções, mantém uma consulta literal com filtro de sites. São pistas de recuperação, não reescrevem o que será julgado. Erro/quota interrompe o plano, sem contornar o fornecedor.
3. A leitura adicional pode levar o total a **seis tentativas cumulativas de páginas**, dentro de **45 segundos** compartilhados pela busca/leitura. Corpos e falhas já obtidos são reutilizados; falha não é repetida ou removida do teto. Das páginas elegíveis, até **três documentos** seguem para comparação.

A afirmação original — inclusive data errada ou negação — permanece intacta na seleção de evidência, nas guardas e na decisão. Identidade/evento de busca, título, snippet, data de publicação, documento enviado pelo usuário e citação de contexto não viram evidência positiva automaticamente. Títulos/subtítulos iniciais e sentenças adjacentes qualificam o corpo; a comparação exige sentença de corpo completa e validada.

Não repetir buscas após quota/erro para contornar o fornecedor. OCR/ASR automático não conferido mantém uma busca/prazo de 20 segundos e não executa a nova comparação; texto conferido entra nesse caminho. [Contrato histórico e limites de 13/10](CRUZAMENTO-FONTES-2026-10-13.md), [revisão e validação de 14/10](VALIDACAO-APIS-2026-10-14.md).

Google Fact Check continua como caminho especializado. O cruzamento pode buscar sustentação/refutação em corpos de páginas quando houver correspondência segura e duas famílias elegíveis (editoriais ou primárias); cópias/dependência de agência contam uma vez. Sem cobertura suficiente ou diante de contexto ambíguo/conflito, deve se abster. Ativar a variável não basta para homologar essa política: sua configuração deve coincidir com o código e o `.env.example` efetivamente publicados e os controles precisam ser realizados após a retomada.

Uma fonte enviada pelo usuário não é confirmação independente; notícias relacionadas, títulos/snippets e várias cópias da mesma matéria não bastam. O teste de retomada precisa conferir trechos recuperados, datas/valores/negações, independência, refutação e conflito, não procurar qualquer resultado “verdadeiro” para encerrar a validação.

### Imagem, áudio e vídeo

| Variáveis | O que manter/conferir |
| --- | --- |
| `SIGHTENGINE_API_USER`, `SIGHTENGINE_API_SECRET` | Credenciais existentes para modelos de imagem realmente autorizados na conta. Presença das chaves não garante acesso a todos os modelos. |
| `SIGHTENGINE_AUDIO_ENABLED=false` | Manter desligado: `ai_speech` não é habilitado automaticamente por chave de imagem. Não contratar acesso de voz neste fluxo. |
| `HUGGINGFACE_ENABLED=false` | Manter desligado; não criar endpoint dedicado pago nem comprar créditos. |
| `ASSEMBLYAI_API_KEY`, `AUDIO_TRANSCRIPTION_PROVIDER=assemblyai` | Usar somente se houver créditos gratuitos disponíveis/autorizados; transcrição `universal-2` não detecta clonagem de voz. Sem créditos, revisar alternativa disponível sem cobrar automaticamente. |
| `VIDEO_MAX_FRAMES=3` | Limita amostras; mais quadros aumentam consumo, não garantem análise temporal completa/lip-sync. |
| `HIVE_API_VERSION=v3` | Usar somente com Secret Key v3 correta e autorização de custo vigente. Chave de projeto v2 e Access Key ID não substituem Secret Key. |
| `HIVE_V3_API_KEY` | Secret Key v3 privada; `HIVE_API_KEY` também é compatível quando versão v3 foi selecionada explicitamente. Não publicar nenhum valor. |
| `HIVE_V3_MEDIA_TYPES=image,audio` | Opt-in pago autorizado anteriormente para saldo existente. Vazio bloqueia envio v3; não habilitar tipos adicionais. |
| `HIVE_V3_IMAGE_REQUEST_LIMIT=20`, `HIVE_V3_AUDIO_SECONDS_LIMIT=60` | Valores autorizados anteriormente; preservar teto acordado, não aumentar para obter um veredito. São reservas por processo, não teto em dólares. |

Cada quadro de vídeo é uma chamada de imagem Hive; imagem/facial v3 compartilham uma chamada, não são duas fontes independentes. Reinícios/redeploys repõem contadores locais e réplicas não os compartilham. Por isso não repetir releases para contornar limite. Confira saldo/uso real no fornecedor antes/depois de controles autorizados; sem recarga, cartão ou contratação automática.

`GPTZERO_API_KEY`, TinEye, Wayback, ExifTool, C2PA e outras opções não são requisitos para o backend iniciar. Não ligar todas indiscriminadamente. Detector de texto gerado por IA não prova falsidade, e ausência de sinais de IA não certifica mídia real. WhatsApp permanece desligado até integração/transporte/autenticação próprios serem configurados.

## 6. Vercel: URL pública e login Google

No projeto Vercel do frontend, ambiente Production:

```text
VITE_API_URL=https://DOMINIO-PUBLICO-DO-BACKEND
```

Substitua pelo domínio HTTPS atual do serviço backend. Não adicionar `/api`: o cliente já acrescenta esse caminho. Não usar domínio privado `railway.internal`, PostgreSQL, localhost ou URL de preview sem querer. O endereço anterior precisa ser confirmado após a reativação, não presumido como disponível.

Alteração de `VITE_API_URL` exige novo build/deploy do frontend: variáveis Vite são incorporadas ao bundle. Somente URL pública e client ID podem ficar em `VITE_*`; nunca chaves Gemini/OpenRouter/Hive, senha de banco, JWT ou HMAC. [Variáveis públicas e build Vite](https://vite.dev/guide/env-and-mode).

Login Google é opcional e separado das chaves Gemini/Fact Check. Se utilizado:

1. `GOOGLE_CLIENT_ID` no backend e `VITE_GOOGLE_CLIENT_ID` no frontend devem identificar o mesmo cliente OAuth Web válido.
2. No Google Cloud, adicionar a origem HTTPS exata do frontend em Authorized JavaScript origins. Não adicionar `/app`, `/api/auth/google` ou outro caminho nessa lista.
3. Conferir branding/consentimento e restrições de público/teste do projeto.
4. Validar login pela interface publicada depois do rebuild, sem compartilhar ID token/cookies.

Este fluxo usa callback JavaScript com validação do ID token no backend; não inventar um redirect URI adicional para “corrigir” sem examinar o fluxo. [Configuração oficial Google Identity](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid).

## 7. Sequência de validação depois da retomada

| Etapa | Critério de passagem | Não comprova |
| --- | --- | --- |
| Infraestrutura | Backend/PostgreSQL ativos; commit desejado; domínio HTTPS acessível | APIs externas ou precisão. |
| Prontidão | `/health` e `/ready` respondem adequadamente | Dados antigos preservados, escrita ou schema completo. |
| Persistência | Conta/histórico existentes recuperados; isolamento entre contas; nova checagem salva e reaberta | Toda política de retenção/backup. |
| Configuração | `/api/capabilities` informa opções esperadas sem segredos | Disponibilidade operacional de fornecedores; presença de chave não é teste real. |
| Texto/link | Entrada original preservada; checagens/fontes consultadas identificadas; falha, ausência e conflito separados | Verdade universal ou aprovação da página inteira. |
| Imagem | Controles reais e sintéticos autorizados; camadas/cobertura e sinais coerentes | Autenticidade certificada de qualquer imagem. |
| Áudio | Fala transcrita/conferida; detector de origem testado separadamente; pendência retomada sem reupload injustificado | Identidade/clonagem apenas pela transcrição. |
| Vídeo | Quadros e áudio tratados separadamente; timestamps/cobertura visíveis | Lip-sync ou perícia temporal completa com três quadros. |
| Relatório/PDF | Mesmo resultado exibido/exportado; arquivo salvo, aberto e conferido; limitações preservadas | Precisão dos fornecedores ou validação de todos os tipos só porque um PDF funcionou. |
| Usabilidade | Celular/computador, modo fácil, teclado, textos legíveis e mensagens de indisponibilidade compreensíveis | Compatibilidade de todos os aparelhos/navegadores. |

Para testes reais, usar arquivos próprios/autorizados ou controles públicos com procedência registrada. Não transmitir documentos pessoais, rostos de terceiros ou gravações privadas apenas para provar que uma API responde. Registrar data, revisão, modalidade, origem/ground truth, fornecedor/modelo realmente chamado, cobertura, resposta e limite do teste.

Se uma etapa falhar, registrar onde: transporte/frontend, API backend, banco, busca, leitura, quota, acesso ao modelo ou política de conclusão. Evitar sucessivas tentativas idênticas que consumam créditos e escondam a causa.

### Testes offline versus validação real

Os **567 testes backend e 170 frontend** são o checkpoint histórico de 11/10, antes do novo cruzamento. A contagem e o resultado da revisão de 13/10 devem ser obtidos na suíte final; não extrapolar nem somar execuções SQLite/PostgreSQL como casos independentes.

Checkpoint local final de 13/10: **637 backend, 181 frontend e build passaram**, sem chamadas externas na suíte. Controles públicos separados executaram busca/leitura e uma comparação OpenRouter, mas continuaram inconclusivos; Gemini e detectores de mídia não foram chamados nesta rodada. [Resultados e limites](CRUZAMENTO-FONTES-2026-10-13.md). Homologação no Railway segue pendente enquanto a hospedagem estiver expirada.

Em 14/10, as primeiras tentativas locais dos controles de Elizabeth II com 8/9 e 9/9 permaneceram inconclusivas. Diagnóstico separado demonstrou que os corpos públicos Royal/UOL conhecidos tinham trechos elegíveis nas guardas; isso não significa que a busca daquelas tentativas os tivesse recuperado. A revisão melhora recuperação/seleção e comparação, mas integração respondendo não basta para afirmar veredito correto. Os resultados finais, fornecedores realmente chamados, regressões e pendências são registrados separadamente em [validação de 14/10](VALIDACAO-APIS-2026-10-14.md), sem reclassificar tentativas antigas como acertos.

Testes pela API local não equivalem a ensaio pela interface. O ensaio de navegador permanece pendente nesta rodada por decisão do usuário; produção depende da retomada da hospedagem e de nova validação ponta a ponta.

O runner offline bloqueia rede/credenciais, testa regras/erros com controles e usa bancos descartáveis. Build e CI demonstram compilação/regressões, não acesso à conta, saldo, disponibilidade atual ou acerto de veredito numa notícia real. Produção indisponível continua impedindo homologação ponta a ponta; não registrar resultado local como teste concluído no Railway.

## 8. Erros comuns e verificação segura

| Sintoma | Conferir primeiro |
| --- | --- |
| Site abre, mas checagens não respondem | Backend Railway/domínio e URL embutida no frontend; depois rota/status, sem assumir falha Gemini. |
| `/health` 200, `/ready` 503 | PostgreSQL ativo, referência `DATABASE_URL`, rede/credenciais e logs sanitizados. Não apontar para SQLite para esconder falha. |
| Build não encontra `requirements.txt` | Root Directory, Dockerfile e Railway Config File do mesmo layout. |
| Login não persiste | HTTPS, cookies Secure/SameSite, origem CORS exata, restrição de cookies do navegador e identidade Google quando usada. |
| PDF indisponível | `HMAC_SECRET_KEY` forte/estável e relatório compatível; não substituir segredo válido aleatoriamente. |
| Google/Gemini HTTP 429 | Cota/RPM da conta, admissão e cooldown. Mais timeout não aumenta cota. |
| OpenRouter sem modelo gratuito | Disponibilidade/cota da rota gratuita; não substituir por modelo pago silenciosamente. |
| Hive indisponível | Secret Key v3, versão, media types e reserva; acesso de projeto v2 não equivale a v3. |
| Áudio transcreve, mas origem inconclusiva | Separação entre ASR e detector acústico; acesso real ao detector e quantidade de fala. |
| Texto continua inconclusivo com buscas respondendo | Fontes realmente recuperadas, sentenças de corpo elegíveis, cobertura/relação com afirmação original, dependência/cópias e motivo da seleção. Não confundir HTTP 200 com duas evidências utilizáveis. |

Não colar logs brutos, arquivos `.env`, cookies, tokens de relatório, credenciais ou URLs de banco em chat/issue. Para pedir ajuda, basta domínio público, hora, modalidade, mensagem/status, commit e nomes das variáveis presentes com valores ocultos.

## Checklist de liberação

- [ ] Causa de suspensão e orçamento revisados pelo titular; nenhuma contratação feita pelo agente.
- [ ] PostgreSQL/volume preservados; retenção, backup e dados anteriores conferidos.
- [ ] Layout Docker/root/config correto e commit desejado no backend.
- [ ] `DATABASE_URL` privada, JWT/HMAC fortes e estáveis, cookies/CORS de produção.
- [ ] Domínio backend confirmado; `VITE_API_URL` correto e frontend rebuildado quando necessário.
- [ ] APIs/opções configuradas somente nas modalidades autorizadas e com orçamento vigente.
- [ ] Regressões da revisão desejada registradas separadamente dos checkpoints de 11/10 e 13/10; consultar validação de 14/10.
- [ ] Testes reais pela interface realizados após retomada, com evidência e limitações por modalidade.
- [ ] Cadastro/login/histórico/isolamento e exportação reaberta validados sem dados privados indevidos.
- [ ] Nenhuma afirmação de “100% de precisão” ou “todas as APIs funcionando” sem evidência correspondente.
