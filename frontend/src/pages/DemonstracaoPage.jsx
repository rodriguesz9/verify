import { useState } from "react";
import { AudioLines, BadgeCheck, Expand, MessageCircle, ScanSearch } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import AudioDeepfakeDemo from "../components/demonstracao/AudioDeepfakeDemo";
import AuthenticitySealDemo from "../components/demonstracao/AuthenticitySealDemo";
import WhatsAppSimulator from "../components/demonstracao/WhatsAppSimulator";
import ForensicTimeline from "../components/demonstracao/ForensicTimeline";

const TABS = [
  { id: "audio", label: "Análise da fala", sub: "Sinais de golpe", icon: AudioLines, color: "#FF3B5C" },
  { id: "seal", label: "Registro SHA-256", sub: "Integridade, não C2PA", icon: BadgeCheck, color: "#00FF87" },
  { id: "whatsapp", label: "WhatsApp", sub: "Teste interativo", icon: MessageCircle, color: "#25D366" },
  { id: "forensic", label: "Análise forense", sub: "Etapas da checagem", icon: ScanSearch, color: "#00D4FF" },
];

export default function DemonstracaoPage() {
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
        <div className="demo-page-header flex flex-col md:flex-row items-center justify-between gap-4 mb-8 p-4 sm:p-6 rounded-2xl bg-gradient-to-r from-[#00D4FF]/10 via-[#0A1520] to-[#00FF87]/10 border border-[#132435]">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00D4FF]/20 border border-[#00D4FF] font-mono text-[11px] text-[#00D4FF] font-bold mb-2">
              <ScanSearch size={13} /> AMBIENTE INTERATIVO
            </div>
            <h1 className="font-syne font-black text-2xl md:text-3xl text-white uppercase tracking-tight">
              Demonstração de Uso <span className="text-[#00FF87]">ao vivo</span>
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleFullscreen}
              className="px-4 py-2.5 rounded-xl bg-[#060D14] border border-[#132435] hover:border-[#00D4FF] text-xs font-mono font-bold text-[#CDE8F0] hover:text-[#00D4FF] transition-all cursor-pointer flex items-center gap-2"
            >
              <Expand size={15} /> Ampliar tela
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 mb-10">
          {TABS.map((tab, index) => {
            const isSelected = activeTab === tab.id;
            const Icon = tab.icon;
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
                <Icon size={22} className="shrink-0" style={{ color: isSelected ? tab.color : "#8BAAC0" }} />
                <div className="min-w-0 break-words">
                  <h4 className={`font-syne font-bold text-sm ${isSelected ? "text-white" : "text-[#CDE8F0]"}`}>
                    {index + 1}. {tab.label}
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
