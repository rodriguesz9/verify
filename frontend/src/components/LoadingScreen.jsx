const STAGES = [
  { label: "ACESSANDO SISTEMA", desc: "Preparando as ferramentas de busca..." },
  { label: "PESQUISANDO FATOS", desc: "Cruzando informações em fontes confiáveis..." },
  { label: "COMPARANDO DADOS", desc: "Nossa inteligência está decidindo o veredito..." }
];

export default function LoadingScreen({ stage = 0 }) {
  const s = STAGES[stage] || STAGES[0];
  return (
    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#04080C] px-6">
       <div className="mb-12 text-center animate-fade-in">
          <h2 className="font-syne font-black text-3xl text-[#CDE8F0] tracking-[10px] mb-4 uppercase">Verificando</h2>
          <p className="font-mono text-[12px] tracking-[5px] text-cyan uppercase font-bold animate-pulse">{s.label}</p>
       </div>
       <div className="h-2 w-64 bg-[#132435] rounded-full overflow-hidden mb-8 shadow-inner">
          <div className="h-full bg-gradient-to-r from-cyan to-green-400 transition-all duration-1000 shadow-[0_0_10px_#00D4FF]" style={{ width: `${(stage + 1) * 33.3}%` }}/>
       </div>
       <p className="font-mono text-[13px] text-[#3A6070] italic text-center max-w-xs">"{s.desc}"</p>
    </div>
  );
}
