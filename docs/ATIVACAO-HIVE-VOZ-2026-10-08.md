# Ativação de imagem e voz — 8 de outubro de 2026

Guia de configuração, não confirmação de implantação ou de precisão. O usuário autorizou uso do saldo existente do Hive; nenhuma recarga, assinatura ou inclusão de cartão foi autorizada. Hugging Face pago não será usado.

## Hive: resolver “não disponível”

Uma chave presente não habilita sozinha todos os modelos. Nesta aplicação, v2 recebe chave de projeto; v3 recebe **Secret Key** de Service API Keys. Access Key ID, nome do projeto e chave v2 não substituem a Secret Key v3. A documentação oficial explica a criação de Service API Keys e autenticação Bearer: [chave v3](https://docs.thehive.ai/docs/chat-completions-openai-compatible-llms). O detector desejado é [AI-Generated & Deepfake Content Detection](https://thehive.ai/models/hive/ai-generated-and-deepfake-content-detection), não um modelo de geração de imagens.

No serviço **backend** do Railway, manter o segredo em variável privada e configurar:

```dotenv
HIVE_API_VERSION=v3
HIVE_V3_API_KEY=<Secret Key privada existente>
HIVE_V3_MEDIA_TYPES=image,audio
HIVE_V3_IMAGE_REQUEST_LIMIT=20
HIVE_V3_AUDIO_SECONDS_LIMIT=60
VIDEO_MAX_FRAMES=3
```

Não copiar o placeholder. Não colocar segredo no frontend, em `VITE_*`, no Git ou em captura de tela. Aplicar as alterações e aguardar o novo backend iniciar. O `.env` local e as Variables do Railway são configurações independentes.

O código também aceita `HIVE_API_KEY` como fallback quando a versão é explicitamente `v3`, mas `HIVE_V3_API_KEY` evita confundir credenciais. Se ambas estiverem preenchidas, a v3 específica tem precedência. `HIVE_V3_MEDIA_TYPES` vazia bloqueia chamadas pagas deliberadamente. `image` também permite analisar os quadros dos vídeos; não adicionar `video`, pois esse cliente envia quadros como imagens. Imagem e manipulação facial compartilham uma chamada e contam como um fornecedor, não dois votos independentes.

Na revisão de 08/10, os dois limites novos têm padrão **zero**, que impede envio. Com os valores de exemplo, cada processo admite até vinte imagens/quadros e sessenta segundos acumulados de áudio. Cada arquivo de áudio arredonda sua duração validada para o segundo inteiro seguinte antes de reservar quota. Não são sessenta segundos por arquivo. Falha, timeout ou cancelamento não devolvem reserva, pois não comprovam ausência de processamento remoto. Aumentar quota autoriza mais consumo; não ajustar para contornar o aviso durante uma apresentação.

Se continuar sem resposta: confirmar versão/chave, acesso ao detector, saldo e erro sanitizado do backend. Não repetir indiscriminadamente uploads: timeout não comprova que o fornecedor deixou de processar ou cobrar.

## Custo e apresentação

O preço consultado é US$ 0,006 por imagem/quadro e US$ 10 por hora de áudio. Assim, três quadros custam nominalmente US$ 0,018; nove, US$ 0,054; áudio de 10 segundos, aproximadamente US$ 0,028. São estimativas de uso, não saldo consultado nem garantia de arredondamento/faturamento. [Preços oficiais](https://thehive.ai/pricing).

Um vídeo pode usar imagens **e** áudio. Reduzir para três quadros economiza, mas diminui cobertura temporal. O detector não comprova que a mensagem falada seja verdadeira, não identifica sozinho a pessoa e não certifica todo vídeo. Ensaiar poucos arquivos curtos autorizados, conferir Usage/Billing e manter recarga automática desligada. Guardas locais por processo não substituem um teto financeiro no fornecedor: reinícios e réplicas podem renovar contadores.

## Sightengine: voz não é música

**AI Music Detection** analisa música; o modelo de voz chama-se `ai_speech`. A documentação atual marca esse modelo como beta com acesso restrito a empresas e parceiros. Ter chave de imagem ou enxergar o menu não comprova permissão. Pedir liberação de teste para projeto acadêmico por [Contact/Support](https://sightengine.com/contact), citando `ai_speech`, orçamento zero e ausência de contratação automática. [Documentação oficial de voz](https://www-cf.sightengine.com/docs/ai-generated-speech-detection).

Somente depois de o fornecedor confirmar acesso/crédito, configurar no backend:

```dotenv
SIGHTENGINE_API_USER=<identificador privado existente>
SIGHTENGINE_API_SECRET=<segredo privado existente>
SIGHTENGINE_AUDIO_ENABLED=true
```

O código usa `POST /1.0/audio/check.json`, arquivo no campo `audio`, `models=ai_speech`, e lê `type.ai_speech`. Isso já corresponde à documentação; mudar só a variável não remove a restrição de acesso. Falta de resposta nunca deve virar “voz verdadeira”.

## Hugging Face

Não contratar endpoint nem comprar créditos. Nesta revisão, `HUGGINGFACE_ENABLED=false` é o padrão e impede envio mesmo com chave e endpoint presentes; manter esse valor no Railway. Em versões anteriores, a ausência de `HUGGINGFACE_IMAGE_API_URL` já impede o envio. A credencial privada pode ser preservada. Um detector experimental ou sem saldo não precisa aparecer como card técnico na interface pública.

## O que é OCR?

É leitura de palavras dentro de uma imagem: por exemplo, transformar um print “Pague uma taxa para liberar seu Pix” em texto que pode ser pesquisado e conferido. Não detecta sozinho montagem, IA ou mentira. O leitor pode trocar uma negação, valor ou data; a aplicação pede conferência antes de checar essas palavras. Para o público, usar “Texto encontrado na imagem”, não a sigla OCR.
