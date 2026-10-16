# Integração revisada da contribuição do Juan — 16/10/2026

Este registro descreve código e testes da integração. Não equivale a homologação de APIs reais nem comprova, sozinho, publicação do backend.

## Origem e crédito

Contribuição original: Juan Oliveira (`juanoliveira90`), commit `c97b9f41918aeacd0757e3cf148cddcf91cd4e66`, branch `fix/gemini-report-flow`.

Base atual preservada: `5b0f6adf4a18da1024695755fcb4bde3f974486d`. O merge de integração preserva o commit original como ancestral e registra o trabalho de adaptação separadamente, sem alterar autor/e-mail/histórico do Juan. Não substitui a versão atual pela árvore antiga nem falsifica autoria para superar restrições da hospedagem.

## Parte aproveitada e regressões descartadas

A ideia aproveitada é o caminho explícito para um relatório mais explicativo nas verificações de texto, lote e links. Ela foi adaptada à política documental atual, em vez de reativar o classificador histórico baseado na resposta livre de um modelo.

- `use_detailed_report=True` nas rotas textuais, incluindo texto extraído conferido pelo usuário.
- A decisão continua `text_report → corroborate_sources → apply_source_decision`.
- Gemini/OpenRouter continuam nas tarefas atuais de extração e comparação fundamentada, com seus limites/fallbacks existentes. Não há chamada adicional para gerar a explicação.
- `report_explanation.py` usa somente avaliações e evidências já aceitas; preserva negações, datas e valores. Não usa notícias relacionadas/snippets como prova, não promove evidência excluída nem converte falha de API em falsidade.
- A camada altera somente `plain_explanation` e o novo envelope versionado `report_explanation`, marcado `explanation_only`. Não muda veredito, índice, cobertura, avaliações, limitações ou política.
- Explica a decisão por trecho e cita, quando cabível, passagens completas de até 600 caracteres e duas referências por afirmação. Passagem maior não é cortada: a referência é mantida sem fabricar uma citação abreviada.
- A interface reconstrói o detalhamento a partir das avaliações canônicas. Não aceita opiniões/citações extras ou texto de erro só porque apareceram no novo envelope. Preserva o título e o escopo da conclusão; não expõe campos de configuração ao público.
- PDF/histórico continuam com o contrato e as evidências originais. A explicação acompanha a cópia assinada, sem refazer checagem ao exportar.
- Formatação preserva parágrafos e permite quebra de endereços longos para não estourar a largura.

## Testes

Suíte backend: **735 testes aprovados** no runner offline SQLite e **735 aprovados** com PostgreSQL descartável. Não somar as duas execuções como casos distintos. O banco PostgreSQL de testes é isolado e temporário; não é o banco do projeto.

Frontend: **20 verificações aprovadas** no resultado do runner, zero falhas/skips, e build de produção concluído. As novas verificações cobrem validação do envelope, citações inventadas/excluídas, negação/datas e renderização do detalhamento em resultado com título diagnóstico. O build final gerou 1.977 módulos; bundle principal `index-C3HLyQHl.js`.

Os testes novos incluem:

1. Notícia relacionada e opinião do modelo não aprovam uma alegação sem evidência.
2. Sustentação/refutação fundamentadas preservam todos os campos de decisão.
3. Falha de comparação não remove o contrato nem vaza erros privados.
4. Quota do Gemini na extração não apaga checagens editoriais válidas.
5. Texto, lote, link e texto conferido pedem detalhamento explicitamente.
6. Relatório detalhado mantém assinatura/exportação PDF.
7. Evidência excluída, fonte enviada, protocolo inseguro e citação inventada não entram na explicação.
8. Afirmação avaliada por checagem não é apresentada como citação literal de corpo de artigo.
9. Negação/data não são removidas; fonte longa não vira trecho cortado.
10. Avisos de golpe, conteúdo misto, imutabilidade e limite de cinco trechos são preservados.

Controles pela interface usam backend local descartável, sem `.env` privado e com provedores bloqueados. Respostas documentais são **simuladas**, incluindo casos corroborado/refutado/inconclusivo; não constituem revalidação do Gemini ou comprovação de precisão para notícias reais. Não colocar esse harness em produção.

## Publicação e bloqueio do Railway

Projeto Vercel confirmado: `robert-rodrigues-projects/verify`, Root Directory `frontend`, framework Vite. O acesso local do titular foi confirmado. A release deve apontar ao commit de integração testado; preservar as regras de permissão e a visibilidade privada do repositório.

Em 16/10, as consultas de inventário e estado do Railway mostraram `alert-peace/production`, serviços `verify` e `Postgres` **offline**, sem rollout pendente. O volume `postgres-volume` continua listado e anexado ao Postgres. Essa listagem não comprova integridade/restauração do banco.

O serviço backend segue o repositório `rodriguesz9/verify@master`. Publicar a master pode disparar deploy automático, mas isso não renova hospedagem nem prova que o backend esteja no ar. Não foi autorizado contratar/renovar plano ou recriar banco/volume como parte da integração.

Após resolver a disponibilidade da conta, usar o projeto/serviço/banco existentes. Seguir [reativação segura](REATIVAR-RAILWAY-2026-10-13.md); conferir commit, Dockerfile/configuração da revisão, `/ready`, histórico, texto/link com referências reais e PDF antes de declarar recuperação. Não rodar testes destrutivos PostgreSQL contra produção. Não copiar `.env` de desenvolvimento inteiro ou sobrescrever segredos válidos.

Não há nova API/chave obrigatória para esta melhoria. `SERPERAPI_KEY`, Gemini e OpenRouter continuam sujeitos à configuração, quota e acesso reais; modelos não se tornam fontes factuais independentes. Não foram consumidos créditos Hive ou contratados serviços nesta adaptação.
