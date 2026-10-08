// Own browser streams independently of DOM refs, which React clears on unmount.
export function createMediaLifecycle() {
  let active = false;
  let generation = 0;
  const streams = new Set();
  const stopped = new WeakSet();
  const releaseStream = (stream) => {
    if (!stream || typeof stream !== "object" || stopped.has(stream)) return;
    stopped.add(stream);
    streams.delete(stream);
    for (const track of stream.getTracks?.() || []) {
      try { track.stop(); } catch { /* Stop the remaining tracks even if one fails. */ }
    }
  };
  const invalidate = () => {
    generation += 1;
    for (const stream of [...streams]) releaseStream(stream);
  };
  const isCurrent = (scope) => active && scope === generation;
  return {
    activate: () => { invalidate(); active = true; },
    capture: () => generation,
    isCurrent,
    invalidate,
    dispose: () => { active = false; invalidate(); },
    releaseStream,
    acceptStream: (stream, scope) => {
      if (!isCurrent(scope)) { releaseStream(stream); return false; }
      streams.add(stream);
      return true;
    },
    guard: (scope, callback) => (...args) => isCurrent(scope) ? callback(...args) : undefined,
  };
}
