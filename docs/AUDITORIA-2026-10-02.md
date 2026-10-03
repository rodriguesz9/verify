# Auditoria do Verify — 2 de outubro de 2026

## Conclusão

A versão publicada responde e tem uma interface utilizável, mas não deve ser apresentada como um verificador forense confiável: houve transcrições/vereditos de áudio dependentes do nome do arquivo, aceitação de mídia inválida e falhas HTTP 500 em texto e WhatsApp.

A revisão local corrige problemas reproduzidos e torna explícita a falta de evidência. **Não foi feito novo deploy nem push.** Precisão de detecção, bot real de WhatsApp e todas as configurações de produção não foram certificados.

## Versão inspecionada

- Frontend: https://verifybr.vercel.app
- API: https://verify-production-ead7.up.railway.app
- Repositório: https://github.com/rodriguesz9/verify
- Commit observado: `8500689814d295a3ad23d7dbda27b57c859720fa`, branch `master`.
- Railway: deploy marcado como bem-sucedido, mas usando Railpack na configuração consultada. O Dockerfile local não prova presença de FFmpeg no serviço publicado.
- Alterações locais preexistentes foram preservadas; o diff final também contém mudanças que já pertenciam ao usuário.

## Principais achados e correções

| Problema observado | Risco | Revisão local |
| --- | --- | --- |
| O mesmo MP3 recebeu `autentica`, 0,88, com um nome e `sintetica`, 0,96, ao ser renomeado `fake_clonado.mp3`; as transcrições também mudaram | Inventar evidência e acusar clonagem sem analisar a voz | Removidos resultados por nome e transcrição de fallback inventada; discurso suspeito é separado da origem da voz |
| Arquivo vazio e PNG corrompido recebiam HTTP 200 | Tratar bytes inválidos como mídia analisada, consumir APIs desnecessariamente | Validação de assinatura, decodificação, família MIME, tamanho, resolução e duração antes das camadas externas |
| Texto e simulador de WhatsApp retornaram HTTP 500 | Fluxos principais indisponíveis apesar de testes antigos passarem | Corrigido uso de `asyncio` sem import em `gptzero_client`; adicionado teste do fluxo real sem mocks de provedores |
| Substring Hive incluía `not_ai_generated` e classes negativas de deepfake | Falso positivo mesmo quando o fornecedor indicava mídia não gerada | Classes exatas e scores válidos; ausência de classe não vira zero; parser legado unificado |
| Sightengine retornava sucesso, mas o código lia campos inexistentes | Descartar evidência válida e ocultar a causa | Campos `type.ai_generated` e `type.deepfake`, conforme documentação; credenciais no formulário, não na URL |
| Vídeo não tinha inspeção real de quadros no fluxo de upload | Resultado baseado em texto/nome, sem examinar a mídia | Três quadros extraídos por FFmpeg, timestamps e limites de cobertura explícitos |
| Fallback/ausência de detector podiam parecer análise concluída; concordância de LLM aumentava score | Falsa certeza | Política conservadora compartilhada, cobertura por camada, confiança não calibrada não apresentada como precisão |
| Marcadores C2PA, EXIF de câmera e datas de arquivo podiam parecer provas | Metadados forjados legitimarem mídia | Separação entre marcador, assinatura/trust e evidência; registro SHA-256 não recebe selo de autenticidade |
| Cache global reutilizava resultados sem versão/isolamento de usuário | Propagar veredito antigo, perder histórico e expor nome de outro envio | Upload deixa de reutilizar cache legado não versionado; cada usuário registra seu resultado |
| Lotes usavam gravações concorrentes na mesma sessão e não contabilizavam todos os itens | Erros de banco e evasão de quota | Análise concorrente, persistência serial, lote limitado e quota por item |
| Hooks do relatório após retorno condicional | Tela de resultado podia quebrar | Hooks movidos para ordem estável; upload real conferido no navegador |
| Promessas de privacidade, exclusão, origem de voz e autenticidade excediam a implementação | Usuário tomar decisão com garantia inexistente | Textos, badges, compartilhamento e README alinhados ao comportamento real; link do rodapé corrigido |

O limiar experimental de concordância não é uma solução definitiva para falsos positivos. Detectores podem compartilhar vieses; é necessária calibração com dados rotulados.

## Testes e evidências

### Controles de produção

