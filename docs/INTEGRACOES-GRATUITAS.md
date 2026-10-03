# Integrações e testes — 3 de outubro de 2026

O código das integrações foi atualizado. **Isso não significa que todas as APIs estejam operacionais em produção ou que os vereditos tenham precisão de 100%.** Credencial presente, HTTP 200 e testes com respostas simuladas são coisas diferentes de acesso real e avaliação de precisão.

Atualização mais recente: [OCR local, proteção de silêncio, transcrição portuguesa e HF experimental](MULTIMODAL-2026-10-03.md). As observações abaixo distinguem testes desta revisão de controles anteriores.

## Resultado observado

| Serviço/camada | Teste real desta etapa | Situação e limite |
| --- | --- | --- |
| Gemini — texto | Uma resposta JSON válida com `gemini-3.7-flash` | Funcionou no controle mínimo. Foram observados timeouts em tentativas anteriores. Não é validação de todas as análises. |
| OCR — local/Gemini | Tesseract no Docker sem internet: 4/4 linhas; Gemini `gemini-3.1-flash-lite`: 4/4 linhas | Leitura funcional nesses controles; Tesseract primeiro, sem chave. Não certifica origem ou precisão geral. |
| Gemini — transcrição | Novo controle português ainda atingiu 20 s | AssemblyAI passa a preferido. Quase silêncio é bloqueado localmente para impedir palavras inventadas nesse controle. |
| OpenRouter | Resposta válida no controle público após corrigir prazo e formato | Modelo efetivo `nvidia/nemotron-3-super-120b-a12b:free`. Extração auxiliar de texto funcionou com preço máximo zero/JSON Schema. OCR gratuito ainda não foi validado ao vivo; a chave local continua ausente. |
| Hive v3 — imagem | Uma chamada com a imagem sintética de controle | Resposta válida: sinal de geração por IA próximo de 1; sinal de deepfake próximo de 0. Não valida reconhecimento de face-swap nem sensibilidade geral. |
| Hive v3 — áudio/vídeo | Não executado | Sem gasto adicional autorizado. As duas saídas visuais usam a mesma chamada, não dois votos independentes. |
| Hugging Face | Endpoint compartilhado respondeu; falso negativo no controle sintético | Integração experimental, sem voto no veredito. Não houve contratação de servidor/GPU pago. |
| Google Fact Check | Consulta pública concluída, sem checagens correspondentes ao exemplo Pix | Sem correspondência não significa verdadeiro/falso. Não valida resultados para outras afirmações. |
| Serper | Notícias relacionadas retornadas no relatório público do exemplo Pix | Funcionou nesse controle; notícia relacionada não é automaticamente prova sobre a mensagem. |
| Sightengine imagem | Sinal IA 0,99 na imagem sintética; 0,001 no gráfico impresso | Dois controles, não benchmark de fotos humanas, face-swap ou vídeo. |
| AssemblyAI | Controle português novo: 16/16 palavras, WER 0 nesse exemplo | Transcrição funcionou; não é detector de clonagem/identidade. |
| SerpAPI | Nova chave autenticou (Account API HTTP 200) | Chave substituída pelo usuário; busca Lens completa não revalidada. |

O Hive foi testado **uma única vez**, dentro da autorização de US$ 0,01. O custo nominal estimado foi **US$ 0,006**, pela tarifa exibida no playground; não houve conferência do lançamento no extrato. Não houve recarga, cartão novo, chamada de áudio/vídeo ou repetição automática. `HIVE_V3_MEDIA_TYPES` fica vazio em produção: a autorização de um teste não autoriza gasto contínuo com visitantes.

## Proteção contra cobrança no OpenRouter

Configuração aplicada ao serviço Railway, sem alterar segredos ou banco:

```dotenv
OPENROUTER_ENABLED=true
OPENROUTER_MODEL=openrouter/free
OPENROUTER_FALLBACK_MODELS=
OPENROUTER_DAILY_LIMIT=40
HIVE_API_VERSION=v3
HIVE_V3_MEDIA_TYPES=
SIGHTENGINE_AUDIO_ENABLED=false
GEMINI_MODEL_NAME=gemini-3.7-flash
VIDEO_MAX_FRAMES=3
LOCAL_OCR_ENABLED=true
GEMINI_MEDIA_MODEL_NAME=gemini-3.1-flash-lite
AUDIO_TRANSCRIPTION_PROVIDER=assemblyai
HUGGINGFACE_IMAGE_API_URL=https://router.huggingface.co/hf-inference/models/Ateeqq/ai-vs-human-image-detector
HUGGINGFACE_AI_LABEL=ai
```

