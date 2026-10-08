import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createPrivacyStorage } from "../src/services/privacyStorage.js";
import { getOfflineCache, getOfflineCount, getOfflineReport, saveToOfflineCache } from "../src/services/offlineCache.js";

function createHost() {
  const handlers = new Map();
  const writes = [];
  const createStorage = () => {
    const values = new Map();
    return {
      values,
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => { values.set(key, value); writes.push({ key, value }); },
      removeItem: (key) => values.delete(key),
      clear: () => { throw new Error("Broad clear() is forbidden"); },
    };
  };
  return {
    localStorage: createStorage(), sessionStorage: createStorage(), writes, handlers,
    addEventListener: (name, listener) => handlers.set(name, listener),
    removeEventListener: (name, listener) => { if (handlers.get(name) === listener) handlers.delete(name); },
  };
}

test("reports are bounded to the tab, never automatically persisted locally", () => {
  const host = createHost();
  const store = createPrivacyStorage(host);
  store.syncAccount(null);
  assert.equal(store.storeReport({ summary: "Consulta privada", pdf_token: "bearer-control" }, "Texto privado"), true);
  assert.equal(host.localStorage.values.size, 0);
  assert.equal(host.sessionStorage.values.has("verify_result"), false);
  assert.deepEqual(store.readReport(), { result: { summary: "Consulta privada", pdf_token: "bearer-control" }, query: "Texto privado" });
  assert.equal(store.storeReport({ summary: "x".repeat(1024 * 1024) }, ""), false);
  assert.equal(store.storeReport({ summary: "á".repeat(600000) }, ""), false, "bound UTF-8 bytes, not only ASCII characters");
  assert.equal(store.storeReport({}, "x".repeat(65537)), false);
});

test("missing verdict and index are preserved, not replaced by suspect or zero", () => {
  const store = createPrivacyStorage(createHost());
  store.syncAccount(null);
  store.storeReport({ analysis_status: "inconclusive", score: null }, "Controle");
  const { result } = store.readReport();
  assert.equal(result.score, null);
  assert.equal(Object.hasOwn(result, "verdict"), false);
  store.storeReport({ summary: "Sem índice" });
  assert.equal(Object.hasOwn(store.readReport().result, "score"), false);
});

test("logout wipes only owned sensitive keys in both stores, preserving preferences and other applications", () => {
  const host = createHost();
  const store = createPrivacyStorage(host);
  store.syncAccount({ id: 1 });
  store.storeReport({ summary: "Privado" }, "Consulta privada");
  const sensitive = ["verify_result", "verify_query", "verifai_result", "verifai_query", "verify_offline_cache", "verifai_offline_cache",
    "verify_access", "verify_refresh", "verifai_access", "verifai_refresh"];
  const preferences = ["verify_accessibility_v1", "verify_font_size", "verify_elderly_mode", "verify_theme", "other_app_report"];
  for (const target of [host.localStorage, host.sessionStorage]) {
    for (const key of sensitive) target.setItem(key, "sensitive");
    for (const key of preferences) target.setItem(key, "preserve");
  }
  store.clearSensitiveData({ reason: "logout", broadcast: true });
  assert.equal(store.readReport(), null);
  for (const target of [host.localStorage, host.sessionStorage]) {
    for (const key of sensitive) assert.equal(target.getItem(key), null);
    for (const key of preferences) assert.equal(target.getItem(key), "preserve");
    assert.equal(target.getItem("verify_session_report_v1"), null);
    assert.equal(target.getItem("verify_analysis_owner_v1"), null);
  }
  const signal = host.writes.findLast(({ key }) => key === "verify_privacy_reset_v1");
  assert.equal(JSON.parse(signal.value).reason, "logout");
  assert.doesNotMatch(signal.value, /Privado|Consulta|user:|bearer/);
  assert.equal(host.localStorage.getItem("verify_privacy_reset_v1"), null);
});

