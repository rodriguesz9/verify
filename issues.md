# Status dos Problemas e Correções Realizadas

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