- Somente `openrouter/free` ou variantes específicas `provedor/modelo:free` são aceitas. `openrouter/auto` e `openrouter/auto:free` são bloqueados.
- Cada requisição limita a zero os preços de entrada, saída, requisição e imagem. Não existe fallback pago nem recarga automática.
- Limite preventivo de 40 tentativas/dia UTC e 10/minuto **por processo**; tentativas com erro contam. Reinícios e múltiplas réplicas não compartilham esse contador. A quota da conta OpenRouter continua sendo o limite externo efetivo.
- HTTP 402/429 interrompe a tentativa e pausa o provedor; não tenta outro modelo para contornar quota.
- O modelo efetivamente escolhido é registrado. No free router ele pode variar.
- A seleção prioriza menor latência sem liberar provedores pagos. O limite inicial de 12 s interrompeu a extração no teste público e foi ampliado de forma limitada; isso não garante disponibilidade dos modelos gratuitos.
- A requisição exige suporte aos parâmetros e usa JSON Schema com campos explícitos. Localmente, aceita somente JSON completo ou um único envelope Markdown completo; não tenta executar/reparar código, extrair objetos de prosa arbitrária ou comprar outra resposta. Saída inválida registra categoria e modelo, sem vazar resposta bruta.
- A IA extrai trechos literais para pesquisa ou lê texto de imagens. Sua opinião não define verdade/falsidade, identidade, clonagem de voz ou origem da mídia.
- Provedores gratuitos podem ter políticas próprias de retenção/uso de dados. Evite conteúdo pessoal sensível e consulte a página de privacidade.

## O que falta configurar ou confirmar

