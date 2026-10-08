import test from "node:test";
import assert from "node:assert/strict";
import { createTranscriptionScope } from "../src/services/transcriptionScope.js";
import { createPrivacyStorage } from "../src/services/privacyStorage.js";

function controlledCrypto() {
  let count = 0;
  return { getRandomValues(bytes) { bytes.fill(++count); return bytes; } };
}

test("anonymous ASR nonce is stable only inside the same live tab", () => {
  const source = controlledCrypto();
  const tabA = createTranscriptionScope(source);
  const tabB = createTranscriptionScope(source);
  const headerA = tabA.headers();
  assert.match(headerA["X-Verify-Analysis-Scope"], /^[a-f0-9]{32}$/);
  assert.deepEqual(tabA.headers(), headerA);
  assert.notDeepEqual(tabB.headers(), headerA);
  tabA.dispose();
  assert.notDeepEqual(tabA.headers(), headerA);
  tabB.dispose();
});

test("logout, account changes and remote privacy resets discard anonymous nonce", () => {
  const storage = createPrivacyStorage();
  const tab = createTranscriptionScope(controlledCrypto(), storage.subscribeReset);
  for (const reason of ["logout", "account-change"]) {
    const previous = tab.headers();
    storage.clearSensitiveData({ reason, remote: true });
    assert.notDeepEqual(tab.headers(), previous);
  }
  const previous = tab.headers();
  storage.syncAccount({ id: "another-account" });
  assert.notDeepEqual(tab.headers(), previous);
  tab.dispose();
});

test("missing or blocked secure randomness disables reuse without Math.random fallback", () => {
  for (const crypto of [undefined, {}, { getRandomValues() { throw new Error("blocked"); } }]) {
    const tab = createTranscriptionScope(crypto);
    assert.deepEqual(tab.headers(), {});
    assert.deepEqual(tab.headers(), {});
    tab.dispose();
  }
});

test("nonce is not placed in browser storage or request URLs", async () => {
  const { readFileSync } = await import("node:fs");
  const source = readFileSync(new URL("../src/services/transcriptionScope.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /localStorage|sessionStorage|Math\.random|URLSearchParams/);
  const apiSource = readFileSync(new URL("../src/services/api.js", import.meta.url), "utf8");
  for (const endpoint of ["/upload", "/verificar/audio-rapido", "/verificar/completo", "/whatsapp/simulate"]) {
    const line = apiSource.split("\n").find((candidate) => candidate.includes(`api.post("${endpoint}"`));
    assert.ok(line.includes("transcriptionScopeHeaders()"), endpoint);
    assert.ok(!line.includes("params:"), endpoint);
  }
});