[Resultado HTTP completo](audit-production-2026-10-02.json): 14 controles, incluindo um teste comportamental de invariância do nome. Quatro controles HTTP falharam: arquivo vazio, arquivo corrompido, texto e WhatsApp. O controle de invariância do áudio também falhou.

Saúde, bloqueio de endereço privado e restrição do histórico anônimo responderam como esperado. PDF válido foi retornado. O HTTP 200 do lote não demonstrou sucesso por item naquele registro; essa limitação foi corrigida no coletor local.

Não foram criadas contas, apagados dados ou registrados selos no serviço público.

### Testes locais

- Suíte automatizada final: **62 testes passaram, 18 subtestes passaram, nenhum teste ignorado**, em 3,59 segundos; cinco avisos de APIs depreciadas. Inclui regressões de mídia, provedores, C2PA, autenticação, banco e texto.
- Compilação Vite: concluída sem erros.
- [25 controles de ponta a ponta](audit-local-2026-10-02.json): todos passaram nos critérios registrados, usando banco SQLite temporário e APIs externas desabilitadas.
- Fluxos cobertos: cadastro/login/perfil/refresh/logout, histórico persistido, lote autenticado, imagem, vídeo, áudio renomeado, texto, simulador WhatsApp, PDF, registro/consulta de integridade e bloqueio de URL privada.
- Navegador: imagem e vídeo efetivamente enviados pela interface; relatório e áudio demonstrativo conferidos, sem erros de console nesses fluxos. Resultado e landing page sem rolagem horizontal em viewport 390 × 844. Não é uma auditoria completa WCAG ou de todos os aparelhos.
- [Evidência visual móvel](mobile-video-result.jpg).

Os testes usam Pillow/FFmpeg reais para validar mídia e extrair quadros. O banco de integração é real e descartável, mas não replica todos os comportamentos do PostgreSQL/Railway. C2PA foi coberto por testes de parser; a verificação criptográfica com c2patool e âncoras reais ainda precisa de prova end-to-end.

### Mídias usadas

Uma imagem inteiramente gerada por IA de pessoa fictícia, um MP4 de três segundos derivado dessa imagem, gravação WebM de silêncio sem duração no cabeçalho, imagens de controle decodificáveis, arquivos vazios/corrompidos e o mesmo MP3 público da demonstração com dois nomes.

O MP4 é uma sequência estática sintética, **não um face-swap ou vídeo gerado por um modelo temporal**. Os MP3 existentes não tiveram origem humana/sintética certificada. Não foram usados documentos bancários reais nem mídia privada. [Origem, prompt e reprodução](../backend/tests/fixtures/README.md).

### Provedores reais

[Resultado seguro, sem credenciais](audit-providers-2026-10-02.json), com uma imagem fictícia e uma tentativa limitada de fala:

| Camada | Resposta observada após os ajustes |
| --- | --- |
| Sightengine | Sucesso, score de IA 0,99 para a imagem sintética |
| Hugging Face | HTTP 400; verificar endpoint/payload, disponibilidade do modelo e permissões do provedor |
| Hive | HTTP 403; verificar acesso ao projeto correto e compatibilidade da chave v2/v3 |
| Gemini OCR/visão | HTTP 429; verificar quota/limites e modelo habilitado |
| Gemini TTS | Falha explícita; nenhuma fala foi produzida nesse teste, nenhum beep de sucesso foi fabricado |

O resultado geral permaneceu inconclusivo porque não havia cobertura suficiente. Esse é o comportamento seguro esperado, **não uma demonstração de que todos os detectores funcionam**. A configuração local e a da Railway podem ter credenciais/limites diferentes; os nomes das variáveis configuradas na nuvem não provam que as chaves sejam válidas.

## Prioridades restantes

Atualização posterior desta revisão: autenticação/base64 do webhook, limites locais, consulta com DNS fixado e relatório detalhado foram implementados e testados na cópia revisada. Veja [continuação](CONTINUACAO-2026-10-02.md) para os resultados novos e limitações restantes. Os itens abaixo descrevem a lista de prioridades registrada na auditoria inicial; não afirmam que os riscos já estejam corrigidos no deploy.

### Antes de apresentar a versão como pronta para produção

