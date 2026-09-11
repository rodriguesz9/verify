import { useState } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import AudioDeepfakeDemo from "../components/banca/AudioDeepfakeDemo";
import AuthenticitySealDemo from "../components/banca/AuthenticitySealDemo";
import WhatsAppSimulator from "../components/banca/WhatsAppSimulator";
import ForensicTimeline from "../components/banca/ForensicTimeline";

export default function BancaDemoPage() {
  const [activeTab, setActiveTab] = useState("audio");

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  return (
    <div className="min-h-screen bg-[#04080C] text-[#CDE8F0] flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-28 pb-20">
        {/* Banner de Apresentação */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 mb-8 p-6 rounded-3xl bg-gradient-to-r from-[#00D4FF]/10 via-[#0A1520] to-[#00FF87]/10 border border-[#132435]">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00D4FF]/20 border border-[#00D4FF] font-mono text-[11px] text-[#00D4FF] font-bold mb-2">
              🎓 PROJETO TÉCNICO EM TI • FUNEC RIACHO
            </div>
            <h1 className="font-syne font-black text-2xl md:text-3xl text-white uppercase tracking-tight">
              Central de Demonstração ao Vivo <span className="text-[#00FF87]">(Modo Banca)</span>
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleFullscreen}
              className="px-4 py-2.5 rounded-xl bg-[#060D14] border border-[#132435] hover:border-[#00D4FF] text-xs font-mono font-bold text-[#CDE8F0] hover:text-[#00D4FF] transition-all cursor-pointer flex items-center gap-2"
            >
              📺 Modo Telão (Full Screen)
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
          {[
            { id: "audio", label: "1. Voz Clonada", sub: "Golpe do Parente", icon: "🎙️", color: "#FF3B5C" },
            { id: "seal", label: "2. Selo C2PA", sub: "Tamper-Evidence", icon: "🛡️", color: "#00FF87" },
            { id: "whatsapp", label: "3. WhatsApp", sub: "Interativo na Tela", icon: "💬", color: "#25D366" },
            { id: "forensic", label: "4. Quadro Forense", sub: "Pipeline Técnico", icon: "⚖️", color: "#00D4FF" }
          ].map((tab) => {
            const isSelected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`p-4 rounded-2xl border text-left transition-all cursor-pointer flex items-center gap-3 ${
                  isSelected
                    ? "bg-[#0A1520] border-white shadow-xl scale-102"
                    : "bg-[#060D14]/80 border-[#132435] hover:border-white/30 text-[#8BAAC0]"
                }`}
                style={{ borderColor: isSelected ? tab.color : undefined }}
              >
                <span className="text-2xl">{tab.icon}</span>
                <div>
                  <h4 className={`font-syne font-bold text-sm ${isSelected ? "text-white" : "text-[#CDE8F0]"}`}>
                    {tab.label}
                  </h4>
                  <span className="font-mono text-[10px] text-[#8BAAC0] block">{tab.sub}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="transition-all">
          {activeTab === "audio" && <AudioDeepfakeDemo />}
          {activeTab === "seal" && <AuthenticitySealDemo />}
          {activeTab === "whatsapp" && <WhatsAppSimulator />}
          {activeTab === "forensic" && <ForensicTimeline />}
        </div>
      </main>

      <Footer />
    </div>
  );
}
