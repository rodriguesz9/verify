import test from "node:test";
import assert from "node:assert/strict";
import { pdfExportState, publicReportDetails, pdfExportError } from "../src/utils/reportExport.js";
import { api, downloadPdfReport } from "../src/services/api.js";
import { readFileSync } from "node:fs";

const result = { pdf_snapshot_token: "vpdf1.signed.snapshot", pdf_snapshot_expires_at: 2000, verdict: "Suspicious", score: null };

test("text and link reports use the same signature guard, not a media-only gate", () => {
  for (const content_type of ["text", "url"]) {
    assert.equal(pdfExportState({ ...result, content_type }, 1999000), "ready");
    assert.equal(pdfExportState({ content_type, verdict: "Authentic" }), "unavailable");
  }
});

test("export feedback is accessible and does not claim the browser saved a file", () => {
  const source = readFileSync(new URL("../src/pages/ReportPage.jsx", import.meta.url), "utf8");
  assert.match(source, /pdfNotice && <p role="status"/);
  assert.match(source, /PDF preparado\. Se o arquivo não aparecer/);
  assert.equal((source.match(/setPdfNotice\(""\)/g) || []).length, 3);
  assert.doesNotMatch(source, /disponível para novas análises de mídia/);
});

test("PDF requires an unexpired snapshot and never treats arbitrary reports as exportable", () => {
  assert.equal(pdfExportState(result, 1999000), "ready");
  assert.equal(pdfExportState(result, 2000000), "expired");
  for (const entry of [null, {}, { ...result, pdf_snapshot_token: "jwt.invalid" },
    { ...result, pdf_snapshot_expires_at: "2000" },
    { ...result, pdf_snapshot_expires_at: Infinity },
    { ...result, pdf_snapshot_token: "vpdf1." + "x".repeat(512 * 1024) }]) {
    assert.equal(pdfExportState(entry), "unavailable");
  }
});

test("copyable technical details omit the export credential without changing evidence", () => {
  const details = publicReportDetails(result);
  assert.equal(details.pdf_snapshot_token, undefined);
  assert.equal(details.verdict, result.verdict);
  assert.equal(details.score, null);
  assert.equal(result.pdf_snapshot_token, "vpdf1.signed.snapshot");
});

test("PDF errors explain recovery without promising a new analysis", async () => {
  assert.match(await pdfExportError({ response: { status: 410 } }), /histórico/);
  assert.match(await pdfExportError({ response: { status: 403 } }), /mesma conta/);
  assert.match(await pdfExportError({ response: { status: 429 } }), /não será refeita/);
  assert.match(await pdfExportError(new Error("offline")), /não refaz/);
});

test("PDF request sends only the issued snapshot, never a media file or unsigned result", async () => {
  const previous = api.defaults.adapter;
  let calls = 0;
  const pdf = new Blob(["%PDF-1.4 test"], { type: "application/pdf" });
  api.defaults.adapter = async (config) => {
    calls += 1;
    assert.equal(config.url, "/verificar/relatorio-pdf");
    assert.equal(config.method, "post");
    assert.deepEqual(JSON.parse(config.data), { snapshot_token: result.pdf_snapshot_token });
    assert.equal(config.responseType, "blob");
    return { data: pdf, status: 200, statusText: "OK", headers: {}, config };
  };
  try {
    assert.equal(await downloadPdfReport(result.pdf_snapshot_token), pdf);
    await assert.rejects(downloadPdfReport(new Blob(["image"])), /não tem/);
    await assert.rejects(downloadPdfReport({ verdict: "Authentic" }), /não tem/);
    assert.equal(calls, 1);
  } finally {
    api.defaults.adapter = previous;
  }
});
