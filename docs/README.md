# Documentação do Verify

Atualizada em 08/10/2026. Produção confirmada no SHA `ef9655ff9d3fa4d350d149cc5b48e44b3611b729`; filtro lexical de notícias e aviso de fragmentos OCR são uma revisão posterior, no checkpoint antes de sua publicação. Documentos anteriores preservam seu estado histórico e não comprovam publicação de cada mudança posterior.

## Comece aqui

- [Publicação e controles reais de 08/10](PUBLICACAO-2026-10-08.md): SHA/deploys confirmados, texto/imagens/voz sintética pela interface, PDF/200 sem nova análise, patch local de contexto e fronteiras ainda pendentes.
- [Correções e diagnóstico de produção de 08/10](CORRECOES-PRODUCAO-2026-10-08.md): Railway online confirmado, versão publicada, 422 de texto/500 de banco separados, novo controle Gemini, interface simples e checkpoints atuais.
- [Ativar Hive e compreender voz/OCR](ATIVACAO-HIVE-VOZ-2026-10-08.md): uso do saldo autorizado, limites por processo, Secret Key v3, acesso Sightengine e HF desligado sem contratação.
- [Status de todas as verificações](STATUS-VERIFICACOES-2026-10-08.md): o que respondeu, o que falta, por que chave não basta e como configurar com links oficiais.
- [Roteiro básico da banca](ROTEIRO-BANCA.md): 8–12 minutos, textos, controles de mídia, falas sugeridas e plano de falha sem resultados fabricados.
- [Entrega candidata de 08/10](ENTREGA-BANCA-2026-10-08.md): testes atuais, proteção contra reenvio/troca de sessão, publicação Git e limites de homologação.
- [Fechamento até 11/10](ENTREGA-ATE-11-OUTUBRO.md): novo prazo desta semana, prioridades, gates e dependências reais. Antecede o calendário original de 14 dias.
- [Resultados de 07/10](FECHAMENTO-2026-10-07.md): correções locais, comparação Gemini, OCR local pela interface e pendências de publicação.
- [Retomada de transcrição de 07/10](TRANSCRICAO-PENDENTE-2026-10-07.md): 424 backend/124 frontend, criação única no ensaio simulado, isolamento, estados claros e limites por processo/janela.
- [Manual completo do projeto](DOCUMENTACAO-COMPLETA.md): produto, arquitetura, fluxos, políticas, API, banco, instalação, todas as variáveis, provedores, deploy, segurança, testes, operação e entrega.
- [Plano detalhado de 14 dias](PLANO-ENTREGA-14-DIAS.md): 04–17/10/2026, tarefas rastreáveis, responsáveis, dependências, critérios de aceite, horas e pacote adicional para público.
- [README do repositório](../README.md): visão rápida e comandos de entrada.
- [Arquitetura resumida](general.md): orientação para trabalhar no código.

## Por objetivo

