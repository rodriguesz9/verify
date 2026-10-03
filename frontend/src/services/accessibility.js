const MODES = ["normal", "large", "xlarge", "elderly"];
const STORAGE_KEY = "verify_accessibility_v1";

export function normalizeAccessibilityMode(mode, legacyEasy) {
  if (legacyEasy === "true") return "elderly";
  if (legacyEasy === "false" && mode === "elderly") return "normal";
  return MODES.includes(mode) ? mode : "normal";
}

export function nextTextSize(mode) {
  return mode === "normal" ? "large" : mode === "large" ? "xlarge" : "normal";
}

export function createAccessibilityStore(host) {
  let mode = "normal";
  let initialized = false;
  const listeners = new Set();
  const read = () => {
    try {
      const current = host?.localStorage.getItem(STORAGE_KEY);
      if (MODES.includes(current)) return current;
      return normalizeAccessibilityMode(host?.localStorage.getItem("verify_font_size"), host?.localStorage.getItem("verify_elderly_mode"));
    } catch { return mode; }
  };
  const apply = () => {
    const root = host?.document?.documentElement;
    if (!root) return;
    if (mode === "normal") root.removeAttribute("data-font-size");
    else root.setAttribute("data-font-size", mode);
    if (mode === "elderly") root.setAttribute("data-elderly-mode", "true");
    else root.removeAttribute("data-elderly-mode");
  };
  const initialize = () => {
    if (initialized) return;
    initialized = true;
    mode = read();
    apply();
  };
  const storageChanged = (event) => {
    if (event.key !== null && ![STORAGE_KEY, "verify_font_size", "verify_elderly_mode"].includes(event.key)) return;
    const next = read();
    if (next === mode) return;
    mode = next;
    apply();
    listeners.forEach((listener) => listener());
  };
  return {
    initialize,
    getSnapshot: () => { initialize(); return mode; },
    setMode: (next) => {
      initialize();
      if (!MODES.includes(next)) return;
      mode = next;
      try {
        host?.localStorage.setItem(STORAGE_KEY, mode);
        host?.localStorage.setItem("verify_font_size", mode);
        host?.localStorage.setItem("verify_elderly_mode", String(mode === "elderly"));
      } catch { /* The preference still works when browser storage is unavailable. */ }
      apply();
      listeners.forEach((listener) => listener());
    },
    subscribe: (listener) => {
      if (!listeners.size) host?.addEventListener("storage", storageChanged);
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
        if (!listeners.size) host?.removeEventListener("storage", storageChanged);
      };
    },
  };
}

export const accessibilityStore = createAccessibilityStore(typeof window === "undefined" ? undefined : window);