test("account switch rejects late analysis and cannot resurrect it through A → B → A", async () => {
  const store = createPrivacyStorage(createHost());
  store.syncAccount({ id: "A" });
  const pendingScope = store.captureScope();
  store.storeReport({ summary: "A" }, "Conta A", pendingScope);
  store.syncAccount({ id: "B" });
  assert.equal(store.readReport(), null);
  assert.equal(store.storeReport({ summary: "Resposta atrasada A" }, "A", pendingScope), false);
  store.syncAccount({ id: "A" });
  assert.equal(store.isScopeCurrent(pendingScope), false);
  assert.equal(store.storeReport({ summary: "Resposta antiga A" }, "A", pendingScope), false);
  assert.equal(store.storeReport({ summary: "Resposta nova A" }, "A", store.captureScope()), true);
});

test("logout followed by anonymous use cannot read an authenticated report", () => {
  const store = createPrivacyStorage(createHost());
  store.syncAccount({ id: 1 });
  const oldScope = store.captureScope();
  store.storeReport({ summary: "Conta" });
  store.clearSensitiveData({ reason: "logout" });
  store.syncAccount(null);
  assert.equal(store.readReport(), null);
  assert.equal(store.storeReport({ summary: "Antigo" }, "", oldScope), false);
  assert.equal(store.storeReport({ summary: "Visitante" }), true);
});

test("same verified account or anonymous reload preserves current tab report, not legacy cache", () => {
  for (const user of [null, { id: 1 }]) {
    const host = createHost();
    const first = createPrivacyStorage(host);
    first.syncAccount(user);
    first.storeReport({ summary: "Atual" }, "Consulta");
    host.localStorage.setItem("verify_offline_cache", "legacy");
    host.sessionStorage.setItem("verifai_result", "legacy");
    host.sessionStorage.setItem("verify_access", "old-token");
    const afterReload = createPrivacyStorage(host);
    assert.equal(afterReload.readReport(), null, "must wait for authentication initialization");
    afterReload.syncAccount(user);
    assert.equal(afterReload.readReport().result.summary, "Atual");
    assert.equal(host.localStorage.getItem("verify_offline_cache"), null);
    assert.equal(host.sessionStorage.getItem("verifai_result"), null);
    assert.equal(host.sessionStorage.getItem("verify_access"), null);
  }
});

test("lost cookie after reload wipes previous owner instead of importing unowned legacy data", () => {
  const host = createHost();
  const first = createPrivacyStorage(host);
  first.syncAccount({ id: 1 });
  first.storeReport({ summary: "Conta antiga" });
  const next = createPrivacyStorage(host);
  next.syncAccount(null);
  assert.equal(next.readReport(), null);
  host.sessionStorage.setItem("verify_result", JSON.stringify({ summary: "Sem proprietário" }));
  next.syncAccount(null);
  assert.equal(next.readReport(), null);
  assert.equal(host.sessionStorage.getItem("verify_result"), null);
});

test("blocked storage still supports in-memory report and immediate logout cleanup", () => {
  const host = {
    get localStorage() { throw new Error("blocked"); },
    get sessionStorage() { throw new Error("blocked"); },
  };
  const store = createPrivacyStorage(host);
  assert.doesNotThrow(() => store.syncAccount({ id: 1 }));
  assert.equal(store.storeReport({ summary: "Somente memória" }), true);
  assert.equal(store.readReport().result.summary, "Somente memória");
  assert.doesNotThrow(() => store.clearSensitiveData({ broadcast: true }));
  assert.equal(store.readReport(), null);
});

test("malformed, oversized or mismatched persisted reports never produce an invented verdict", () => {
  const host = createHost();
  const store = createPrivacyStorage(host);
  store.syncAccount({ id: 1 });
  for (const value of ["broken", "x".repeat(1024 * 1024 + 1),
    JSON.stringify({ schema_version: 1, owner: "user:2", result: { verdict: "Authentic" }, query: "" }),
    JSON.stringify({ schema_version: 1, owner: "user:1", result: [], query: "" })]) {
    host.sessionStorage.setItem("verify_session_report_v1", value);
    assert.equal(store.readReport(), null);
  }
});

