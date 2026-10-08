import test from "node:test";
import assert from "node:assert/strict";
import axios from "axios";
import { api, analyzeUpload, getMe, login, register, googleAuth, logout } from "../src/services/api.js";
import { captureAnalysisScope, clearSensitiveBrowserData, syncAnalysisAccount,
  subscribeAnalysisReset } from "../src/services/privacyStorage.js";

const success = (config, data = {}) => ({ data, status: 200, statusText: "OK", headers: {}, config });
const failure = (config, status = 401) => new axios.AxiosError("Fixed local adapter control",
  "ERR_BAD_RESPONSE", config, undefined,
  { config, data: { detail: "Fixed local adapter control" }, status, statusText: "CONTROL", headers: {} });
const deferred = () => {
  let resolve;
  const promise = new Promise((settle) => { resolve = settle; });
  return { promise, resolve };
};

// These adapters never send cookies, HTTP requests, files or provider calls.
async function controlled(adapter, run, { startup = false, anonymous = false } = {}) {
  const previousAdapter = api.defaults.adapter;
  const previousWindow = globalThis.window;
  clearSensitiveBrowserData();
  if (!startup) syncAnalysisAccount(anonymous ? null : { id: "A" });
  globalThis.window = { location: { href: "/control" } };
  api.defaults.adapter = adapter;
  try { await run(); }
  finally {
    api.defaults.adapter = previousAdapter;
    clearSensitiveBrowserData();
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  }
}

test("startup getMe can refresh and retry before account initialization", async () => {
  const calls = [];
  await controlled(async (config) => {
    calls.push(config.url);
    if (config.url === "/auth/me" && !config._retry) throw failure(config);
    return success(config, config.url === "/auth/me" ? { id: "A" } : {});
  }, async () => {
    assert.equal(captureAnalysisScope().owner, null);
    assert.deepEqual(await getMe(), { id: "A" });
    assert.deepEqual(calls, ["/auth/me", "/auth/refresh", "/auth/me"]);
    assert.equal(globalThis.window.location.href, "/control");
  }, { startup: true });
});

test("POST upload refreshes but never automatically replays its FormData", async () => {
  const calls = [];
  await controlled(async (config) => {
    calls.push({ url: config.url, body: config.data });
    if (config.url === "/upload") throw failure(config);
    return success(config);
  }, async () => {
    await assert.rejects(analyzeUpload(new Blob(["fixed local control"], { type: "audio/wav" })), (error) => {
      assert.equal(error.code, "ERR_REQUEST_REQUIRES_RESUBMISSION");
      assert.equal(error.response.status, 401);
      assert.match(error.response.data.detail, /não foi reenviado automaticamente/);
      return true;
    });
    assert.deepEqual(calls.map(({ url }) => url), ["/upload", "/auth/refresh"]);
    assert.ok(calls[0].body instanceof FormData);
    assert.equal(captureAnalysisScope().owner, "user:A");
  });
});

test("other write methods also require deliberate resubmission after refresh", async () => {
  const calls = [];
  await controlled(async (config) => {
    calls.push([config.method, config.url]);
    if (config.url === "/auth/refresh") return success(config);
    throw failure(config);
  }, async () => {
    for (const method of ["post", "put", "patch", "delete"]) {
      await assert.rejects(api.request({ method, url: "/control-write", data: { control: true } }),
        { code: "ERR_REQUEST_REQUIRES_RESUBMISSION" });
    }
    assert.equal(calls.filter(([, url]) => url === "/control-write").length, 4);
    assert.equal(calls.filter(([, url]) => url === "/auth/refresh").length, 4);
    assert.equal(calls.some(([, url]) => url === "/auth/logout"), false);
  });
});

test("read-only GET retries once when owner and epoch stay unchanged", async () => {
  const calls = [];
  await controlled(async (config) => {
    calls.push(config.url);
    if (config.url === "/history" && !config._retry) throw failure(config);
    return success(config, { control: true });
  }, async () => {
    const before = captureAnalysisScope();
    assert.deepEqual((await api.get("/history")).data, { control: true });
    assert.deepEqual(calls, ["/history", "/auth/refresh", "/history"]);
    assert.deepEqual(captureAnalysisScope(), before);
  });
});

