# Entrega candidata — 08/10/2026

Branch de entrega: `entrega/banca-2026-10-08`, baseada em `5db970da8f8a109472050ed96e3ab77d20e7f5e7`. O SHA final deve ser consultado no GitHub/Git; este documento não afirma que a branch foi promovida a `master`, que um preview foi aprovado ou que Vercel/Railway receberam esta revisão.

## O que foi preparado

- [Status detalhado das verificações](STATUS-VERIFICACOES-2026-10-08.md): última resposta real, limitações, configuração adicional além das chaves e links oficiais.
- [Roteiro básico de banca](ROTEIRO-BANCA.md): apresentação de 8–12 minutos, exemplos existentes com procedência, falas sugeridas e contingência sem simular sucesso.
- Código, testes e documentação acumulados na revisão separada. O repositório original em `/mnt/externo/IMPORTANTES/mostra/verify` foi preservado, com suas alterações locais intactas.
- `.gitignore` protege também variantes privadas `.env.*`, mantendo o template `.env.example`. Isso não remove retroativamente um arquivo já rastreado; o `frontend/.env.production` existente contém configuração pública e não deve receber segredos.

## Correção de renovação/troca de sessão

`frontend/src/services/api.js` captura conta/época de forma síncrona antes do despacho. Em HTTP 401, somente pedidos de leitura podem repetir, se o contexto não mudou antes/depois da renovação. POST/FormData e outras escritas não repetem automaticamente: a interface recebe instrução de reenvio deliberado.

Falha de refresh antigo não encerra conta nova; logout antigo não redireciona outra sessão. Login/cadastro/Google invalidam o contexto privado e avisam outras abas **antes** de alterar cookies. Startup sem conta inicializada continua podendo consultar `/auth/me` e renovar uma vez.

**Limites:** não desfaz pedidos já enviados, não revoga cookies/tokens no servidor, não resolve `Set-Cookie` tardio entre abas, nem adiciona guarda genérica de toda resposta bem-sucedida de autenticação. Home já descarta respostas de análise de contextos anteriores. Homologação de sessões/banco/browser e revogação ainda são gates; não anunciar isolamento completo de todas as corridas.

Controles locais em [sessionRefresh.test.js](../frontend/tests/sessionRefresh.test.js): 18 casos, com adapter sem rede; A→B, A→B→A, contexto antigo, POST/FormData, métodos de escrita, inicialização, falha antiga, login/cadastro/Google e logout. Não houve envio de credenciais ou arquivos reais nesses testes.

## Testes reexecutados em 08/10

| Controle | Resultado | Alcance |
| --- | --- | --- |
| Backend | 424 testes, 9,841 s; zero falhas/skips | SQLite descartável, sem rede/chaves; transporte real bloqueado |
| Frontend | 142 testes, 594,753 ms; zero falhas/skips | Inclui 18 novos controles de sessão; não homologa fornecedores |
| Build frontend | 1.976 módulos, 3,32 s | Bundle de produção compilado, não implantação |
| Valores privados em arquivos candidatos | Zero correspondências no scan de 298 arquivos antes da consolidação documental | Valores longos do `.env` privado comparados sem imprimir secrets; não é auditoria de todo histórico Git |

A suíte anterior de 424 foi executada também no modo PostgreSQL descartável em 07/10, mas **somente três testes têm integração real PostgreSQL**. Não somar execuções nem afirmar validação integral da aplicação nesse banco.

## Produção: fronteira ainda não comprovada

- Landing pública `https://verifybr.vercel.app` respondeu HTTP 200; seu bundle apontou para `https://verify-production-ead7.up.railway.app`.
- As consultas read-only ao backend não completaram neste ambiente. `/health` apresentou timeout DNS em 5 s, HTTP `000`, não uma resposta HTTP 5xx. Não se conclui indisponibilidade global do Railway.
- Nenhuma análise externa de conteúdo foi feita em 08/10 nesta entrega. Evidências Gemini/OR/detectores permanecem datadas, não são novos testes reais de todas as APIs.
- Push pode disparar CI/preview conforme a configuração do repositório. Conferir o SHA, os checks e a configuração remota; push não comprova deploy nem orçamento seguro para tráfego público.

## O que precisa fechar antes da banca

1. Confirmar frontend/backend correspondentes ao candidato, conexão, banco e ferramentas na imagem Docker final.
2. Aplicar configuração necessária no Railway sem copiar SQLite, secrets de teste ou habilitações pagas. Ver [guia atual](STATUS-VERIFICACOES-2026-10-08.md#4-configuração-segura-por-serviço).
3. Ensaiar os exemplos do roteiro pela interface da versão apresentada; registrar saídas reais e preservar negações, datas e valores. Não garantir um par factual verdadeiro/falso sem as checagens correspondentes realmente recuperadas.
4. Confirmar CI remoto, PDF salvo/aberto, Modo Fácil/mobile/zoom/teclado e isolamento de sessão na homologação.
5. Receber fala/vídeos humanos autorizados, avaliar erros e abstenções por modalidade. Arquivos sintéticos não substituem essa etapa.
6. Manter Hive pago e modelos não autorizados pausados. Indisponibilidade vira cobertura insuficiente, não veredito inventado.

Para lançamento aberto, ainda concluir retenção/exclusão, backup/restore, revogação de sessões, migrações e quotas compartilhadas. O [plano até 11/10](ENTREGA-ATE-11-OUTUBRO.md) mantém os critérios de aceite; esta branch é candidata, não certificado de “100% pronto”.
