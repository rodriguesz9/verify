import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="relative z-10 border-t border-[#132435] mt-20 bg-[#04080C]">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
          <div className="md:col-span-2">
            <h3 className="font-syne font-black text-2xl tracking-[6px] text-text mb-6">
              VERIFY
            </h3>
            <p className="font-mono text-[13px] leading-relaxed max-w-sm text-[#3A6070]">
              Ajudando você a descobrir a verdade por trás das notícias. 
              Tecnologia avançada, agora fácil de usar para todos.
            </p>
          </div>
          
          <div>
            <span className="font-mono text-[10px] tracking-[5px] block mb-8 text-cyan uppercase font-bold">MENU</span>
            <ul className="flex flex-col gap-4 font-mono text-[12px] uppercase tracking-widest">
              <li><Link to="/app" className="text-[#3A6070] no-underline hover:text-cyan transition-colors">Verificar</Link></li>
              <li><Link to="/dashboard" className="text-[#3A6070] no-underline hover:text-cyan transition-colors">Meu Painel</Link></li>
              <li><Link to="/history" className="text-[#3A6070] no-underline hover:text-cyan transition-colors">Histórico</Link></li>
              <li><Link to="/plans" className="text-[#3A6070] no-underline hover:text-cyan transition-colors">Planos</Link></li>
            </ul>
          </div>

          <div>
            <span className="font-mono text-[10px] tracking-[5px] block mb-8 text-cyan uppercase font-bold">LINKS ÚTEIS</span>
            <ul className="flex flex-col gap-4 font-mono text-[12px] uppercase tracking-widest">
              <li><Link to="/terms" className="text-[#3A6070] no-underline hover:text-cyan transition-colors">Termos de Uso</Link></li>
              <li><Link to="/privacy" className="text-[#3A6070] no-underline hover:text-cyan transition-colors">Privacidade</Link></li>
              <li><Link to="/limitations" className="text-[#3A6070] no-underline hover:text-cyan transition-colors">Limitações de IA</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[#132435] mt-16 pt-10 flex flex-col md:flex-row justify-between items-center gap-6">
          <p className="font-mono text-[10px] text-[#1A3A50] tracking-[2px] uppercase font-bold">
            &copy; {new Date().getFullYear()} Verify – A verdade ao seu alcance.
          </p>
          <div className="flex gap-8 font-mono text-[9px] text-[#1A3A50] tracking-[3px] uppercase font-bold">
             <span>Brasil</span>
             <span>Criptografado</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
