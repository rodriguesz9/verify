const REPORT_KEY = "verify_session_report_v1";
const OWNER_KEY = "verify_analysis_owner_v1";
const RESET_KEY = "verify_privacy_reset_v1";
const MAX_REPORT_BYTES = 1024 * 1024;
const MAX_QUERY_LENGTH = 65536;
const LEGACY_CACHE_KEYS = ["verify_offline_cache", "verifai_offline_cache"];
const LEGACY_REPORT_KEYS = ["verify_result", "verify_query", "verifai_result", "verifai_query"];
const LEGACY_TOKEN_KEYS = ["verify_access", "verify_refresh", "verifai_access", "verifai_refresh"];
const SENSITIVE_KEYS = [
  REPORT_KEY, OWNER_KEY,
  ...LEGACY_REPORT_KEYS, ...LEGACY_TOKEN_KEYS, ...LEGACY_CACHE_KEYS,
];

// Explicit owned keys only: never clear browser storage or accessibility/theme preferences.
export function createPrivacyStorage(host) {
  let owner = null;
  let initialized = false;
  let epoch = 0;
  let memoryReport = null;
  const listeners = new Set();
  const storage = (name) => {
    try { return host?.[name]; } catch { return undefined; }
  };
  const read = (name, key) => {
    try { return storage(name)?.getItem(key) ?? null; } catch { return null; }
  };
  const removeKeys = (name, keys) => {
    for (const key of keys) {
      try { storage(name)?.removeItem(key); } catch { /* Storage may be blocked. */ }
    }
  };
  const set = (name, key, value) => {
    try {
      const target = storage(name);
      if (!target) return false;
      target.setItem(key, value);
      return true;
    } catch { return false; }
  };
  const accountOwner = (user) => user && ["number", "string"].includes(typeof user.id)
    && String(user.id).trim() ? `user:${String(user.id)}` : "anonymous";
  const broadcast = (reason) => {
    // No identity, query or bearer PDF credential in the cross-tab signal.
    set("localStorage", RESET_KEY, JSON.stringify({ reason, nonce: `${Date.now()}-${Math.random()}` }));
    removeKeys("localStorage", [RESET_KEY]);
  };
  const clearSensitiveData = ({ broadcast: notifyTabs = false, reason = "reset", remote = false } = {}) => {
    epoch += 1;
    initialized = false;
    owner = null;
    memoryReport = null;
    removeKeys("localStorage", SENSITIVE_KEYS);
    removeKeys("sessionStorage", SENSITIVE_KEYS);
    for (const listener of listeners) {
      try { listener({ reason, remote }); } catch { /* One subscriber must not stop privacy cleanup. */ }
    }
    if (notifyTabs) broadcast(reason);
  };
  const clearLegacyOfflineCache = () => {
    removeKeys("localStorage", LEGACY_CACHE_KEYS);
    removeKeys("sessionStorage", LEGACY_CACHE_KEYS);
  };
  const syncAccount = (user, { broadcast: notifyTabs = false } = {}) => {
    const next = accountOwner(user);
    const previous = initialized ? owner : read("sessionStorage", OWNER_KEY);
    // Persistent reports/tokens from older versions are never imported automatically.
    removeKeys("localStorage", SENSITIVE_KEYS);
    removeKeys("sessionStorage", [...LEGACY_REPORT_KEYS, ...LEGACY_TOKEN_KEYS]);
    clearLegacyOfflineCache();
    if (previous !== next) clearSensitiveData({ broadcast: notifyTabs, reason: "account-change" });
    owner = next;
    initialized = true;
    set("sessionStorage", OWNER_KEY, owner);
    return owner;
  };
  const captureScope = () => ({ owner, epoch });
  const isScopeCurrent = (scope) => initialized && !!scope && scope.owner === owner && scope.epoch === epoch;
  const storeReport = (result, query = "", scope = captureScope()) => {
    if (!isScopeCurrent(scope) || !result || typeof result !== "object" || Array.isArray(result)
      || typeof query !== "string" || query.length > MAX_QUERY_LENGTH) return false;
    let raw;
    try {
      raw = JSON.stringify({ schema_version: 1, owner, result, query });
      if (raw.length > MAX_REPORT_BYTES || new TextEncoder().encode(raw).byteLength > MAX_REPORT_BYTES) return false;
      memoryReport = JSON.parse(raw);
    } catch { return false; }
    removeKeys("sessionStorage", LEGACY_REPORT_KEYS);
    // Blocked/quota-full storage still permits the current in-memory report, not a persistent cache.
    if (!set("sessionStorage", REPORT_KEY, raw)) removeKeys("sessionStorage", [REPORT_KEY]);
    return true;
  };
  const readReport = () => {
    if (!initialized) return null;
    try {
      const raw = memoryReport ? JSON.stringify(memoryReport) : read("sessionStorage", REPORT_KEY);
      if (!raw || raw.length > MAX_REPORT_BYTES || new TextEncoder().encode(raw).byteLength > MAX_REPORT_BYTES) return null;
      const report = JSON.parse(raw);
      if (report.schema_version !== 1 || report.owner !== owner || !report.result
        || typeof report.result !== "object" || Array.isArray(report.result)
        || typeof report.query !== "string" || report.query.length > MAX_QUERY_LENGTH) return null;
      return { result: report.result, query: report.query };
    } catch { return null; }
  };
  const storageChanged = (event) => {
    if (event.key !== RESET_KEY || !event.newValue) return;
    try {
      const signal = JSON.parse(event.newValue);
      if (!["logout", "account-change"].includes(signal.reason)) return;
      clearSensitiveData({ reason: signal.reason, remote: true });
    } catch { /* Ignore malformed cross-tab events. */ }
  };
  const subscribeReset = (listener) => {
    if (!listeners.size) host?.addEventListener?.("storage", storageChanged);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
      if (!listeners.size) host?.removeEventListener?.("storage", storageChanged);
    };
  };
  return { clearSensitiveData, clearLegacyOfflineCache, syncAccount, captureScope, isScopeCurrent, storeReport, readReport, subscribeReset };
}

const privacyStorage = createPrivacyStorage(typeof window === "undefined" ? undefined : window);
export const clearSensitiveBrowserData = privacyStorage.clearSensitiveData;
export const clearLegacyOfflineCache = privacyStorage.clearLegacyOfflineCache;
export const syncAnalysisAccount = privacyStorage.syncAccount;
export const captureAnalysisScope = privacyStorage.captureScope;
export const isAnalysisScopeCurrent = privacyStorage.isScopeCurrent;
export const storeSessionReport = privacyStorage.storeReport;
export const readSessionReport = privacyStorage.readReport;
export const subscribeAnalysisReset = privacyStorage.subscribeReset;
