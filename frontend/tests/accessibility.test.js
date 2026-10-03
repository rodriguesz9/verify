import test from "node:test";
import assert from "node:assert/strict";
import { createAccessibilityStore, normalizeAccessibilityMode, nextTextSize } from "../src/services/accessibility.js";

function fakeHost(initial = {}) {
  const values = new Map(Object.entries(initial));
  const attrs = new Map();
  const events = new Map();
  return {
    values, attrs, events,
    localStorage: { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) },
    document: { documentElement: { setAttribute: (key, value) => attrs.set(key, value), removeAttribute: (key) => attrs.delete(key) } },
    addEventListener: (key, listener) => events.set(key, listener),
    removeEventListener: (key, listener) => { if (events.get(key) === listener) events.delete(key); },
  };
}

test("migrates conflicting legacy preferences without keeping Easy Mode accidentally active", () => {
  assert.equal(normalizeAccessibilityMode("elderly", "false"), "normal");
  assert.equal(normalizeAccessibilityMode("large", "true"), "elderly");
  assert.equal(normalizeAccessibilityMode("invalid", null), "normal");
  assert.equal(normalizeAccessibilityMode("xlarge", null), "xlarge");
});
test("initializes the document before rendering and honors the versioned preference", () => {
  const host = fakeHost({ verify_accessibility_v1: "elderly", verify_elderly_mode: "false" });
  const store = createAccessibilityStore(host);
  store.initialize();
  assert.equal(host.attrs.get("data-font-size"), "elderly");
  assert.equal(host.attrs.get("data-elderly-mode"), "true");
  assert.equal(store.getSnapshot(), "elderly");
});
test("turning Easy Mode off clears both attributes and persists across reloads", () => {
  const host = fakeHost();
  const store = createAccessibilityStore(host);
  store.setMode("elderly");
  store.setMode("normal");
  assert.equal(host.attrs.size, 0);
  assert.equal(host.values.get("verify_elderly_mode"), "false");
  assert.equal(createAccessibilityStore(host).getSnapshot(), "normal");
});
test("all subscribers see changes with only one cross-tab listener", () => {
  const host = fakeHost();
  const store = createAccessibilityStore(host);
  let count = 0;
  const unsubscribeA = store.subscribe(() => count++);
  const unsubscribeB = store.subscribe(() => count++);
  assert.equal(host.events.size, 1);
  store.setMode("large");
  assert.equal(count, 2);
  host.values.set("verify_accessibility_v1", "elderly");
  host.events.get("storage")({ key: "verify_accessibility_v1" });
  assert.equal(count, 4);
  assert.equal(store.getSnapshot(), "elderly");
  unsubscribeA();
  assert.equal(host.events.size, 1);
  unsubscribeB();
  assert.equal(host.events.size, 0);
});
test("works when storage is blocked and ignores unsupported sizes", () => {
  const host = fakeHost();
  host.localStorage = { getItem() { throw Error("blocked"); }, setItem() { throw Error("blocked"); } };
  const store = createAccessibilityStore(host);
  assert.equal(store.getSnapshot(), "normal");
  store.setMode("elderly");
  store.setMode("invalid");
  assert.equal(store.getSnapshot(), "elderly");
  assert.equal(host.attrs.get("data-elderly-mode"), "true");
});
test("larger text cycles predictably, without multiplying font sizes", () => {
  assert.equal(nextTextSize("normal"), "large");
  assert.equal(nextTextSize("large"), "xlarge");
  assert.equal(nextTextSize("xlarge"), "normal");
});
