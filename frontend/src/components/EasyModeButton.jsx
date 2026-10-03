import { Accessibility, Check } from "lucide-react";
import { useAccessibility } from "../hooks/useAccessibility";

export default function EasyModeButton({ className = "" }) {
  const { easyMode, toggleEasyMode } = useAccessibility();
  return (
    <button type="button" className={`easy-mode-toggle ${className}`} aria-pressed={easyMode} onClick={toggleEasyMode}>
      <Accessibility size={20} aria-hidden="true" />
      <span>{easyMode ? "Modo Fácil: ativo" : "Modo Fácil"}</span>
      {easyMode && <Check size={18} aria-hidden="true" />}
    </button>
  );
}
