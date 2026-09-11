import { useEffect, useState } from "react";

export default function SplashScreen() {
  const [visible, setVisible] = useState(true);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[999] flex flex-col items-center justify-center" style={{ backgroundColor: "#04080C", overflow: "hidden" }}>
      {/* Dynamic Background Elements */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px] animate-pulse" style={{ backgroundColor: "#00D4FF10" }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] rounded-full blur-[80px] animate-pulse" style={{ backgroundColor: "#00FF8705", animationDelay: '1s' }} />
      </div>

      {/* Grid Pattern */}
      <div className="pointer-events-none absolute inset-0" style={{
        backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
        backgroundSize: "64px 64px", opacity: .15 }} />

      {/* Scanline Animation */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="w-full h-[150px] absolute top-[-150px] animate-scanline" style={{ background: "linear-gradient(to bottom, transparent, rgba(0,212,255,0.05), transparent)" }} />
      </div>

      <div className="relative flex flex-col items-center" style={{ gap: "2rem" }}>
        {/* Animated Hex Logo */}
        <div className="relative group">
          <div className="absolute inset-0 blur-2xl rounded-full scale-50 opacity-50" style={{ backgroundColor: "#00D4FF30" }} />
          <svg width="100" height="100" viewBox="0 0 28 28" className="relative">
            <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" 
                     fill="none" 
                     stroke="#00D4FF" 
                     strokeWidth="0.8" 
                     className="animate-dash" />
            <polygon points="14,5 23,10 23,18 14,23 5,18 5,10" 
                     fill="none" 
                     stroke="#00FF87" 
                     strokeWidth="0.5" 
                     opacity="0.6"
                     className="animate-dash-reverse" />
            <circle cx="14" cy="14" r="3.5" fill="#00D4FF" className="animate-pulse shadow-inner" />
          </svg>
        </div>

        {/* Text Brand */}
        <div className="text-center overflow-hidden">
          <div className="animate-slide-up">
            <h1 className="font-syne font-black text-4xl tracking-[18px] text-[#CDE8F0] mb-3 translate-x-[9px] select-none">
              VERIFY
            </h1>
            <div className="flex flex-col items-center" style={{ gap: "0.5rem" }}>
              <p className="font-mono text-[9px] tracking-[6px] text-[#00FF87] uppercase font-bold">
                A verdade ao alcance de todos
              </p>
              <div className="h-[1px] w-12 mt-1" style={{ background: "linear-gradient(to right, transparent, rgba(0,212,255,0.25), transparent)" }} />
            </div>
          </div>
        </div>
      </div>

      {/* Loading Bar at Bottom */}
      <div className="absolute bottom-16 w-48 h-[2px] rounded-full overflow-hidden" style={{ backgroundColor: "#132435" }}>
        <div className="h-full animate-loading-bar" style={{ background: "linear-gradient(to right, #00D4FF, #00FF87)" }} />
      </div>

      <style>{`
        @keyframes scanline {
          0% { top: -150px; }
          100% { top: 100%; }
        }
        .animate-scanline {
          animation: scanline 4s linear infinite;
        }
        @keyframes dash {
          to { stroke-dashoffset: 0; }
        }
        .animate-dash {
          stroke-dasharray: 80;
          stroke-dashoffset: 80;
          animation: dash 3s ease-out forwards;
        }
        .animate-dash-reverse {
          stroke-dasharray: 60;
          stroke-dashoffset: -60;
          animation: dash 3.5s ease-out forwards;
        }
        @keyframes slide-up {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .animate-slide-up {
          animation: slide-up 1s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }
        @keyframes loading-bar {
          0% { width: 0; transform: translateX(-100%); }
          50% { width: 60%; transform: translateX(50%); }
          100% { width: 100%; transform: translateX(200%); }
        }
        .animate-loading-bar {
          animation: loading-bar 2.5s infinite ease-in-out;
        }
      `}</style>
    </div>
  );
}
