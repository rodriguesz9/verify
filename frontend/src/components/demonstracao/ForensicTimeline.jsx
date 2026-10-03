import { useState } from "react";

const FORENSIC_LAYERS = [
  {
    id: "layer1",
    badge: "CAMADA 1",
    title: "Metadados & Proveniência C2PA",
    tech: "EXIFTool + C2PATool (Local / Sem API)",
    icon: "📸",
    color: "#00D4FF",
    desc: "Examina o cabeçalho binário do arquivo em busca de dados de câmera original (Make/Model), GPS, timestamps, e marcas de software como Midjourney, Photoshop ou DALL-E.",
    checks: [
      "Tags EXIF declaradas; podem ser alteradas e não comprovam autenticidade",
      "Assinatura digital C2PA (Coalition for Content Provenance)",
      "Detecção de ferramentas de IA no campo CreatorTool/Software",
      "Timestamp original de captura do arquivo"
    ]
  },
  {
    id: "layer2",
    badge: "CAMADA 2",
    title: "Detecção Multimodal de IA & Deepfakes",
    tech: "Hive AI + Sightengine + HuggingFace",
    icon: "🧠",
    color: "#FF3B5C",
    desc: "Modelos neurais convolucionais e Vision Transformers treinados para identificar aberrações de texturas, dentes irregulares, reflexos inconsistentes e artefatos de difusão.",
    checks: [
      "Probabilidade de geração por modelos de difusão (0 a 100%)",
      "Detecção de Deepfakes de troca de rosto (Face-Swap)",
      "Artefatos em íris, bordas de pele e cabelos",
      "Classificação multimodal para imagens e vídeos"
    ]
  },
  {
    id: "layer3",
    badge: "CAMADA 3",
    title: "Contexto Histórico & Reuso de Mídia",
    tech: "Wayback Machine + TinEye + Google Fact Check",
    icon: "🌐",
    color: "#FFB800",
    desc: "Descobre se a imagem ou notícia divulgada como 'urgente' na verdade foi publicada anos atrás em outro contexto, desmascarando desinformação reciclada.",
    checks: [
      "Data de um registro disponível na Wayback; não necessariamente o primeiro",
      "Busca reversa por duplicatas exatas ou cortes na web (TinEye)",
      "Cruzamento com bases de agências de checagem (Lupa, Aos Fatos)",
      "Reputação do domínio transmissor"
    ]
  },
  {
    id: "layer4",
    badge: "CAMADA 4",
    title: "Transcrição & Sinais de Golpe",
    tech: "Gemini Audio + padrões no conteúdo da fala",
    icon: "🎙️",
    color: "#8A2BE2",
    desc: "Transcreve a fala quando o provedor está disponível e aponta padrões de pedido financeiro suspeito. Não comprova clonagem, identidade ou origem humana da voz.",
    checks: [
      "Transcrição real ou indicação de indisponibilidade; sem texto inventado",
      "Autenticidade da voz inconclusiva sem detector validado para essa finalidade",
      "Detecção de scripts do 'Golpe do Parente' e falsos pedidos de Pix",
      "Confirmação de identidade por outro canal continua necessária"
    ]
  },
  {
    id: "layer5",
    badge: "CAMADA 5 (ORQUESTRADOR)",
    title: "Política Conservadora de Evidências",
    tech: "Regras auditáveis + inspeção visual auxiliar",
    icon: "⚖️",
    color: "#00FF87",
    desc: "O cérebro que pondera todas as evidências das camadas 1 a 4, identifica eventuais contradições técnicas entre sinais e emite o laudo final com explicação acessível a leigos.",
    checks: [
      "Identificação de contradições (ex: C2PA diz real, mas Hive dá 90% IA)",
      "Índice heurístico não equivale à precisão estatística nem à autenticidade comprovada",
      "Geração de explicação em linguagem simples para idosos",
      "Recomendação de segurança prática para o cidadão"
    ]
  }
];

export default function ForensicTimeline() {
  const [activeLayer, setActiveLayer] = useState(FORENSIC_LAYERS[4]);

  return (
    <div className="bg-[#0A1520] border border-[#132435] rounded-3xl p-8 max-w-4xl mx-auto shadow-2xl">
      {/* Header */}
      <div className="text-center mb-8">
        <span className="font-mono text-xs text-[#00D4FF] tracking-widest uppercase font-bold block mb-2">
          ARQUITETURA TÉCNICA • QUADRO DE INVESTIGAÇÃO FORENSE
        </span>
        <h2 className="font-syne font-black text-3xl md:text-4xl text-[#CDE8F0] uppercase tracking-tight">
          Pipeline Multi-Camadas <span className="text-[#00FF87]">(Multi-Layer Verification)</span>
        </h2>
        <p className="font-mono text-sm text-[#3A6070] mt-3 max-w-2xl mx-auto">
          Veja quais camadas podem apoiar a análise. Disponibilidade depende da configuração e todas têm limitações; não há garantia de detecção.
        </p>
      </div>

      {/* Interactive Layer Flow */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-8">
        {FORENSIC_LAYERS.map((layer) => {
          const isSelected = activeLayer.id === layer.id;
          return (
            <button
              key={layer.id}
              type="button"
              onClick={() => setActiveLayer(layer)}
              className={`p-4 rounded-2xl border text-center transition-all cursor-pointer flex flex-col items-center justify-center ${
                isSelected
                  ? "bg-[#060D14] border-white shadow-xl scale-105"
                  : "bg-[#060D14]/60 border-[#132435] hover:border-white/30"
              }`}
              style={{ borderColor: isSelected ? layer.color : undefined }}
            >
              <span className="text-2xl mb-1">{layer.icon}</span>
              <span
                className="font-mono text-[9px] uppercase tracking-wider font-bold mb-1"
                style={{ color: layer.color }}
              >
                {layer.badge}
              </span>
              <h4 className="font-syne font-bold text-xs text-[#CDE8F0] line-clamp-2">
                {layer.title.split("&")[0]}
              </h4>
            </button>
          );
        })}
      </div>

      {/* Detailed Selected Layer Card */}
      <div
        className="p-8 rounded-3xl border bg-[#060D14] transition-all animate-fade-in"
        style={{ borderColor: `${activeLayer.color}44` }}
      >
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6 pb-6 border-b border-white/5">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl shadow"
              style={{ backgroundColor: `${activeLayer.color}22`, border: `1px solid ${activeLayer.color}66` }}
            >
              {activeLayer.icon}
            </div>
            <div>
              <span
                className="font-mono text-xs uppercase tracking-widest font-bold"
                style={{ color: activeLayer.color }}
              >
                {activeLayer.badge} • {activeLayer.tech}
              </span>
              <h3 className="font-syne font-black text-2xl text-[#CDE8F0] mt-1">{activeLayer.title}</h3>
            </div>
          </div>
        </div>

        <p className="font-mono text-sm text-[#CDE8F0] leading-relaxed mb-6">{activeLayer.desc}</p>

        <div>
          <h5 className="font-mono text-xs text-[#8BAAC0] uppercase tracking-wider font-bold mb-3">
            O QUE ESTA CAMADA INVESTIGA:
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {activeLayer.checks.map((check, i) => (
              <div
                key={i}
                className="p-3 rounded-xl bg-black/40 border border-white/5 flex items-center gap-3 font-mono text-xs text-[#8BAAC0]"
              >
                <span style={{ color: activeLayer.color }}>✓</span>
                <span>{check}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
