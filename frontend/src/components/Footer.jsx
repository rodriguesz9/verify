import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="relative z-10 border-t border-[#132435] mt-16 bg-[#04080C]">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 py-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8">
          <div className="md:col-span-2">
            <h3 className="font-syne font-black text-2xl tracking-[4px] text-[#CDE8F0] mb-3">
              VERIFY
            </h3>
            <p className="font-mono text-xs leading-relaxed max-w-sm text-[#8AA2B4]">
              Protegendo famílias e cidadãos contra notícias falsas, fraudes e golpes do WhatsApp. 
              Tecnologia de ponta com linguagem simples para todos.
            </p>
          </div>
          
          <div>
            <span className="font-mono text-[11px] tracking-[2px] block mb-4 text-[#00D4FF] uppercase font-bold">NAVEGAÇÃO</span>
            <ul className="flex flex-col gap-2.5 font-mono text-xs uppercase tracking-wider">
              <li><Link to="/app" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Checar Notícia</Link></li>
              <li><Link to="/dashboard" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Painel</Link></li>
              <li><Link to="/history" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Histórico</Link></li>
              <li><Link to="/mission" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Nossa Missão</Link></li>
            </ul>
          </div>

          <div>
            <span className="font-mono text-[11px] tracking-[2px] block mb-4 text-[#00D4FF] uppercase font-bold">TRANSPARÊNCIA</span>
            <ul className="flex flex-col gap-2.5 font-mono text-xs uppercase tracking-wider">
              <li><Link to="/terms" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Termos de Uso</Link></li>
              <li><Link to="/privacy" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Privacidade</Link></li>
              <li><Link to="/limitations" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Limitações de IA</Link></li>
              <li><Link to="/suggestions" className="text-[#8AA2B4] no-underline hover:text-[#00D4FF] transition-colors">Sugestões</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[#132435] mt-10 pt-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="font-mono text-xs text-[#5A7E94] tracking-wide text-center md:text-left">
            &copy; {new Date().getFullYear()} Verify – A verdade ao alcance de todos.
          </p>
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 font-mono text-[10px] text-[#5A7E94] uppercase font-bold">
             <span>🇧🇷 Feito no Brasil</span>
             <span>🛡️ 100% Gratuito</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
