// A nonce narrows anonymous ASR resumption to this live tab, not a login token.
// Never persist it, send it in URLs or reuse it after privacy/account resets.
import { subscribeAnalysisReset } from "./privacyStorage.js";

export function createTranscriptionScope(cryptoProvider, subscribeReset = () => () => {}) {
  let nonce;
  const reset = () => { nonce = undefined; };
  const unsubscribe = subscribeReset(reset);
  return {
    headers() {
      if (!nonce) {
        try {
          if (typeof cryptoProvider?.getRandomValues !== "function") return {};
          const bytes = new Uint8Array(16);
          cryptoProvider.getRandomValues(bytes);
          nonce = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
        } catch { return {}; }
      }
      return { "X-Verify-Analysis-Scope": nonce };
    },
    dispose() { reset(); unsubscribe(); },
  };
}

const tabScope = createTranscriptionScope(globalThis.crypto, subscribeAnalysisReset);
export const transcriptionScopeHeaders = () => tabScope.headers();