test("cross-tab reset is deduplicated, removes sensitive state and preserves preferences", () => {
  const host = createHost();
  const store = createPrivacyStorage(host);
  store.syncAccount({ id: 1 });
  store.storeReport({ summary: "Outra aba" });
  host.localStorage.setItem("verify_accessibility_v1", "elderly");
  const signals = [];
  const stopFirst = store.subscribeReset((event) => signals.push(event));
  const stopSecond = store.subscribeReset(() => {});
  assert.equal(host.handlers.size, 1);
  host.handlers.get("storage")({ key: "unrelated", newValue: "ignored" });
  assert.equal(store.readReport().result.summary, "Outra aba");
  host.handlers.get("storage")({ key: "verify_privacy_reset_v1", newValue: JSON.stringify({ reason: "logout", nonce: "control" }) });
  assert.equal(store.readReport(), null);
  assert.deepEqual(signals, [{ reason: "logout", remote: true }]);
  assert.equal(host.localStorage.getItem("verify_accessibility_v1"), "elderly");
  stopFirst();
  assert.equal(host.handlers.size, 1);
  stopSecond();
  assert.equal(host.handlers.size, 0);
});

test("remote logout permits a fresh anonymous analysis without reusing the other account", () => {
  const host = createHost();
  const store = createPrivacyStorage(host);
  store.syncAccount({ id: 1 });
  const authenticatedScope = store.captureScope();
  store.storeReport({ summary: "Conta anterior" });
  const unsubscribe = store.subscribeReset(({ reason }) => {
    // AuthProvider applies the same transition for local and remote logout.
    if (reason === "logout") store.syncAccount(null);
  });
  host.handlers.get("storage")({ key: "verify_privacy_reset_v1", newValue: JSON.stringify({ reason: "logout", nonce: "other-tab" }) });
  assert.equal(store.readReport(), null);
  assert.equal(store.captureScope().owner, "anonymous");
  assert.equal(store.storeReport({ summary: "Tarefa antiga" }, "", authenticatedScope), false);
  assert.equal(store.storeReport({ summary: "Nova consulta anônima" }), true);
  assert.equal(store.readReport().result.summary, "Nova consulta anônima");
  unsubscribe();
});

test("one failing reset subscriber cannot stop cleanup or remaining subscribers", () => {
  const store = createPrivacyStorage(createHost());
  store.syncAccount(null);
  store.storeReport({ summary: "Controle" });
  let called = false;
  store.subscribeReset(() => { throw new Error("subscriber failed"); });
  store.subscribeReset(() => { called = true; });
  assert.doesNotThrow(() => store.clearSensitiveData());
  assert.equal(called, true);
  assert.equal(store.readReport(), null);
});

test("retired offline feature cannot save defaults or expose historical reports", () => {
  assert.equal(saveToOfflineCache({ summary: "Privado" }), null);
  assert.deepEqual(getOfflineCache(), []);
  assert.equal(getOfflineReport("legacy"), null);
  assert.equal(getOfflineCount(), 0);
  const home = readFileSync(new URL("../src/pages/Home.jsx", import.meta.url), "utf8");
  const auth = readFileSync(new URL("../src/hooks/useAuth.jsx", import.meta.url), "utf8");
  const api = readFileSync(new URL("../src/services/api.js", import.meta.url), "utf8");
  assert.doesNotMatch(home, /saveToOfflineCache|sessionStorage\.setItem|localStorage\.setItem|console\.error/);
  assert.match(home, /captureAnalysisScope\(\)/);
  assert.match(home, /isAnalysisScopeCurrent\(scope\)/);
  assert.match(auth, /syncAnalysisAccount\(me/);
  assert.match(auth, /syncAnalysisAccount\(null/);
  assert.match(api, /clearSensitiveBrowserData\(\{ broadcast: true, reason: "logout" \}\)/);
});
