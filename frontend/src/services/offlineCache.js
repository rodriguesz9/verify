import { clearLegacyOfflineCache } from "./privacyStorage.js";

// Persistent offline saving is intentionally disabled. Legacy exports remain for
// the connection indicator; they never expose/import reports from a previous user.
export function getOfflineCache() {
  clearLegacyOfflineCache();
  return [];
}

export function saveToOfflineCache() {
  clearLegacyOfflineCache();
  return null;
}

export function getOfflineReport() {
  clearLegacyOfflineCache();
  return null;
}

export function clearOfflineCache() {
  clearLegacyOfflineCache();
}

export function getOfflineCount() {
  clearLegacyOfflineCache();
  return 0;
}
