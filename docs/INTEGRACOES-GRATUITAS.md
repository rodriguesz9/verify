# Integrações e testes — 3 de outubro de 2026

O código das integrações foi atualizado. **Isso não significa que todas as APIs estejam operacionais em produção ou que os vereditos tenham precisão de 100%.** Credencial presente, HTTP 200 e testes com respostas simuladas são coisas diferentes de acesso real e avaliação de precisão.

## Resultado observado

| Serviço/camada | Teste real desta etapa | Situação e limite |
| --- | --- | --- |
| Gemini — texto | Uma resposta JSON válida com `gemini-3.7-flash` | Funcionou no controle mínimo. Foram observados timeouts em tentativas anteriores. Não é validação de todas as análises. |
| Gemini — leitura de imagem | HTTP 503 no último controle | Indisponível nessa tentativa; OCR alternativo gratuito do OpenRouter foi implementado, mas precisa de validação com chave. |
| Gemini — transcrição | Prazo de 12 s atingido | Não foi possível transcrever nesse controle. O relatório conserva esse motivo, sem inventar fala ou autenticidade. |
| OpenRouter | Chave local ausente; variável mascarada existe no Railway | Integração gratuita implementada e testada com respostas controladas. A chamada real ainda precisa ser validada. |
| Hive v3 — imagem | Uma chamada com a imagem sintética de controle | Resposta válida: sinal de geração por IA próximo de 1; sinal de deepfake próximo de 0. Não valida reconhecimento de face-swap nem sensibilidade geral. |
| Hive v3 — áudio/vídeo | Não executado | Sem gasto adicional autorizado. As duas saídas visuais usam a mesma chamada, não dois votos independentes. |
| Hugging Face | Sem endpoint de detecção configurado | Token sozinho não disponibiliza um detector. Não foi contratado servidor/GPU pago. |
| Google Fact Check, Serper, Sightengine, AssemblyAI e SerpAPI | Não revalidados ao vivo nesta etapa | Adaptadores e políticas têm controles automatizados; acesso, modelo e quota reais ainda precisam ser confirmados. |

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
- A IA extrai trechos literais para pesquisa ou lê texto de imagens. Sua opinião não define verdade/falsidade, identidade, clonagem de voz ou origem da mídia.
- Provedores gratuitos podem ter políticas próprias de retenção/uso de dados. Evite conteúdo pessoal sensível e consulte a página de privacidade.

## O que falta configurar ou confirmar

1. **OpenRouter:** gere/use a chave em [Settings → Keys](https://openrouter.ai/settings/keys). Mantenha-a somente no backend/Railway. Para o teste local, preencha `OPENROUTER_API_KEY` no `.env` privado do backend e avise; não cole no chat nem use variável `VITE_` para segredos.
2. **Hive:** a chave v3 é a **Secret Key**, não o Access Key ID da captura. Use `HIVE_V3_API_KEY` ou a `HIVE_API_KEY` existente com `HIVE_API_VERSION=v3`. Só preencha `HIVE_V3_MEDIA_TYPES=image,audio` se decidir autorizar o consumo contínuo. Isso é pago; vídeo também consome análises de quadros. A plataforma não dispõe aqui de um teto financeiro global do Hive.
3. **Hugging Face:** configure um endpoint compatível com o contrato documentado em [ATIVAR-DETECTORES.md](ATIVAR-DETECTORES.md). Não foi confirmado um detector hospedado gratuito adequado. Deixe desativado se exigir pagamento; ausência dessa camada gera resultado inconclusivo quando faltarem evidências.
4. **Gemini:** a chave funcionou para texto, mas OCR/transcrição tiveram indisponibilidade/prazo. Confira a [quota do projeto](https://aistudio.google.com/usage) e não ative faturamento só para ocultar o erro. O fallback de transcrição AssemblyAI usa `universal-2`, requer chave e crédito próprios.
5. **SerpAPI:** a chave apareceu inteira em uma captura enviada. **Revogue e gere outra em [Manage API key](https://serpapi.com/manage-api-key)**, depois atualize o `.env` privado e Railway. Não reutilize a chave exposta.
6. **Demais serviços:** confirme créditos gratuitos/entitlements antes dos testes reais. Não habilite `SIGHTENGINE_AUDIO_ENABLED` só porque a chave de imagem existe. Google Fact Check e buscas não garantem checagens correspondentes para toda mensagem.

## Verificação reproduzível

Resultado final nesta etapa:

- Backend: **161 testes e 90 subtestes aprovados**; dois avisos de descontinuação de dependências, nenhum erro.
- Frontend: **27 casos aprovados**, distribuídos em quatro arquivos; build de produção aprovado.
- HTTP local: **25 controles aprovados** (24 respostas esperadas e uma comparação comportamental). Incluem texto/lote, mídia inválida, imagem/vídeo, áudio invariável ao nome do arquivo, PDF, simulador WhatsApp, cadastro/login/refresh/logout, histórico e selo.
- Interface: fluxo real do exemplo Pix até o relatório; Modo Fácil em 320 px sem rolagem horizontal. Ajustes de quebra de texto, botões e cabeçalho do indicador; sem novos erros no console nesse fluxo.
- As suítes e controles HTTP usaram banco descartável local e **chaves externas desligadas**. Não foram usados dados ou banco de produção.

As amostras sintéticas de imagem/vídeo verificam decodificação e fluxo, não são um conjunto representativo de deepfakes. O simulador WhatsApp não comprova entrega para um número real. Os testes anteriores de PostgreSQL e Docker continuam registrados no README; não equivalem a confirmar o runtime do novo deployment Railway.

O endpoint público do backend não pôde ser acessado deste ambiente na tentativa inicial (timeout de conexão). Publicação/deployment deve ser conferido após o push. O estado `not_tested` em `/api/capabilities` é proposital: presença de variável não é um teste ativo, nem dispara cobrança.

## Limites dos vereditos

Texto necessita checagens correspondentes de duas famílias editoriais independentes para apoiar/refutar a afirmação. Notícias relacionadas, respostas de LLM e palavras como “fake” no nome do arquivo não são prova. A ausência de resultado não vira “verdadeiro” ou “falso”.

Mídia separa origem/produção do conteúdo factual. Os limiares experimentais dos detectores não foram calibrados em um conjunto representativo; as pontuações não são uma probabilidade universal de falsidade. Para medir precisão incluindo inconclusivos, veja [o plano de avaliação](VERIFICACOES-2026-10-03.md#como-medir-precisão-de-verdade-sem-esconder-inconclusivos).

## Referências oficiais

- [OpenRouter free router](https://openrouter.ai/openrouter/free), [limites gratuitos](https://openrouter.ai/docs/api_reference/limits) e [seleção/preço máximo de provedores](https://openrouter.ai/docs/guides/routing/provider-selection).
- [Aviso sobre cobrança com auto:free](https://openrouter.zendesk.com/hc/en-us/articles/51679572756123-I-used-openrouter-auto-free-or-auto-and-still-got-charged).
- [Hive v3: modelo, classes e requisição](https://docs.thehive.ai/docs/ai-generated-and-deepfake-content-detection-playground) e [tarifa do modelo](https://thehive.ai/models/hive/ai-generated-and-deepfake-content-detection).
- [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash) e [thinkingLevel](https://ai.google.dev/gemini-api/docs/thinking).
- [AssemblyAI: escolha explícita de modelo de transcrição](https://www.assemblyai.com/docs/pre-recorded-audio/select-the-speech-model).
