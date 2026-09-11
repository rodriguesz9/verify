import { useState, useRef, useEffect } from "react";
import { simulateWhatsApp } from "../../services/api";

const PRESET_MESSAGES = [
  {
    label: "🚨 Golpe do Pix Aprovado",
    text: "URGENTE: Seu Pix no valor de R$ 4.890,00 foi aprovado pela Caixa. Para liberar o saldo na sua conta, pague a taxa de R$ 34,90 no link: pix-libera-caixa.site/pagar"
  },
  {
    label: "📦 Falsa Taxa dos Correios",
    text: "Correios Informa: Sua encomenda tributada BR948271032 está retida na alfândega de Curitiba. Efetue a regularização de R$ 49,90 em até 2 horas para evitar devolução: correios-rastreio-taxa.online"
  },
  {
    label: "👵 Golpe do Filho / Celular Novo",
    text: "Oi mãe, caí na rua agora e meu celular quebrou todo a tela. Tô usando esse número provisório. Preciso pagar o guincho agora senão eles não levam o carro, me manda 280 no Pix por favor!"
  }
];

export default function WhatsAppSimulator() {
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "👋 Olá! Sou o *Verify*, assistente de checagem de fatos e proteção contra golpes.\n\nEnvie qualquer notícia, link, áudio ou mensagem suspeita que eu verifico na hora para você!",
      time: "Agora"
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [typing, setTyping] = useState(false);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const handleSend = async (messageToSend) => {
    const text = messageToSend || inputText;
    if (!text.trim() || typing) return;

    const userMsg = {
      sender: "user",
      text: text.trim(),
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setTyping(true);

    try {
      const data = await simulateWhatsApp(text.trim());
      const botResponse = data.whatsapp_response || "Erro ao processar verificação.";

      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: botResponse,
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          }
        ]);
        setTyping(false);
      }, 700);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: "⚠️ Não foi possível verificar esta mensagem no momento. Tente novamente em alguns segundos.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
      setTyping(false);
    }
  };

  return (
    <div className="bg-[#0A1520] border border-[#132435] rounded-3xl p-8 max-w-4xl mx-auto shadow-2xl">
      {/* Header */}
      <div className="text-center mb-8">
        <span className="font-mono text-xs text-[#25D366] tracking-widest uppercase font-bold block mb-2">
          FEATURE #3 • INTERATIVIDADE AO VIVO
        </span>
        <h2 className="font-syne font-black text-3xl md:text-4xl text-[#CDE8F0] uppercase tracking-tight">
          Bot de WhatsApp <span className="text-[#25D366]">(Simulador na Tela)</span>
        </h2>
        <p className="font-mono text-sm text-[#3A6070] mt-3 max-w-2xl mx-auto">
          A banca e a plateia podem participar enviando mensagens para ver o bot respondendo ao vivo como se estivesse no smartphone.
        </p>
      </div>

      {/* Quick Suggestion Buttons */}
      <div className="flex flex-wrap gap-2 mb-6 justify-center">
        {PRESET_MESSAGES.map((preset, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSend(preset.text)}
            className="px-4 py-2 rounded-xl bg-[#060D14] border border-[#132435] hover:border-[#25D366] text-[#CDE8F0] font-mono text-xs transition-all cursor-pointer hover:bg-[#25D366]/10"
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Phone Mockup Frame */}
      <div className="max-w-md mx-auto rounded-[2.5rem] overflow-hidden border-4 border-[#1F2C34] bg-[#0B141B] shadow-[0_25px_60px_rgba(0,0,0,0.8)]">
        {/* WhatsApp Top Bar */}
        <div className="bg-[#1F2C34] px-4 py-3 flex items-center gap-3 border-b border-white/5">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#00D4FF] to-[#00FF87] flex items-center justify-center font-syne font-black text-[#04080C] text-sm shadow">
            V
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-syne font-bold text-sm text-[#E9EDEF] truncate">Verify Checagem</h4>
            <span className="font-mono text-[11px] text-[#25D366]">
              {typing ? "digitando laudo..." : "online • proteção ativa"}
            </span>
          </div>
          <div className="flex gap-3 text-[#8696A0] text-sm">
            <span>📞</span>
            <span>⋮</span>
          </div>
        </div>

        {/* WhatsApp Chat Area */}
        <div className="h-96 overflow-y-auto p-4 space-y-3 bg-[#0B141B] bg-opacity-95">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-md whitespace-pre-line text-xs font-sans leading-relaxed ${
                  m.sender === "user"
                    ? "bg-[#005C4B] text-[#E9EDEF] rounded-tr-none"
                    : "bg-[#202C33] text-[#D1D7DB] rounded-tl-none border border-white/5"
                }`}
              >
                {m.text}
                <div className="text-[10px] text-right mt-1 text-[#8696A0] flex justify-end items-center gap-1">
                  <span>{m.time}</span>
                  {m.sender === "user" && <span className="text-[#53BDEB]">✓✓</span>}
                </div>
              </div>
            </div>
          ))}

          {typing && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-[#202C33] w-fit text-[#8696A0] font-mono text-xs">
              <span className="w-2 h-2 rounded-full bg-[#25D366] animate-bounce" />
              <span className="w-2 h-2 rounded-full bg-[#25D366] animate-bounce [animation-delay:0.2s]" />
              <span className="w-2 h-2 rounded-full bg-[#25D366] animate-bounce [animation-delay:0.4s]" />
              <span className="ml-1 text-[11px] text-[#25D366]">Analisando nas camadas forenses...</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* WhatsApp Input Bar */}
        <div className="bg-[#1F2C34] p-3 flex items-center gap-2 border-t border-white/5">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Digite uma mensagem para a banca testar..."
            className="flex-1 bg-[#2A3942] text-[#E9EDEF] text-xs font-sans rounded-full px-4 py-2.5 outline-none placeholder-[#8696A0]"
          />
          <button
            type="button"
            onClick={() => handleSend()}
            disabled={typing || !inputText.trim()}
            className="w-10 h-10 rounded-full bg-[#25D366] text-[#04080C] flex items-center justify-center font-bold hover:scale-105 active:scale-95 transition-all cursor-pointer shadow disabled:opacity-50"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
