// Vite-only visual fixture. Not an application route or a production analysis.
import React, {useState} from "react";
import {createRoot} from "react-dom/client";
import AnimatedScore from "../src/components/report/AnimatedScore";
import "../src/index.css";

function ScorePreview() {
  const [revision, setRevision] = useState(0);
  return <main className="max-w-2xl mx-auto p-6 space-y-6">
    <h1 className="text-2xl font-bold">Controle local da animação</h1>
    <p>Valores fictícios para teste visual. Não são resultados de verificação.</p>
    <AnimatedScore key={revision} value={90} label="Controle visual · alvo 90" />
    <AnimatedScore value={0} label="Controle visual · alvo zero" />
    <AnimatedScore value={null} label="Controle visual · sem evidência" />
    <button className="bg-[#132435] rounded-lg px-4 py-3" onClick={() => setRevision((value) => value + 1)}>Reiniciar animação</button>
  </main>;
}
createRoot(document.getElementById("root")).render(<ScorePreview />);
