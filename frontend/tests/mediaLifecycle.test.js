import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createMediaLifecycle } from "../src/services/mediaLifecycle.js";

function fakeStream() {
  const tracks = [{ calls: 0, stop() { this.calls += 1; } }, { calls: 0, stop() { this.calls += 1; } }];
  return { getTracks: () => tracks, tracks };
}

test("owned streams stop on unmount without relying on a DOM video ref", () => {
  const lifecycle = createMediaLifecycle();
  lifecycle.activate();
  const stream = fakeStream();
  assert.equal(lifecycle.acceptStream(stream, lifecycle.capture()), true);
  const videoRef = { current: null };
  lifecycle.dispose();
  assert.equal(videoRef.current, null);
  assert.deepEqual(stream.tracks.map(track => track.calls), [1, 1]);
  lifecycle.dispose();
  lifecycle.releaseStream(stream);
  assert.deepEqual(stream.tracks.map(track => track.calls), [1, 1]);
});

test("a simulated getUserMedia resolving after unmount stops immediately, without creating a recorder", async () => {
  const lifecycle = createMediaLifecycle();
  lifecycle.activate();
  const scope = lifecycle.capture();
  const stream = fakeStream();
  let resolvePermission;
  const getUserMedia = () => new Promise(resolve => { resolvePermission = resolve; });
  let recorders = 0;
  const request = (async () => {
    const received = await getUserMedia();
    if (!lifecycle.acceptStream(received, scope)) return;
    recorders += 1;
  })();
  lifecycle.dispose();
  resolvePermission(stream);
  await request;
  assert.equal(recorders, 0);
  assert.deepEqual(stream.tracks.map(track => track.calls), [1, 1]);
});

test("manual reset rejects a pending camera even while the component remains mounted", async () => {
  const lifecycle = createMediaLifecycle();
  lifecycle.activate();
  const oldScope = lifecycle.capture();
  lifecycle.invalidate();
  const stream = fakeStream();
  assert.equal(lifecycle.acceptStream(stream, oldScope), false);
  assert.deepEqual(stream.tracks.map(track => track.calls), [1, 1]);
  assert.equal(lifecycle.isCurrent(lifecycle.capture()), true);
  assert.equal(lifecycle.acceptStream(fakeStream(), lifecycle.capture()), true);
  lifecycle.dispose();
});

test("queued MediaRecorder callbacks cannot create an object URL, append chunks or start an upload after teardown", () => {
  const lifecycle = createMediaLifecycle();
  lifecycle.activate();
  const scope = lifecycle.capture();
  const chunks = [];
  let objectUrls = 0;
  let uploads = 0;
  const recorder = {
    ondataavailable: lifecycle.guard(scope, event => chunks.push(event.data)),
    onstop: lifecycle.guard(scope, () => { objectUrls += 1; uploads += 1; }),
  };
  recorder.ondataavailable({ data: "valid-before-teardown" });
  assert.equal(chunks.length, 1);
  const queuedData = recorder.ondataavailable;
  const queuedStop = recorder.onstop;
  lifecycle.dispose();
  recorder.onstop = null;
  recorder.ondataavailable = null;
  queuedData({ data: "late" });
  queuedStop();
  lifecycle.activate();
  queuedStop();
  assert.deepEqual(chunks, ["valid-before-teardown"]);
  assert.equal(objectUrls, 0);
  assert.equal(uploads, 0);
});

test("late result callback from an old lifecycle cannot affect a reactivated instance", async () => {
  const lifecycle = createMediaLifecycle();
  lifecycle.activate();
  const oldScope = lifecycle.capture();
  let result = null;
  const complete = lifecycle.guard(oldScope, data => { result = data; });
  lifecycle.dispose();
  lifecycle.activate();
  await Promise.resolve("private-old-result").then(complete);
  assert.equal(result, null);
  lifecycle.guard(lifecycle.capture(), data => { result = data; })("current-result");
  assert.equal(result, "current-result");
});

test("one failed track stop does not leave the remaining owned tracks running", () => {
  const lifecycle = createMediaLifecycle();
  lifecycle.activate();
  let stopped = false;
  const stream = { getTracks: () => [{ stop() { throw new Error("track failure"); } }, { stop() { stopped = true; } }] };
  lifecycle.acceptStream(stream, lifecycle.capture());
  assert.doesNotThrow(() => lifecycle.dispose());
  assert.equal(stopped, true);
});

test("both demo components accept only current streams and guard deferred work before creating files or calling APIs", () => {
  const audio = readFileSync(new URL("../src/components/demonstracao/AudioDeepfakeDemo.jsx", import.meta.url), "utf8");
  const camera = readFileSync(new URL("../src/components/demonstracao/AuthenticitySealDemo.jsx", import.meta.url), "utf8");
  for (const component of [audio, camera]) {
    assert.match(component, /lifecycle\.activate\(\)/);
    assert.match(component, /lifecycle\.dispose\(\)/);
    assert.match(component, /if \(!lifecycle\.acceptStream\(stream, scope\)\) return/);
  }
  assert.match(audio, /recorder\.ondataavailable = lifecycle\.guard\(scope/);
  assert.match(audio, /recorder\.onstop = lifecycle\.guard\(scope/);
  assert.match(audio, /recorder\.onstop = null/);
  assert.match(audio, /recorder\.ondataavailable = null/);
  assert.match(audio, /URL\.revokeObjectURL\(previewUrl\)/);
  assert.match(audio, /if \(lifecycle\.isCurrent\(scope\)\) setResult\(data\)/);
  assert.match(camera, /canvas\.toBlob\(async \(blob\) => \{\s*if \(!lifecycle\.isCurrent\(scope\)\) return/);
  assert.match(camera, /img\.onload = \(\) => \{\s*if \(!lifecycle\.isCurrent\(scope\)\) return/);
});
