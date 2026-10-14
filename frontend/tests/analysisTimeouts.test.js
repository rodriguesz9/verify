import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { api, analyzeText, analyzeTextBatch, analyzeUrl, analyzeReviewedText, analyzeUpload,
  verifyAudioQuick, verifyComplete, simulateWhatsApp, login, downloadPdfReport } from "../src/services/api.js";

test("analysis deadlines cover bounded server stages; auth and PDF remain short", async () => {
  const previous = api.defaults.adapter;
  const observed = [];
  api.defaults.adapter = async (config) => {
    observed.push([config.url, config.timeout]);
    return { data: {}, status: 200, statusText: "OK", headers: {}, config };
  };
  try {
    const file = new Blob(["control"], { type: "image/png" });
    await analyzeText("fixed control");
    await analyzeTextBatch(["fixed control"]);
    await analyzeUrl("https://example.test");
    await analyzeReviewedText("fixed control", "control-token");
    await analyzeUpload(file);
    await verifyAudioQuick(file);
    await verifyComplete(file);
    await simulateWhatsApp("fixed control");
    await login({ email: "test@example.test", password: "test-only" });
    await downloadPdfReport("vpdf1.control");
    assert.deepEqual(observed, [
      ["/check-text", 240000], ["/check-text-batch", 240000], ["/check-url", 240000], ["/check-extracted-text", 240000],
      ["/upload", 180000], ["/verificar/audio-rapido", 180000], ["/verificar/completo", 180000],
      ["/whatsapp/simulate", 240000], ["/auth/login", 60000], ["/verificar/relatorio-pdf", 30000],
    ]);
  } finally {
    api.defaults.adapter = previous;
  }
});

test("waiting feedback is accessible and does not fabricate percentage progress", () => {
  const source = readFileSync(new URL("../src/pages/Home.jsx", import.meta.url), "utf8");
  assert.match(source, /role="status" aria-live="polite"/);
  assert.match(source, /Aguarde sem enviar novamente/);
  assert.match(source, /checagens de texto e link podem levar até quatro minutos/);
});
