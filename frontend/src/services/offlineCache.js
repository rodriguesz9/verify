const CACHE_KEY = "verify_offline_cache";
const CACHE_MAX = 50;

export function getOfflineCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveToOfflineCache(result) {
  try {
    const cache = getOfflineCache();
    const entry = {
      id: result.id || `offline_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      query_input: result.query_input || result.plain_explanation?.slice(0, 120) || "Consulta offline",
      verdict_label: result.verdict || result.verdict_label || "Suspeito",
      verdict_score: result.score ?? result.verdict_score ?? 0,
      ai_summary: result.summary || result.ai_summary || "",
      plain_explanation: result.plain_explanation || "",
      content_type: result.content_type || "text",
      created_at: result.created_at || new Date().toISOString(),
      cached_offline: true,
    };
    const exists = cache.find((e) => e.query_input === entry.query_input && e.verdict_label === entry.verdict_label);
    if (!exists) {
      cache.unshift(entry);
      if (cache.length > CACHE_MAX) cache.pop();
      localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
    }
    return entry;
  } catch {
    return null;
  }
}

export function getOfflineReport(id) {
  const cache = getOfflineCache();
  return cache.find((e) => e.id === id) || null;
}

export function clearOfflineCache() {
  localStorage.removeItem(CACHE_KEY);
}

export function getOfflineCount() {
  return getOfflineCache().length;
}
