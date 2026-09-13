import { useEffect, useRef, useState, useCallback } from "react";
import { Loader2 } from "lucide-react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const GOOGLE_SCRIPT_URL = "https://accounts.google.com/gsi/client";

export default function GoogleButton({ onSuccess, onError }) {
  const containerRef = useRef(null);
  const initializedRef = useRef(false);
  const [scriptLoaded, setScriptLoaded] = useState(false);

  const initGoogle = useCallback(async () => {
    if (!GOOGLE_CLIENT_ID || initializedRef.current) return;

    try {
      if (!window.google) {
        const script = document.createElement("script");
        script.src = GOOGLE_SCRIPT_URL;
        script.async = true;
        script.defer = true;
        await new Promise((resolve, reject) => {
          script.onload = resolve;
          script.onerror = reject;
        });
      }

      if (!window.google) return;

      google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          if (!response?.credential) {
            onError?.("Credencial do Google não recebida.");
            return;
          }

          try {
            await onSuccess(response.credential);
          } catch {
            onError?.("Não foi possível autenticar com Google.");
          }
        },
      });

      if (containerRef.current) {
        google.accounts.id.renderButton(containerRef.current, {
          theme: "outline",
          size: "large",
          width: "100%",
          shape: "rectangular",
          text: "signin_with",
          logo_alignment: "left",
        });
      }

      initializedRef.current = true;
      setScriptLoaded(true);
    } catch {
      setScriptLoaded(false);
    }
  }, []);

  useEffect(() => {
    initGoogle();
  }, [initGoogle]);

  return (
    <div className="flex justify-center">
      <div
        ref={containerRef}
        className={scriptLoaded ? "flex justify-center w-full" : "hidden"}
      />
      {!scriptLoaded && (
        <button
          type="button"
          disabled
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#4285F4]/30 bg-[#4285F4]/10 px-4 py-3 font-mono text-sm font-medium uppercase tracking-wider text-[#4285F4] opacity-50 cursor-not-allowed"
        >
          <Loader2 size={16} className="animate-spin" />
          Carregando Google...
        </button>
      )}
    </div>
  );
}
