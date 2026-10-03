import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

test("Portuguese demo files contain real audio bytes and are labelled synthetic", () => {
  const component = readFileSync(new URL("../src/components/demonstracao/AudioDeepfakeDemo.jsx", import.meta.url), "utf8");
  for (const name of ["demo-pedido-sintetico.wav", "demo-conversa-sintetica.wav"]) {
    const bytes = readFileSync(new URL(`../public/audio/${name}`, import.meta.url));
    assert.equal(bytes.toString("ascii", 0, 4), "RIFF");
    assert.equal(bytes.toString("ascii", 8, 12), "WAVE");
    assert.ok(bytes.length > 100000);
    assert.ok(component.includes(name));
  }
  assert.match(component, /As duas vozes são sintéticas/);
  assert.doesNotMatch(component, /Ouvir gravação real|origem não auditada/);
});
