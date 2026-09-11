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
      "Presença de tags EXIF autênticas de sensor fotográfico",
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
      "Data de primeiro arquivamento na Wayback Machine",
      "Busca reversa por duplicatas exatas ou cortes na web (TinEye)",
      "Cruzamento com bases de agências de checagem (Lupa, Aos Fatos)",
      "Reputação do domínio transmissor"
    ]
  },
  {
    id: "layer4",
    badge: "CAMADA 4",
    title: "Forense de Áudio & Voz Clonada",
    tech: "AssemblyAI + Heurísticas Acústicas TTS",
    icon: "🎙️",
    color: "#8A2BE2",
    desc: "Avalia a prosódia, o espectrograma e a ausência de micro-pausas respiratórias humanas, além de transcrever o discurso para identificar padrões de estelionato.",
    checks: [
      "Ausência de ruído de respiração natural e acústica ambiente",
      "Pitch e prosódia característicos de modelos de clonagem (XTTS/VITS)",
      "Detecção de scripts do 'Golpe do Parente' e falsos pedidos de Pix",
      "Confiança fonética palavra por palavra"
    ]
  },
  {
    id: "layer5",
    badge: "CAMADA 5 (ORQUESTRADOR)",
    title: "Consolidação Forense com Gemini 3.7",
    tech: "Google Gemini 3.7 Flash",
    icon: "⚖️",
    color: "#00FF87",
    desc: "O cérebro que pondera todas as evidências das camadas 1 a 4, identifica eventuais contradições técnicas entre sinais e emite o laudo final com explicação acessível a leigos.",
    checks: [
      "Identificação de contradições (ex: C2PA diz real, mas Hive dá 90% IA)",
      "Cálculo ponderado do score final de autenticidade (0 a 100%)",
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
          Veja como o Verify cruza evidências independentes para tomar a decisão mais confiável e à prova de falhas.
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
