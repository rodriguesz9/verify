# Status dos Problemas e Correções Realizadas

## Auditoria de 2026-10-02 — estado verificado

Os registros abaixo deste bloco são históricos, não garantias de precisão ou de produção concluída. A auditoria reproduziu falhas de texto/WhatsApp, áudio condicionado ao nome e validação insuficiente de mídia no deploy.

- [x] Revisão local: validação real, três quadros de vídeo, respostas inconclusivas, leitura correta de Sightengine/Hive, áudio sem evidência inventada, lotes e hooks corrigidos.
- [x] Suíte ampliada, 25 controles locais e compilação; [relatório e limites](docs/AUDITORIA-2026-10-02.md).
- [ ] Publicar e repetir os controles na versão ativa.
- [ ] Resolver Hive HTTP 403, Hugging Face HTTP 400 e Gemini HTTP 429 observados; certificar fala TTS.
- [ ] Medir falsos positivos/negativos com fotos reais e deepfakes de origem conhecida; amostra de vídeo atual não é benchmark de face-swap.
- [ ] Autenticar webhook, limitar convidados/custos, reforçar SSRF e implementar retenção/exclusão.
- [ ] Certificar WhatsApp real, cookies de produção e C2PA criptográfico.


## UI
- **"Meu Painel"**
  - [x] *A barra superior bloqueia o conteúdo da sessão:* **Corrigido.** O espaçamento superior da tag `<main>` em `Dashboard.jsx` foi ampliado de `pt-10` para `pt-28`, evitando sobreposição com a barra fixa de navegação.
  - [x] *A página fica carregada muito baixa, e não tem como scrollar pra cima:* **Corrigido.** Adicionado `useEffect` com `window.scrollTo(0, 0)` no componente `PageWrapper` em `App.jsx`, garantindo que toda troca de rota inicie com a visualização no topo da tela.
- **Geral**
  - [x] *Palavras e números grandes escapam das divs:* Mitigado com `min-w-0`, `break-words` e tipografia responsiva.
  - [ ] *Ajuste de proporções do rodapé:* Reduzir escala de margens nos cards de rodapé para telas móveis.

## Server & Pipeline Forense
- [x] *Não lê imagens:* **Corrigido e Aprimorado.**
  - Resolvida a causa de imagens reais serem acusadas de falsas: `Photoshop` e `GIMP` foram removidos da lista de assinaturas de IA e categorizados como edição convencional de imagem.
  - O limiar de consenso foi elevado para evitar falso-positivo em fotos tiradas por smartphone com pós-processamento e compressão do WhatsApp.
  - Suporte completo a metadados EXIF, IPTC, C2PA e verificação forense.
- [x] *Dependências de áudio:* Adicionado carregamento seguro (lazy import) de `numpy` e `librosa` para evitar falha no boot do servidor.
- [x] *Demonstração com áudios reais:* Inseridos arquivos reais (`voz_humana_real.mp3` e `voz_golpe_clonado.mp3`) na pasta pública, integrados com reprodutor nativo HTML5 e endpoint `/api/verificar/audio-rapido`.
- [x] *WhatsApp Bot:* Webhook e simulador alinhados e validados por suíte de testes.

## Roadmap implementado (ROADMAP_FUTURO.md)
- [x] *Fase 1.1 - Inspeção multimodal direta (Gemini Vision):* O endpoint `/api/upload` agora envia os bytes da imagem (`image/jpeg/png/webp`) ao Gemini Vision com prompt forense (anatomia, consistência física, compressão vs difusão, edição convencional vs IA), via `analyze_image_with_vision()` em `app/core/gemini_analyzer.py`.
- [x] *Fase 1 - OCR de capturas:* `extract_text_from_image()` extrai texto via Gemini Vision (comprovantes, prints, documentos), preservando valores, datas e chaves Pix.
- [x] *Fase 1.2 - Prova de existência histórica:* `search_google_lens_reverse()` em `app/services/reverse_search_service.py` integra SerpApi (Google Lens reversa) com data de primeira aparição e regra de corte para imagens pré-2022 (veredito "Foto Histórica Autêntica").
- [x] *Fase 3.1 - Modo Fácil / Terceira Idade:* Seletor global no topo (`Navbar.jsx`), CTA no hero da `LandingPage.jsx` e efeito `data-font-size="elderly"` em `index.css` (fonte 20px, alto contraste, botões ≥48px).
- [x] *Fase 2 - Bot WhatsApp (parcial):* Contêiner `evolution-api` no `docker-compose.yml` (perfil `whatsapp`); download de mídia (áudio/imagem), transcrição, OCR+Vision, resposta em áudio via Gemini TTS e histórico anônimo (hash SHA-256) no webhook.

## Pendências (futuras)
- [ ] *Fase 4 - Exemplos reais na Demonstração:* 4 novos cenários (áudio de idosa sobre receita, clonagem com resgate falso, comprovante Pix agendado falso, foto da década de 1980) dependem de arquivos de mídia reais a serem fornecidos.
- [ ] *Fase 1.3 - Deepfake em vídeos:* extração de frames com ffmpeg, taxa de piscar e sincronia labial.
- [ ] *Módulo 4 - Compativeis Pix e boletos:* validação de linha digitável e detecção de comprovante "AGENDADO" falso.