1. Revisar e publicar a revisão; repetir os controles no deploy efetivamente ativo. Confirmar FFmpeg/ffprobe e migrações do banco.
2. Restaurar acesso aos provedores, criar teste de saúde por camada com custo limitado e alertar quando a cobertura cair. Não habilitar retries ilimitados.
3. Autenticar o webhook; limitar convidados, lotes, geração de fala e downloads; definir orçamento de chamadas e concorrência. O limitador existente não demonstra limite efetivo em todos os endpoints públicos.
4. Reforçar proteção SSRF contra DNS rebinding e limitar bytes/tempo total das páginas consultadas. O bloqueio de localhost foi testado, mas não é prova de proteção completa.
5. Revisar o fluxo Evolution: base64 não é URL de download, mídias WhatsApp podem precisar de descriptografia, e retornar JSON não equivale a enviar mensagem pelo gateway. Provisionamento do banco do gateway, autenticação, recebimento e resposta no número real não foram testados.
6. Implementar política de retenção, canal de contato e exclusão de conta/histórico. Hash simples de telefone é pseudonimização, não anonimização garantida; não evita descoberta por tentativa de números.
7. Testar cookies de produção e login Google no navegador real. Domínios Vercel/Railway distintos podem ter restrições de cookies de terceiros.

### Para melhorar a qualidade das verificações

1. Montar conjunto rotulado/licenciado com fotos reais de celular, JPEG recomprimido/WhatsApp, HDR, filtros, arte, prints e gerações de vários modelos. Separar calibração e avaliação; não ajustar limiares nos mesmos exemplos usados para medir acerto.
2. Medir falso positivo, falso negativo e cobertura inconclusiva por modalidade. Evitar uma única “precisão” que esconda limitações.
3. Usar deepfakes de vídeo de procedência conhecida: face-swap, alteração de expressão, voz clonada e lip-sync, incluindo controles genuínos. Três frames são apenas triagem, não análise temporal.
4. Se ampliar amostragem, mostrar quantidade, timestamps e modelo aplicado; manter limites de custo. Para vídeos longos, adotar jobs assíncronos com progresso verdadeiro e cancelamento.
5. Diferenciar quatro perguntas: geração por IA, edição, proveniência e veracidade/contexto. Imagem gerada pode ilustrar uma informação verdadeira; foto real pode circular com legenda falsa.
6. Registrar hash SHA-256, versão da política/modelos e estado das camadas para reprodução. Se voltar a usar cache, incluir versão e contexto e manter nomes/histórico isolados por usuário.
7. Para busca reversa, não publicar uploads privados automaticamente. Data de snapshot Wayback não é primeira publicação nem prova de identidade da imagem. TinEye/Lens precisam de contrato e validação real próprios.
8. Testar acessibilidade com teclado/leitor de tela, contraste, zoom e dispositivos reais. O modo fácil e o layout móvel ajudam, mas não substituem essa auditoria.

## Fontes técnicas usadas

- [Sightengine: campos de IA](https://sightengine.com/docs/ai-generated-image-detection) e [deepfake](https://sightengine.com/docs/deepfake-detection).
- [Hive: autenticação por projeto](https://docs.thehive.ai/reference/authentication), [áudio](https://docs.thehive.ai/reference/ai-generated-audio-detection-1) e [classes de deepfake](https://docs.thehive.ai/reference/deepfake-detection-1).
- [Hugging Face: Inference Providers](https://huggingface.co/docs/inference-providers/index).
- [Gemini: modelos](https://ai.google.dev/gemini-api/docs/models), [chaves](https://ai.google.dev/gemini-api/docs/api-key) e [geração de fala](https://ai.google.dev/gemini-api/docs/speech-generation).
- [c2patool: validação e trust](https://github.com/contentauth/c2patool/blob/main/docs/usage.md).
- [SerpApi: requisitos do Google Lens](https://serpapi.com/google-lens-api).

Os links para obter chaves e executar a aplicação estão no [README](../README.md). Não copie chaves para relatórios, screenshots ou variáveis públicas do frontend.

## Ocorrência no disco local

Durante a auditoria, o disco USB desconectou/reconectou. A montagem antiga `/mnt/externo` passou a retornar erros de entrada/saída; o projeto reapareceu em `/media/robert/HDExterno/IMPORTANTES/mostra/verify` e as alterações anteriores continuaram presentes.

Nenhum reparo, formatação, desmontagem ou publicação automática foi feito. O projeto foi copiado para uma pasta interna de recuperação, sem `.env` reais, para concluir os testes. A entrega preserva uma cópia revisada; confira o caminho informado na resposta antes de continuar o desenvolvimento. As alterações concluídas nessa cópia não foram sincronizadas de volta para o disco externo.