for (const sequence of [["B"], ["B", "A"]]) {
  test(`account change during refresh prevents GET replay (${sequence.join(" → ")})`, async () => {
    const refreshStarted = deferred();
    const releaseRefresh = deferred();
    const calls = [];
    await controlled(async (config) => {
      calls.push(config.url);
      if (config.url === "/auth/refresh") {
        refreshStarted.resolve();
        await releaseRefresh.promise;
        return success(config);
      }
      throw failure(config);
    }, async () => {
      const rejected = assert.rejects(api.get("/history"), (error) => error.response?.status === 401);
      await refreshStarted.promise;
      for (const id of sequence) syncAnalysisAccount({ id });
      releaseRefresh.resolve();
      await rejected;
      assert.deepEqual(calls, ["/history", "/auth/refresh"]);
      assert.equal(captureAnalysisScope().owner, `user:${sequence.at(-1)}`);
      assert.equal(globalThis.window.location.href, "/control");
    });
  });
}

test("account change during upload refresh cannot send the old body under account B", async () => {
  const refreshStarted = deferred();
  const releaseRefresh = deferred();
  const calls = [];
  await controlled(async (config) => {
    calls.push(config.url);
    if (config.url === "/auth/refresh") {
      refreshStarted.resolve();
      await releaseRefresh.promise;
      return success(config);
    }
    throw failure(config);
  }, async () => {
    const rejected = assert.rejects(analyzeUpload(new Blob(["account A local control"])),
      (error) => error.response?.status === 401);
    await refreshStarted.promise;
    syncAnalysisAccount({ id: "B" });
    releaseRefresh.resolve();
    await rejected;
    assert.deepEqual(calls, ["/upload", "/auth/refresh"]);
    assert.equal(captureAnalysisScope().owner, "user:B");
  });
});

test("old 401 arriving after an account change cannot start refresh or logout", async () => {
  const requestStarted = deferred();
  const releaseResponse = deferred();
  const calls = [];
  await controlled(async (config) => {
    calls.push(config.url);
    requestStarted.resolve();
    await releaseResponse.promise;
    throw failure(config);
  }, async () => {
    const rejected = assert.rejects(api.get("/history"), (error) => error.response?.status === 401);
    await requestStarted.promise;
    syncAnalysisAccount({ id: "B" });
    releaseResponse.resolve();
    await rejected;
    assert.deepEqual(calls, ["/history"]);
    assert.equal(captureAnalysisScope().owner, "user:B");
  });
});

test("scope is captured synchronously before an immediate account change", async () => {
  const releaseResponse = deferred();
  const captured = [];
  await controlled(async (config) => {
    captured.push({ url: config.url, ...config._privacyScope });
    await releaseResponse.promise;
    throw failure(config);
  }, async () => {
    const scopeA = captureAnalysisScope();
    const rejected = assert.rejects(api.post("/check-text", { text: "Account A local control" }),
      (error) => error.response?.status === 401);
    syncAnalysisAccount({ id: "B" });
    assert.deepEqual(captured, [{ url: "/check-text", ...scopeA }],
      "the first adapter dispatch already belongs to A, not a later microtask under B");
    releaseResponse.resolve();
    await rejected;
    assert.equal(captured.length, 1, "an already dispatched request cannot be undone, but never replayed");
    assert.equal(captureAnalysisScope().owner, "user:B");
  });
});

test("failed refresh from account A cannot log out or redirect newer account B", async () => {
  const refreshStarted = deferred();
  const releaseRefresh = deferred();
  const calls = [];
  await controlled(async (config) => {
    calls.push(config.url);
    if (config.url === "/auth/refresh") {
      refreshStarted.resolve();
      await releaseRefresh.promise;
      throw failure(config, 500);
    }
    throw failure(config);
  }, async () => {
    const rejected = assert.rejects(api.get("/history"), (error) => error.response?.status === 401);
    await refreshStarted.promise;
    syncAnalysisAccount({ id: "B" });
    releaseRefresh.resolve();
    await rejected;
    assert.deepEqual(calls, ["/history", "/auth/refresh"]);
    assert.equal(captureAnalysisScope().owner, "user:B");
    assert.equal(globalThis.window.location.href, "/control");
  });
});

