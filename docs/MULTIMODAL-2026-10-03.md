# Leitura de mídia e detectores — 3 de outubro de 2026

Correções testadas com controles públicos e fictícios. Não é avaliação estatística de precisão nem garantia de disponibilidade futura. HTTP 200 indica resposta, não um veredito correto.

## Resultado real observado

| Camada | Controle e resultado | Interpretação permitida |
| --- | --- | --- |
| OCR local Tesseract | Docker sem internet: quatro linhas impressas, incluindo negação, R$ 123,45 e data; quatro recuperadas | Leitura funcional nesse controle, sem chave comercial. Não prova autenticidade nem cobre manuscritos/fotos difíceis. |
| Gemini OCR | `gemini-3.1-flash-lite`: quatro linhas recuperadas, 5,17 s | Alternativa remota funcional nesse controle. O modelo de texto permanece separado. |
| Gemini transcrição | Controle novo de fala portuguesa: prazo de 20 s atingido, inclusive após normalização | Continua não confiável nesse caminho. Preferência por AssemblyAI evita depender desse resultado. Não comprar quota para esconder a falha. |
| Proteção de silêncio | Antes: Gemini inventou seis palavras num WAV silencioso. Depois: bloqueio local, nenhuma chamada de transcrição, zero palavras | Corrige silêncio/quase silêncio; não é um detector geral de voz nem resolve toda alucinação em gravações ruidosas. |
| AssemblyAI | Nova fala sintética portuguesa, 16 palavras esperadas: 16 recuperadas; WER 0 nesse controle; 4,28 s | Integração/transcrição funcional, não reconhecimento de clonagem ou identidade. Usa somente os créditos gratuitos autorizados. |
| Hugging Face | Endpoint compartilhado respondeu. Imagem declaradamente sintética: sinal IA 0,002527 — falso negativo. Em produção, gráfico impresso local: sinal exibido de 100,0% (arredondado) — falso positivo | Conectado, porém experimental e **sem voto no veredito**, inclusive em quadros de vídeo. Não confundir acesso com qualidade. |
| Sightengine imagem | Imagem sintética: `genai` 0,99; controle gráfico impresso: 0,001; sinal facial 0,02/0,001 respectivamente | Dois controles de integração, não benchmark. Manipulação facial e fotografias humanas diversas não validadas. |
| SerpAPI | Nova chave privada autenticada: Account API HTTP 200, sem consumir uma pesquisa | Credencial válida nessa tentativa. Busca Lens completa não revalidada; uploads privados não são publicados para obter URL. |
| Hive | Nenhuma chamada nova nesta etapa | Teste anterior de imagem permanece registrado. Áudio, face-swap e lip-sync não validados. Chamadas pagas continuam pausadas. |

O MP3 antigo apresentado como conversa portuguesa continha fala em inglês e origem não auditada. A demonstração agora usa dois WAVs de **fala sintética portuguesa**, gerados offline por eSpeak NG. Ambos são identificados como sintéticos; o exemplo cotidiano não é anunciado como voz humana real. Não foi feita imitação de pessoa real. Os MP3 antigos foram preservados, mas saíram dessa demonstração.

## Configuração não secreta do backend/Railway

Aplicar somente com esta revisão implantada, porque ela exclui Hugging Face experimental da decisão:

```dotenv
LOCAL_OCR_ENABLED=true
GEMINI_MEDIA_MODEL_NAME=gemini-3.1-flash-lite
AUDIO_TRANSCRIPTION_PROVIDER=assemblyai
HUGGINGFACE_IMAGE_API_URL=https://router.huggingface.co/hf-inference/models/Ateeqq/ai-vs-human-image-detector
HUGGINGFACE_AI_LABEL=ai
```

Preservar as chaves privadas existentes; nenhuma deve ir para `VITE_*`, Git ou chat. O `.env.example` documenta opções, não replica segredos do `.env`. O padrão de transcrição no código continua `gemini`; a configuração acima escolhe AssemblyAI primeiro, com fallback limitado. A chave do Gemini não habilita automaticamente todos os modelos: `gemini-2.5-flash-lite` retornou 404 nessa conta mesmo constando na listagem.

Manter `OPENROUTER_MODEL=openrouter/free`, preço máximo zero, `HIVE_V3_MEDIA_TYPES=` e `SIGHTENGINE_AUDIO_ENABLED=false`. Não houve compra de endpoint dedicado, assinatura, cartão ou recarga. Créditos gratuitos têm limite; o HF compartilhado não é ilimitado. Erro de acesso/quota vira indisponibilidade, não compra automática nem prova de falsidade. **Não há teto financeiro global implementado para todos os provedores**; os serviços precisam continuar em planos gratuitos sem cobrança automática, como confirmado para Sightengine/AssemblyAI.

## Melhorias implementadas

