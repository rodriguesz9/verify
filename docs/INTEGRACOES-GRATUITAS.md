# Integrações e testes — 3 de outubro de 2026

O código das integrações foi atualizado. **Isso não significa que todas as APIs estejam operacionais em produção ou que os vereditos tenham precisão de 100%.** Credencial presente, HTTP 200 e testes com respostas simuladas são coisas diferentes de acesso real e avaliação de precisão.

## Resultado observado

| Serviço/camada | Teste real desta etapa | Situação e limite |
| --- | --- | --- |
| Gemini — texto | Uma resposta JSON válida com `gemini-3.7-flash` | Funcionou no controle mínimo. Foram observados timeouts em tentativas anteriores. Não é validação de todas as análises. |
| Gemini — leitura de imagem | HTTP 503 no último controle | Indisponível nessa tentativa; OCR alternativo gratuito do OpenRouter foi implementado, mas precisa de validação com chave. |
| Gemini — transcrição | Prazo de 12 s atingido | Não foi possível transcrever nesse controle. O relatório conserva esse motivo, sem inventar fala ou autenticidade. |
| OpenRouter | Resposta válida no controle público após corrigir prazo e formato | Modelo efetivo `nvidia/nemotron-3-super-120b-a12b:free`. Extração auxiliar de texto funcionou com preço máximo zero/JSON Schema. OCR gratuito ainda não foi validado ao vivo; a chave local continua ausente. |
| Hive v3 — imagem | Uma chamada com a imagem sintética de controle | Resposta válida: sinal de geração por IA próximo de 1; sinal de deepfake próximo de 0. Não valida reconhecimento de face-swap nem sensibilidade geral. |
| Hive v3 — áudio/vídeo | Não executado | Sem gasto adicional autorizado. As duas saídas visuais usam a mesma chamada, não dois votos independentes. |
| Hugging Face | Sem endpoint de detecção configurado | Token sozinho não disponibiliza um detector. Não foi contratado servidor/GPU pago. |
| Google Fact Check | Consulta pública concluída, sem checagens correspondentes ao exemplo Pix | Sem correspondência não significa verdadeiro/falso. Não valida resultados para outras afirmações. |
| Serper | Notícias relacionadas retornadas no relatório público do exemplo Pix | Funcionou nesse controle; notícia relacionada não é automaticamente prova sobre a mensagem. |
| Sightengine, AssemblyAI e SerpAPI | Não revalidados ao vivo nesta etapa | Adaptadores e políticas têm controles automatizados; acesso, modelo e quota reais ainda precisam ser confirmados. |

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
3. **Hugging Face:** configure um endpoint compatível com o contrato documentado em [ATIVAR-DETECTORES.md](ATIVAR-DETECTORES.md). Não foi confirmado um detector hospedado gratuito adequado. Deixe desativado se exigir pagamento; ausência dessa camada gera resultado inconclusivo quando faltarem evidências.
4. **Gemini:** a chave funcionou para texto, mas OCR/transcrição tiveram indisponibilidade/prazo. A janela de transcrição passou de 12 para 20 s; OCR usa até 12 s no Gemini e 20 s no fallback gratuito, sem certificado de funcionamento de todas as modalidades. Confira a [quota do projeto](https://aistudio.google.com/usage) e não ative faturamento só para ocultar o erro. O fallback de transcrição AssemblyAI usa `universal-2`, requer chave e crédito próprios.
5. **SerpAPI:** a chave apareceu inteira em uma captura enviada. **Revogue e gere outra em [Manage API key](https://serpapi.com/manage-api-key)**, depois atualize o `.env` privado e Railway. Não reutilize a chave exposta.
6. **Demais serviços:** confirme créditos gratuitos/entitlements antes dos testes reais. Não habilite `SIGHTENGINE_AUDIO_ENABLED` só porque a chave de imagem existe. Google Fact Check e buscas não garantem checagens correspondentes para toda mensagem.

## Verificação reproduzível

Resultado final nesta etapa:

- Backend: **164 testes e 93 subtestes aprovados**; dois avisos de descontinuação de dependências, nenhum erro.
- Frontend: **27 casos aprovados**, distribuídos em quatro arquivos; build de produção aprovado.
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
