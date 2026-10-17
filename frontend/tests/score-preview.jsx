// Vite-only visual fixture. Not an application route or a production analysis.
import React, {useState} from "react";
import {createRoot} from "react-dom/client";
import AnimatedScore from "../src/components/report/AnimatedScore";
import {accessibilityStore} from "../src/services/accessibility";
import "../src/index.css";

function ScorePreview() {
  const [revision, setRevision] = useState(0);
  return <main className="max-w-2xl mx-auto p-6 space-y-6">
    <h1 className="text-2xl font-bold">Controle local da animação</h1>
    <p>Valores fictícios para teste visual. Não são resultados de verificação.</p>
    <div className="flex flex-wrap gap-3">
      <button className="rounded-lg bg-[#132435] p-3" onClick={() => accessibilityStore.setMode("elderly")}>Ativar Modo Fácil</button>
      <button className="rounded-lg bg-[#132435] p-3" onClick={() => accessibilityStore.setMode("normal")}>Tamanho normal</button>
    </div>
    <section className="report-result-card min-w-0 rounded-xl border border-[#4C4427] bg-[#19180E] p-6 sm:p-8" aria-label="Controle responsivo sem resultado">
      <div className="report-result-layout grid min-w-0 gap-4 mb-4 lg:grid-cols-[minmax(0,1fr)_15rem] lg:items-center">
        <h2 className="report-result-title min-w-0 font-syne text-2xl font-black text-[#FFD65C]">Sem correspondência nas fontes consultadas</h2>
        <AnimatedScore value={null} color="#FFD65C" />
      </div>
      <p>Controle fictício de layout: nenhuma API foi consultada.</p>
    </section>
    <AnimatedScore key={revision} value={90} label="Controle visual · alvo 90" />
    <AnimatedScore value={0} label="Controle visual · alvo zero" />
    <AnimatedScore value={null} label="Controle visual · sem evidência" />
    <button className="bg-[#132435] rounded-lg px-4 py-3" onClick={() => setRevision((value) => value + 1)}>Reiniciar animação</button>
  </main>;
}
createRoot(document.getElementById("root")).render(<ScorePreview />);
