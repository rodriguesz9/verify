# Verify

> Checagem acessível de mensagens, links, imagens e áudios para ajudar pessoas e famílias a reconhecerem golpes e desinformação antes de compartilhar.

O Verify combina sinais de risco, fontes de checagem e explicações claras. O resultado é apoio à decisão — não substitui confirmação em canais oficiais, perícia humana ou orientação jurídica.

## O que ele faz

- Checa texto e URLs suspeitas.
- Analisa imagens e áudios quando os provedores opcionais estão configurados.
- Identifica padrões comuns de golpe, como falso resgate de Pix e pedido urgente de dinheiro.
- Salva histórico por conta e gera relatórios de fácil leitura.
- Inclui uma [demonstração de uso](#demonstração-de-áudio) com voz falada no navegador e gravação de áudio real.

## Tecnologias

| Camada | Tecnologia |
| --- | --- |
| Interface | React, Vite, Tailwind CSS, Lucide |
| API | FastAPI, SQLAlchemy assíncrono |
| Banco | PostgreSQL 16 |
| Autenticação | Cookies HTTP-only, JWT, Argon2 |
| Execução local | Docker Compose |
| Publicação | Vercel (interface) + Railway (API e banco) |

## Executar com Docker

1. Crie o arquivo local de configuração:

   ```bash
   cp backend/.env.example backend/.env
   ```

2. Informe pelo menos uma chave Gemini nova no `backend/.env`. Nunca publique este arquivo.

3. Inicie os serviços:

   ```bash
   docker-compose up --build
   ```

No conjunto de portas deste repositório:

| Serviço | Endereço |
| --- | --- |
| Interface | `http://localhost:5174` |
| API | `http://localhost:8001` |
| Saúde da API | `http://localhost:8001/health` |
| PostgreSQL | `localhost:5433` |

Para encerrar sem apagar o banco local:

```bash
docker-compose down
```

## Variáveis de ambiente

Use [`backend/.env.example`](backend/.env.example) como a lista canônica. Não use prefixo `VITE_` em variáveis secretas: tudo que começa com `VITE_` é enviado ao navegador.

### Necessárias em produção

| Variável | Finalidade |
| --- | --- |
| `DATABASE_URL` | URL interna do PostgreSQL Railway |
| `GEMINI_API_KEY` | Orquestração e análise de texto/áudio |
| `JWT_SECRET` | Assinatura de sessões HTTP-only |
| `HMAC_SECRET_KEY` | Assinatura dos selos de autenticidade |
| `CORS_ORIGINS` | Domínio exato da interface Vercel |
| `COOKIE_SECURE` | `true` em HTTPS |
| `COOKIE_SAME_SITE` | `none` em domínios separados; `lax` sob domínio próprio compartilhado |

Gere os dois segredos locais, únicos e longos:

```bash
openssl rand -hex 32
```

### Integrações opcionais

Sem elas, o Verify permanece funcional, mas mostra menos evidências ou usa respostas de contingência.

| Variável | Serviço | Onde criar |
| --- | --- | --- |
| `GEMINI_API_KEY` | Google AI Studio | [Criar chave](https://aistudio.google.com/app/apikey) |
| `GOOGLE_FACT_CHECK_KEY` | Google Fact Check Tools | [Ativar API](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com) e [criar chave](https://console.cloud.google.com/apis/credentials) |
| `SERPERAPI_KEY` | Serper, busca de notícias | [Serper](https://serper.dev/) |
| `SERPAPI_KEY` | SerpApi, busca reversa | [SerpApi](https://serpapi.com/manage-api-key) |
| `SIGHTENGINE_API_USER` + `SIGHTENGINE_API_SECRET` | Sightengine, análise de mídia | [Credenciais Sightengine](https://dashboard.sightengine.com/api-credentials) |
| `HUGGINGFACE_API_TOKEN` | Hugging Face, segunda análise de imagem | [Tokens Hugging Face](https://huggingface.co/settings/tokens) |
| `HIVE_API_KEY` | Hive, análise multimídia | [Hive](https://thehive.ai/) |
| `TINEYE_API_KEY` | TinEye, origem de imagens | [TinEye API](https://services.tineye.com/) é PAGA, Não consegui pegar, temq ser aceito pelos devs do projeto deles|
| `ASSEMBLYAI_API_KEY` | AssemblyAI, transcrição e áudio | [Chave AssemblyAI](https://www.assemblyai.com/docs/faq/how-to-get-your-api-key) |
| `GPTZERO_API_KEY` | GPTZero, análise complementar de texto | [GPTZero API](https://gptzero.me/api) |
| `GOOGLE_CLIENT_ID` | Login Google no backend | [Credenciais OAuth](https://console.cloud.google.com/apis/credentials) |
| `VITE_GOOGLE_CLIENT_ID` | Login Google na interface | Mesmo cliente OAuth acima |

O Fact Check Tools oferece busca de alegações verificadas pela API oficial do Google. Veja a [referência oficial](https://developers.google.com/fact-check/tools/api/reference/rest/). O Serper fornece resultados de busca e notícias em tempo real; a página oficial oferece uma cota inicial gratuita. [Saiba mais no Serper](https://serper.dev/).

### Aviso de segurança: chave Gemini antiga

Uma chave Gemini foi encontrada anteriormente em uma versão do arquivo de exemplo e foi removida. Considere-a comprometida: **revogue-a e crie outra** no Google AI Studio antes de publicar. Também limite cada chave ao serviço correspondente no painel do provedor e nunca a envie para o GitHub, Vercel ou navegador.

## Publicar: Railway + Vercel

### 1. API e banco no Railway

1. Crie um projeto no [Railway](https://railway.app/).
2. Adicione um serviço **PostgreSQL**.
3. Crie um serviço a partir deste repositório GitHub, usando `backend` como diretório-raiz.
4. O arquivo [`backend/railway.toml`](backend/railway.toml) já informa Docker, comando de início e health check.
5. Em **Variables** do serviço da API, configure:

   ```dotenv
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   GEMINI_API_KEY=chave_nova_do_google_ai_studio
   JWT_SECRET=valor_gerado_com_openssl
   HMAC_SECRET_KEY=outro_valor_gerado_com_openssl
   COOKIE_SECURE=true
   COOKIE_SAME_SITE=none
   CORS_ORIGINS=https://SEU-PROJETO.vercel.app
   CORS_ORIGIN_REGEX=https://.*\\.vercel\\.app
   ```

   Ajuste `Postgres` para o nome real do serviço PostgreSQL no projeto Railway. Não defina `PORT`: o Railway o fornece automaticamente.

6. Em **Networking**, gere o domínio público. Confirme `https://SEU-DOMINIO-RAILWAY/health` após o deploy.

O Railway oferece PostgreSQL gerenciado e expõe a URL de conexão do serviço; confira a [documentação de PostgreSQL](https://docs.railway.com/databases/postgresql) e de [variáveis](https://docs.railway.com/variables).

### 2. Interface no Vercel

1. Importe o mesmo repositório no [Vercel](https://vercel.com/new).
2. Defina `frontend` como **Root Directory**. O Vercel detecta Vite; o build é `npm run build` e a saída é `dist`.
3. Em **Environment Variables**, para Production e Preview, adicione:

   ```dotenv
   VITE_API_URL=https://SEU-DOMINIO-RAILWAY
   # Opcional, somente se login Google estiver habilitado
   VITE_GOOGLE_CLIENT_ID=seu_client_id.apps.googleusercontent.com
   ```

4. Publique. [`frontend/vercel.json`](frontend/vercel.json) já mantém as rotas React funcionando em recargas.

O guia oficial do Vercel para Vite está [aqui](https://vercel.com/docs/frameworks/frontend/vite), e o de variáveis de ambiente [aqui](https://vercel.com/docs/deployments/environments).

### Sessões entre Vercel e Railway

Com o domínio padrão `*.vercel.app` e `*.up.railway.app`, cookies são de terceiros. A configuração acima usa `SameSite=None; Secure`, mas navegadores podem restringir cookies de terceiros. Para produção, prefira domínios próprios sob o mesmo domínio-base, por exemplo:

```text
app.seudominio.com  → Vercel
api.seudominio.com  → Railway
```

Nesse caso use `CORS_ORIGINS=https://app.seudominio.com` e `COOKIE_SAME_SITE=lax`.

### Publicação pela linha de comando

Após entrar nas duas contas, os comandos equivalentes são:

```bash
# Interface
cd frontend
vercel login
vercel --prod

# API: crie/associe antes o projeto e o PostgreSQL no Railway
cd ../backend
railway login
railway up
```

Os comandos de login abrem uma autorização no navegador. A documentação oficial do Railway CLI está em [CLI](https://docs.railway.com/cli) e [Deploy](https://docs.railway.com/cli/deploy).

## Demonstração de áudio

As duas amostras da tela de demonstração foram feitas para explicar sinais de risco. O botão **Ouvir voz** usa a voz disponível no navegador, portanto há fala audível em vez de um som curto. O resultado delas é explicitamente marcado como educativo.

Para análise real, use **Enviar áudio** ou **Gravar minha voz**. A gravação preserva o tipo capturado pelo navegador (`webm` ou `ogg`) e encerra o microfone ao parar.

## Testes e qualidade

```bash
# Interface
cd frontend
npm run build

# API, dentro do ambiente Docker
cd ../backend
docker-compose -f ../docker-compose.yml exec -T backend python -m unittest discover -s tests -v
```

Última validação local: **21 testes aprovados**, 2 testes de integração com banco externo opcionalmente ignorados, compilação Vite concluída e fluxo visível de cadastro, análise, relatório, histórico, painel e demonstração exercitado no navegador.

## Estrutura resumida

```text
frontend/  React, páginas, componentes e cliente HTTP
backend/   FastAPI, pipeline de análise, autenticação e modelos
docs/      arquitetura e notas de integração
docker-compose.yml  desenvolvimento local completo
```

Detalhes da arquitetura: [`docs/general.md`](docs/general.md).
