import { useSyncExternalStore } from "react";
import { accessibilityStore, nextTextSize } from "../services/accessibility";

export function useAccessibility() {
  const mode = useSyncExternalStore(accessibilityStore.subscribe, accessibilityStore.getSnapshot, () => "normal");
  return {
    mode,
    easyMode: mode === "elderly",
    toggleEasyMode: () => accessibilityStore.setMode(mode === "elderly" ? "normal" : "elderly"),
    cycleTextSize: () => accessibilityStore.setMode(nextTextSize(mode)),
  };
}