1. **OpenRouter:** o teste público confirmou a chave atual do Railway para extração de texto; não é necessário recriá-la por causa desse teste. Para reproduzir localmente, preencha `OPENROUTER_API_KEY` no `.env` privado do backend com sua chave de [Settings → Keys](https://openrouter.ai/settings/keys). Mantenha-a somente no backend/Railway; não cole no chat nem use variável `VITE_` para segredos.
2. **Hive:** a chave v3 é a **Secret Key**, não o Access Key ID da captura. Use `HIVE_V3_API_KEY` ou a `HIVE_API_KEY` existente com `HIVE_API_VERSION=v3`. Só preencha `HIVE_V3_MEDIA_TYPES=image,audio` se decidir autorizar o consumo contínuo. Isso é pago; vídeo também consome análises de quadros. A plataforma não dispõe aqui de um teto financeiro global do Hive.
3. **Hugging Face:** endpoint compartilhado testado acima, classe `ai`; responde mas mostrou falso negativo. Não habilita voto nem exige GPU paga. Créditos finitos e resultados experimentais explícitos; veja [guia atual](MULTIMODAL-2026-10-03.md).
4. **Gemini/AssemblyAI:** OCR local primeiro e modelo multimodal separado corrigem leitura no controle. Transcrição Gemini ainda atingiu o prazo; AssemblyAI `universal-2` foi testado e escolhido primeiro. Não ative faturamento para ocultar indisponibilidade; confira a [quota do projeto](https://aistudio.google.com/usage).
5. **SerpAPI:** usuário confirmou revogação/substituição no `.env` privado e Railway. Nova credencial local autenticou HTTP 200, sem consumir pesquisa. Não é necessário revogá-la novamente por causa desse teste; não publicar chaves em capturas.
6. **Demais serviços:** usuário confirmou créditos gratuitos e ausência de cobrança automática em Sightengine/AssemblyAI. Os testes ficaram nesse escopo. Não habilite `SIGHTENGINE_AUDIO_ENABLED` só porque a chave de imagem existe. Google Fact Check e buscas não garantem cobertura de toda mensagem.

## Verificação reproduzível

Resultado final nesta etapa:

- Backend: **178 testes e 93 subtestes aprovados**; dois avisos de descontinuação de dependências, nenhum erro.
- Frontend: **29 casos aprovados**, distribuídos em cinco arquivos; build de produção aprovado.
- HTTP local: **25 controles aprovados** (24 respostas esperadas e uma comparação comportamental). Incluem texto/lote, mídia inválida, imagem/vídeo, áudio invariável ao nome do arquivo, PDF, simulador WhatsApp, cadastro/login/refresh/logout, histórico e selo.
- Interface: fluxo real do exemplo Pix até o relatório; Modo Fácil em 320 px sem rolagem horizontal. Ajustes de quebra de texto, botões e cabeçalho do indicador; sem novos erros no console nesse fluxo.
- As suítes e controles HTTP usaram banco descartável local e **chaves externas desligadas**. Não foram usados dados ou banco de produção.

As amostras sintéticas de imagem/vídeo verificam decodificação e fluxo, não são um conjunto representativo de deepfakes. O simulador WhatsApp não comprova entrega para um número real. Os testes anteriores de PostgreSQL e Docker continuam registrados no README; não equivalem a confirmar o runtime do novo deployment Railway.

Publicação do commit de integrações `ac727ee`: Railway confirmou `SUCCESS`, build com Dockerfile e instalação de FFmpeg/ExifTool, aplicação iniciada na porta 8080. No Vercel foram conferidos CSS e identificadores públicos do JavaScript atualizados. A interface pública enviou o exemplo Pix e recebeu relatório (`POST /api/check-text` HTTP 200), com Google Fact Check e Serper respondendo. Tentativas diretas deste ambiente ao backend tiveram falha de conexão, mas o fluxo pelo navegador funcionou; elas não provam indisponibilidade do serviço.

O ajuste de latência `1fd2157` também teve deploy Railway `SUCCESS` e controle público concluído: OpenRouter respondeu, mas a saída não atendia ao formato esperado, sem alterar o veredito. O contrato JSON foi reforçado no commit `f4dbc0d`, com nova suíte aprovada e deployment `8dba53c4-0928-42f3-8519-dd0f68d092bd` confirmado `SUCCESS`. O novo controle público apresentou OpenRouter e Serper como concluídos, Google Fact Check sem correspondências, e registrou o modelo gratuito `nvidia/nemotron-3-super-120b-a12b:free`. Não houve erro de console nesse fluxo. O modelo do router pode variar nos próximos pedidos.

OCR/transcrição passam à consulta literal de evidências, sem uma segunda extração por LLM que gastaria quota e poderia atrasar/cancelar a busca factual. O estado `not_tested` em `/api/capabilities` é proposital: presença de variável não é um teste ativo, nem dispara cobrança. O sucesso deste controle de texto não certifica todas as modalidades nem disponibilidade futura de nenhum serviço.

## Limites dos vereditos

Texto necessita checagens correspondentes de duas famílias editoriais independentes para apoiar/refutar a afirmação. Notícias relacionadas, respostas de LLM e palavras como “fake” no nome do arquivo não são prova. A ausência de resultado não vira “verdadeiro” ou “falso”.

Mídia separa origem/produção do conteúdo factual. Os limiares experimentais dos detectores não foram calibrados em um conjunto representativo; as pontuações não são uma probabilidade universal de falsidade. Para medir precisão incluindo inconclusivos, veja [o plano de avaliação](VERIFICACOES-2026-10-03.md#como-medir-precisão-de-verdade-sem-esconder-inconclusivos).

## Referências oficiais

- [OpenRouter free router](https://openrouter.ai/openrouter/free), [limites gratuitos](https://openrouter.ai/docs/api_reference/limits) e [seleção/preço máximo de provedores](https://openrouter.ai/docs/guides/routing/provider-selection).
- [OpenRouter: contrato JSON Schema e suporte por endpoint](https://openrouter.ai/docs/guides/features/structured-outputs).
- [Aviso sobre cobrança com auto:free](https://openrouter.zendesk.com/hc/en-us/articles/51679572756123-I-used-openrouter-auto-free-or-auto-and-still-got-charged).
- [Hive v3: modelo, classes e requisição](https://docs.thehive.ai/docs/ai-generated-and-deepfake-content-detection-playground) e [tarifa do modelo](https://thehive.ai/models/hive/ai-generated-and-deepfake-content-detection).
- [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash) e [thinkingLevel](https://ai.google.dev/gemini-api/docs/thinking).
- [AssemblyAI: escolha explícita de modelo de transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/select-the-speech-model).