test("a stale captured request is rejected before reaching the adapter", async () => {
  let calls = 0;
  await controlled(async (config) => { calls += 1; return success(config); }, async () => {
    const previous = captureAnalysisScope();
    syncAnalysisAccount({ id: "B" });
    await assert.rejects(api.get("/history", { _privacyScope: previous }), (error) => axios.isCancel(error));
    assert.equal(calls, 0);
  });
});

for (const [name, authenticate, endpoint] of [
  ["login", login, "/auth/login"], ["register", register, "/auth/register"], ["google", googleAuth, "/auth/google"],
]) {
  test(`${name} invalidates and announces old private scope before changing cookies`, async () => {
    const resets = [];
    let previous;
    await controlled(async (config) => {
      assert.equal(config.url, endpoint);
      assert.deepEqual(resets, ["account-change"]);
      assert.notDeepEqual(captureAnalysisScope(), previous);
      assert.equal(captureAnalysisScope().owner, null);
      return success(config);
    }, async () => {
      previous = captureAnalysisScope();
      const unsubscribe = subscribeAnalysisReset(({ reason }) => resets.push(reason));
      try { await authenticate({ control: true }); }
      finally { unsubscribe(); }
    });
  });
}

test("anonymous to login during refresh cannot replay earlier private work", async () => {
  const refreshStarted = deferred();
  const releaseRefresh = deferred();
  const calls = [];
  await controlled(async (config) => {
    calls.push(config.url);
    if (config.url === "/auth/refresh") {
      refreshStarted.resolve();
      await releaseRefresh.promise;
      return success(config);
    }
    if (config.url === "/auth/login") return success(config);
    throw failure(config);
  }, async () => {
    const rejected = assert.rejects(api.get("/history"), (error) => error.response?.status === 401);
    await refreshStarted.promise;
    await login({ control: true });
    syncAnalysisAccount({ id: "B" });
    releaseRefresh.resolve();
    await rejected;
    assert.deepEqual(calls, ["/history", "/auth/refresh", "/auth/login"]);
    assert.equal(captureAnalysisScope().owner, "user:B");
  }, { anonymous: true });
});

test("getMe failed refresh at startup neither logs out nor redirects", async () => {
  const calls = [];
  await controlled(async (config) => { calls.push(config.url); throw failure(config); }, async () => {
    const before = captureAnalysisScope();
    await assert.rejects(getMe(), (error) => error.response?.status === 401);
    assert.deepEqual(calls, ["/auth/me", "/auth/refresh"]);
    assert.deepEqual(captureAnalysisScope(), before);
    assert.equal(globalThis.window.location.href, "/control");
  }, { startup: true });
});

test("late explicit logout completion cannot redirect newer account B", async () => {
  const requestStarted = deferred();
  const releaseResponse = deferred();
  await controlled(async (config) => {
    assert.equal(config.url, "/auth/logout");
    requestStarted.resolve();
    await releaseResponse.promise;
    return success(config);
  }, async () => {
    const pending = logout();
    await requestStarted.promise;
    syncAnalysisAccount({ id: "B" });
    releaseResponse.resolve();
    await pending;
    assert.equal(globalThis.window.location.href, "/control");
    assert.equal(captureAnalysisScope().owner, "user:B");
  });
});

test("second GET 401 is not refreshed recursively or replayed a third time", async () => {
  const calls = [];
  await controlled(async (config) => {
    calls.push(config.url);
    if (config.url === "/auth/refresh") return success(config);
    throw failure(config);
  }, async () => {
    await assert.rejects(api.get("/history"), (error) => error.response?.status === 401);
    assert.deepEqual(calls, ["/history", "/auth/refresh", "/history"]);
  });
});