| Preciso… | Ler primeiro |
| --- | --- |
| Entender o que o produto promete e não promete | [Produto](DOCUMENTACAO-COMPLETA.md#produto), [situação comprovada](DOCUMENTACAO-COMPLETA.md#situacao) |
| Instalar, rodar em Docker e configurar env | [Instalação](DOCUMENTACAO-COMPLETA.md#instalacao), [inventário de variáveis](DOCUMENTACAO-COMPLETA.md#ambiente) |
| Obter e ativar APIs sem novas contratações | [Provedores](DOCUMENTACAO-COMPLETA.md#provedores) |
| Publicar no Railway/Vercel | [Deploy](DOCUMENTACAO-COMPLETA.md#deploy), [checklist de entrega](DOCUMENTACAO-COMPLETA.md#entrega) |
| Entender uma conclusão ou score | [Políticas](DOCUMENTACAO-COMPLETA.md#politicas), [contrato do relatório](DOCUMENTACAO-COMPLETA.md#relatorios) |
| Trabalhar na API/banco/sessão | [API](DOCUMENTACAO-COMPLETA.md#api), [banco](DOCUMENTACAO-COMPLETA.md#banco), [autenticação](DOCUMENTACAO-COMPLETA.md#autenticacao) |
| Saber se está pronto e o que falta | [Plano](PLANO-ENTREGA-14-DIAS.md), [testes](DOCUMENTACAO-COMPLETA.md#testes), [matriz](MATRIZ-VALIDACAO-30-CASOS.md) |
| Preparar operação, privacidade e apresentação | [Segurança](DOCUMENTACAO-COMPLETA.md#seguranca), [operação](DOCUMENTACAO-COMPLETA.md#operacao), [roteiro](DOCUMENTACAO-COMPLETA.md#contribuicao) |

## Evidências por etapa — preservar como histórico

| Registro | Assunto e alcance |
| --- | --- |
| [Publicação e controles de 08/10](PUBLICACAO-2026-10-08.md) | Vercel READY/Railway SUCCESS no SHA ef9655ff; texto, duas imagens e voz sintética pela interface pública; PDF/200, salvamento não confirmado. Revisão posterior antes de publicar: 492 backend, 156 frontend e build; fala humana/vídeo/benchmark continuam sem homologação ampla |
| [Diagnóstico complementar de 08/10](CORRECOES-PRODUCAO-2026-10-08.md) | Checkpoint anterior à promoção: produção online no SHA antigo; 482 backend e mesmo runner no modo PG, com quatro integrações reais; 155 frontend; seis chamadas Gemini, duas Hive, UI Lite inconclusiva corretamente. A publicação posterior tem registro separado |
| [Entrega candidata de 08/10](ENTREGA-BANCA-2026-10-08.md) | Registro anterior 424/142 e proteção de refresh; CI desse commit passou posteriormente; não confundir com implantação da revisão seguinte |
| [Retomada de transcrição](TRANSCRICAO-PENDENTE-2026-10-07.md) | Suíte final 424/124; operação simulada sem API real; não homologa fidelidade nem implantação |
| [Fechamento de 07/10](FECHAMENTO-2026-10-07.md) | Etapa anterior desta data: correções, Gemini e APIs por modalidade; sem nova publicação |
| [Auditoria de 02/10](AUDITORIA-2026-10-02.md), [continuação](CONTINUACAO-2026-10-02.md) | Achados de versões anteriores, não estado final atual |
| [Verificações de 03/10](VERIFICACOES-2026-10-03.md) | Políticas, testes e separação de dimensões |
| [Multimodal de 03/10](MULTIMODAL-2026-10-03.md) | OCR/transcrição/detectores; falhas e limites reais |
| [Primeira etapa](PRIMEIRA-ETAPA-2026-10-03.md) | Histórico, privacidade no navegador, PDF e controles locais |
| [Validação pela interface](VALIDACAO-INTERFACE-2026-10-04.md) | Caminhos UI e chamadas reais gratuitas limitadas |
| [Conferência humana](CONFERENCIA-TEXTO-2026-10-04.md) | Original/editor/checagem textual vinculada |
| [PDF, prontidão e CI](PDF-READINESS-CI-2026-10-04.md) | Exportação, banco e runner/workflow |
| [Controles de extração](CONTROLES-EXTRACAO-2026-10-04.md) | HTML/OCR degradado/vídeo; comparação estrita 18/19 |
| [PDF de texto/link](PDF-TEXTO-LINK-2026-10-04.md) | Última suíte: 274 backend/84 frontend; salvamento final do browser pendente |
| [Consolidação documental](DOCUMENTACAO-VALIDACAO-2026-10-04.md) | Conferência de links, variáveis, rotas e sintaxe; não nova suíte/deploy |
| [Matriz de 30 casos](MATRIZ-VALIDACAO-30-CASOS.md) | 22 parcialmente executados/8 pendentes; não 22 acertos |
| [Fixtures](../backend/tests/fixtures/README.md) | Origem declarada dos controles e limites |

Arquivos JSON junto a esses registros guardam observações sanitizadas. Quantidades de testes variam por etapa: não somar execuções antigas ou tratar um teste parcialmente feito como classificação correta.

## Guias anteriores e decisão técnica

- [APIs sem custo](APIS-SEM-CUSTO.md), [ativar detectores](ATIVAR-DETECTORES.md), [integrações](INTEGRACOES-GRATUITAS.md).
- [Configuração de produção anterior](CONFIGURACAO-PRODUCAO.md), [interface/Modo Fácil](INTERFACE-MODO-FACIL.md).
- [ADR: notícias Serper](adr/serper_news.md).

Em caso de divergência entre guia antigo e manual consolidado, conferir o código e usar o manual atual para configurar. Não copiar valores privados de capturas ou reativar fornecedor pago por instrução histórica.
