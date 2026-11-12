# Migração para Render — 12/11/2026

Base: master 3547b4e. Nenhum código da aplicação foi alterado.

## Criar os serviços

No Render, entrar com a conta proprietária e autorizar acesso somente ao repositório
privado rodriguesz9/verify. New > Blueprint, selecionar a branch
deploy/render-free-20261112, caminho render.yaml. Conferir que backend e PostgreSQL
estão ambos em Free antes de criar. Não usar backend/render.yaml: configuração legada.

O Docker existente instala FFmpeg, Tesseract e ExifTool. O comando existente usa
PORT. /ready verifica a conexão com o banco sem consumir APIs de análise.
DATABASE_URL vem da conexão interna do PostgreSQL; o código já converte a URL
para o driver asyncpg. Não usar SQLite nem copiar DATABASE_URL local/Railway.

## Configuração privada

Preencher as chaves dos provedores pelo painel Environment, nunca no GitHub.
Copiar do ambiente privado os valores atuais de GEMINI_MODEL_NAME,
GEMINI_MEDIA_MODEL_NAME, GEMINI_REQUEST_TIMEOUT_SECONDS, OPENROUTER_MODEL,
OPENROUTER_ENABLED, AUDIO_TRANSCRIPTION_PROVIDER e demais ajustes necessários.
Para os serviços de mídia, copiar as credenciais existentes de Sightengine,
AssemblyAI e Hive quando utilizados. Copiar também seus limites e flags atuais;
não habilitar novas chamadas pagas apenas por migrar hospedagem.
Hugging Face pode continuar desabilitado. GOOGLE_CLIENT_ID é necessário se o
login Google for utilizado. Não copiar variáveis internas RAILWAY_* ou PORT.

JWT_SECRET e HMAC_SECRET_KEY são gerados independentemente. Novos segredos
invalidam sessões e assinaturas anteriores. Preservar os segredos antigos no
painel se a continuidade desses tokens for necessária; nunca expô-los em logs.

## Dados anteriores

Criar PostgreSQL novo não migra usuários/histórico. Se for necessário preservá-los,
obter backup pg_dump do Railway e restaurar no banco novo antes da troca pública.
Não tratar a criação automática das tabelas como importação. Se Railway não
permitir acesso ou não houver backup, a preservação continua pendente.
Conexões públicas estão inicialmente bloqueadas; restauração externa exige
liberação temporária e delimitada do IP de origem e posterior fechamento.

## Trocar a Vercel somente após validar

1. Confirmar deploy Live e GET /health e /ready com HTTP 200.
2. Confirmar preflight CORS com Origin https://verifybr.vercel.app.
3. Testar cadastro/login e persistência em uma conta de teste autorizada.
4. Atualizar VITE_API_URL na Vercel Production para a URL HTTPS .onrender.com,
   sem /api ao final; publicar novamente o mesmo frontend.
5. Conferir login/histórico e um fluxo de análise na interface, com orçamento
   específico autorizado para chamadas externas. Não declarar precisão apenas
   porque /ready respondeu.

Rollback: restaurar VITE_API_URL anterior e republicar; só restabelece serviço se
o backend Railway estiver ativo. Manter os dados antigos até confirmar a migração.

## Prazo do plano gratuito

O PostgreSQL Free expira 30 dias após sua criação. Registrar a data real no painel
e exportar backup antes do vencimento. Backend Free adormece após inatividade;
o primeiro acesso pode demorar. O plano gratuito não oferece disponibilidade
contínua garantida nem elimina limitações de cookies entre sites dos navegadores.

Documentação: https://render.com/docs/free e
https://render.com/docs/blueprint-spec.
