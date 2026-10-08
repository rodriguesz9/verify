import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { scheduleHistoryLoad, averageScoreLabel } from "../src/utils/historyQuery.js";
import { api, getHistory } from "../src/services/api.js";

const query = { page: 1, search: "", contentType: "all", verdict: "all" };
test("average index never turns missing/inconclusive placeholders into zero or 50", () => {
  for (const value of [null, {}, { avg_score: 50 }, { avg_score: null, avg_score_count: 0 },
    { avg_score: 50, avg_score_count: 0 }, { avg_score: 999, avg_score_count: 1 }, { avg_score: NaN, avg_score_count: 1 }]) {
    assert.equal(averageScoreLabel(value), "Não determinado");
  }
  assert.equal(averageScoreLabel({ avg_score: 0, avg_score_count: 1 }), "0/100");
  assert.equal(averageScoreLabel({ avg_score: 70, avg_score_count: 2 }), "70/100");
});
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function harness(overrides = {}) {
  const scheduled = [], canceled = [], events = [];
  const options = {
    query, schedule: (fn, delay) => { scheduled.push({ fn, delay }); return scheduled.length; },
    cancel: (id) => canceled.push(id), loadHistory: async () => ({ items: [], total: 0, limit: 20 }),
    loadStats: async () => ({ total: 0 }), onStart: () => events.push("start"),
    onSuccess: (...result) => events.push(["success", ...result]),
    onError: () => events.push("error"), onFinish: () => events.push("finish"), ...overrides,
  };
  return { scheduled, canceled, events, start: () => scheduleHistoryLoad(options) };
}

test("debounced history cancels replaced keystrokes before any request", async () => {
  let calls = 0;
  const h = harness({ loadHistory: async () => { calls++; return {}; } });
  const cleanup = h.start();
  assert.equal(h.scheduled[0].delay, 300);
  assert.equal(calls, 0);
  cleanup();
  await h.scheduled[0].fn();
  assert.equal(calls, 0);
  assert.deepEqual(h.canceled, [1]);
  assert.deepEqual(h.events, ["start"]);
});

test("history sends server filters and aborts requests on replacement", async () => {
  let received;
  const pending = deferred();
  const h = harness({ query: { page: 3, search: "  literal_%  ", contentType: "Video", verdict: "False" },
    loadHistory: (page, options) => { received = { page, ...options }; return pending.promise; } });
  const cleanup = h.start();
  const running = h.scheduled[0].fn();
  assert.equal(received.page, 3);
  assert.equal(received.search, "literal_%");
  assert.equal(received.contentType, "Video");
  assert.equal(received.verdict, "False");
  assert.equal(received.signal.aborted, false);
  cleanup();
  assert.equal(received.signal.aborted, true);
  pending.resolve({ items: [{ id: "stale" }] });
  await running;
  assert.deepEqual(h.events, ["start"]);
});

test("stale errors cannot replace the next query's successful page", async () => {
  const old = deferred();
  const previous = harness({ loadHistory: () => old.promise });
  const stopOld = previous.start();
  const oldRunning = previous.scheduled[0].fn();
  stopOld();
  const next = harness();
  next.start();
  await next.scheduled[0].fn();
  old.reject(new Error("old failure"));
  await oldRunning;
  assert.deepEqual(previous.events, ["start"]);
  assert.equal(next.events[1][0], "success");
  assert.equal(next.events.at(-1), "finish");
});

test("genuine failures leave loading and show a retryable error", async () => {
  const h = harness({ loadHistory: async () => { throw new Error("offline"); } });
  h.start();
  await h.scheduled[0].fn();
  assert.deepEqual(h.events, ["start", "error", "finish"]);
});

test("unmounted history loads do not run callbacks", async () => {
  const pending = deferred();
  const h = harness({ loadStats: () => pending.promise });
  const cleanup = h.start();
  const running = h.scheduled[0].fn();
  cleanup();
  pending.resolve({ total: 10 });
  await running;
  assert.deepEqual(h.events, ["start"]);
});

test("dashboard shares a 20-row limit, accessible filters and report links", () => {
  const dashboard = readFileSync(new URL("../src/pages/Dashboard.jsx", import.meta.url), "utf8");
  const api = readFileSync(new URL("../src/services/api.js", import.meta.url), "utf8");
  assert.match(dashboard, /const LIMIT = 20/);
  assert.match(api, /getHistory[^\n]+limit: 20/);
  assert.match(api, /getHistory[^\n]+content_type: contentType[^\n]+signal/);
  assert.match(dashboard, /value: "Video"/);
  assert.match(dashboard, /maxLength=\{200\}/);
  assert.match(dashboard, /setSearchQuery\(e.target.value\); setPage\(1\)/);
  assert.match(dashboard, /<Link to=\{`\/report\/\$\{item.id\}`\}/);
  assert.doesNotMatch(dashboard, /onClick=\{\(\) => navigate\(`\/report/);
  assert.doesNotMatch(dashboard, /items\.filter/);
  assert.match(dashboard, /role="alert"/);
  assert.match(dashboard, /Tentar novamente/);
});

test("history client passes literal filters and the abort signal without a network call", async () => {
  const originalAdapter = api.defaults.adapter;
  const controller = new AbortController();
  let captured;
  api.defaults.adapter = async (config) => {
    captured = config;
    return { status: 200, statusText: "OK", headers: {}, config, data: { total: 45, limit: 20, items: [] } };
  };
  try {
    const result = await getHistory(3, { search: "literal_%", contentType: "Video", verdict: "False", signal: controller.signal });
    assert.equal(result.total, 45);
    assert.equal(captured.url, "/history");
    assert.deepEqual(captured.params, { page: 3, limit: 20, search: "literal_%", content_type: "Video", verdict: "False" });
    assert.equal(captured.signal, controller.signal);
  } finally {
    api.defaults.adapter = originalAdapter;
  }
});