- OCR local primeiro; qualidade insuficiente ou ferramenta ausente permite alternativas remotas. Prazo, bytes, resolução e saída limitados; arquivos temporários privados removidos após uso. Confiança de reconhecimento não vira porcentagem de veracidade.
- Áudio convertido localmente para mono 16 kHz. Quase silêncio não é enviado para pedir palavras a um LLM. O usuário deve regravar; o bloqueio não certifica que nenhuma voz exista no original.
- Polling AssemblyAI dentro de prazo único de 25 s, sem reenviar automaticamente uma tarefa pendente. Camada de áudio com prazo de 50 s; entrada permanece limitada a dois minutos. Há distinção entre erro, ausência de fala e sucesso.
- Respostas estruturadas de OCR/transcrição, modelo efetivo e tentativas registradas, sem respostas brutas ou credenciais.
- HF exige URL oficial HTTPS, classe positiva exata e scores finitos; não segue redirecionamentos autenticados. Resultado experimental fica visível, mas não determina origem.
- A visão simples não apresenta porcentagens de detectores experimentais. O valor bruto permanece no diagnóstico técnico. Fontes recuperadas sem correspondência validada são rotuladas como não usadas na decisão, com o motivo; uma checagem de outro assunto marcada “Falso” não prova falsidade do conteúdo enviado.
- “Urgente” isolado e “não pague uma taxa” deixam de gerar esses falsos alarmes. Negação é tratada por regras conservadoras, não compreensão semântica completa: citações, ironia e relatos ainda podem exigir análise humana.
- Demonstração impede trocar arquivo durante análise/carregamento/gravação; não apresenta resultado de uma amostra como se fosse de outra.
- Atalhos e título da demonstração corrigidos no Modo Fácil: largura de conteúdo 305 px em viewport 320 px com área reservada à barra de rolagem; sem rolagem lateral nesse controle.

## Verificação reproduzível

Backend: **178 testes + 93 subtestes aprovados**; frontend: **30 casos aprovados**; build de produção aprovado. Docker inclui Tesseract português/inglês e FFmpeg. Controle visual percorreu envio de imagem → OCR → consulta factual → relatório, sem erro de console; conteúdo sem evidência correspondente permaneceu inconclusivo.

HTTP local: **25 controles aprovados**, com chaves externas desligadas e banco SQLite descartável. O primeiro lote atingiu corretamente o limite 429; a repetição usou limites maiores **somente no contêiner de testes**, sem alterar produção. Cadastro, login, refresh, logout, histórico, PDF, lote, WhatsApp simulado e selos passaram; isso não valida transporte WhatsApp real nem todos os fornecedores.

Probes opt-in, na raiz do repositório (podem consumir créditos):

```bash
PYTHONPATH=backend python backend/scripts/multimodal_probe.py \
  --env-file backend/.env --controls hf_metadata,gemini_ocr \
  --output /tmp/verify-media-controls.json

# Só após confirmar crédito gratuito sem cobrança automática:
PYTHONPATH=backend python backend/scripts/multimodal_probe.py \
  --env-file backend/.env --controls assembly_pt,sightengine_negative,serpapi_account \
  --free-credits-confirmed --output /tmp/verify-free-controls.json
```

O probe não inclui chamadas Hive, não contrata endpoints e não imprime chaves. `hf_image` usa o controle sintético conhecido e registra eventual erro de classificação. `gemini_pt` não usa AssemblyAI escondido para transformar uma falha Gemini em sucesso. As amostras são controles de desenvolvimento, nunca conjunto independente de validação.

## Controle público após publicação

Commit de backend `addbf27`: deployment Railway `5010379a-bfa7-4da1-afaf-32f0d2b9661e` confirmou `SUCCESS`, aplicação iniciada na porta 8080. Variáveis não secretas acima aplicadas. Vercel apresentou os WAVs e rótulos novos. Não houve alteração de segredos, plano ou banco de produção.

- Áudio pelo navegador público: `POST /api/verificar/audio-rapido` HTTP 200, 2.889 ms totais; transcrição exatamente igual às 16 palavras da conversa portuguesa. Origem da voz permaneceu inconclusiva, com Hive/Sightengine áudio pausados. Nenhum erro de console observado.
- Imagem pelo navegador público: `POST /api/upload` HTTP 200, 6.657 ms totais; quatro linhas lidas por Tesseract. Sightengine/HF/Gemini visual responderam; HF experimental não alterou o veredito. Sem novo erro de console. Google Fact Check trouxe resultados de outro assunto, rejeitados pela correspondência conservadora: não se tornaram prova de falsidade.
- A leitura direta da rota de capacidades foi bloqueada na navegação deste ambiente; o proxy Railway registrou HTTP 200. A conferência dos fluxos públicos foi feita pela interface e pelos logs, sem contornar proteções do navegador.

Esses são controles limitados, não uma homologação de todas as modalidades ou uma garantia para futuros pedidos. Os ajustes de exibição posteriores preservam os mesmos dados/política; não adicionam votos nem atribuem precisão ao HF.

## O que ainda falta para avaliar precisão

Corpus independente com consentimento/licenças, separado dos controles de desenvolvimento: fotografias humanas, imagens IA de vários geradores, face-swap, compressão/redimensionamento, fala humana/sintética e vídeos manipulados. Medir falsos positivos, falsos negativos e abstenções por modalidade/modelo/grupo; não excluir inconclusivos para inflar acurácia.

Ainda sem validação real de clonagem de voz, identidade, lip-sync ou cobertura de todos os quadros. Dois detectores de fornecedores diferentes são requisito conservador da política, **não garantia estatística de independência ou correção**. Não liberar voto do HF sem validação/calibração independente. Para orientações de próxima etapa, veja [plano de avaliação](VERIFICACOES-2026-10-03.md#como-medir-precisão-de-verdade-sem-esconder-inconclusivos).

## Referências oficiais

- [Tesseract — instalação e idiomas](https://tesseract-ocr.github.io/tessdoc/Installation.html).
- [Gemini 3.1 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [acesso ao modelo 2.5 legado](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite).
- [AssemblyAI — seleção do modelo](https://www.assemblyai.com/docs/pre-recorded-audio/select-the-speech-model).
- [HF — créditos de inferência](https://huggingface.co/docs/inference-providers/main/pricing), [modelo testado, com alerta de overfitting](https://huggingface.co/Ateeqq/ai-vs-human-image-detector).
- [Sightengine — planos e limites](https://sightengine.com/pricing).
- [SerpAPI — consulta de conta](https://serpapi.com/account-api).
