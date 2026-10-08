import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { extractedReviewText, reviewedTextValid, textReviewState, textReviewError, withoutReviewCredential } from "../src/utils/textReview.js";
import { publicReportDetails } from "../src/utils/reportExport.js";
import { api, analyzeUpload, analyzeReviewedText } from "../src/services/api.js";

const original = "Não pague R$ 123,45 em 03/10/2026.";
const report = { content_type: "image", forensics: { ocr: { text: original } }, text_review_status: "ready", text_review_token: "vrev1.test.proof", text_review_expires_at: 2000 };

test("review uses exact OCR/transcription including negation, numbers and ASR errors", () => {
  assert.equal(extractedReviewText(report), original);
  assert.equal(extractedReviewText({ content_type: "audio", transcription: "Faz um pic surgente." }), "Faz um pic surgente.");
  assert.equal(extractedReviewText({ content_type: "video", transcription: "Faço um Pix." }), "Faço um Pix.");
  assert.equal(extractedReviewText({}), "");
});

test("review requires explicit confirmation, usable text and unexpired capability", () => {
  assert.equal(textReviewState(report, 1999000), "ready");
  assert.equal(textReviewState(report, 2000000), "expired");
  for (const value of [{}, { ...report, text_review_token: "vpdf1.other" }, { ...report, text_review_expires_at: Infinity },
    { ...report, forensics: { ocr: { text: "" } } }, { ...report, text_review_token: "vrev1." + "x".repeat(32 * 1024) }]) {
    assert.equal(textReviewState(value, 1), "unavailable");
  }
  assert.equal(reviewedTextValid(original, false), false);
  assert.equal(reviewedTextValid(original, true), true);
  assert.equal(reviewedTextValid(" curto ", true), false);
  assert.equal(reviewedTextValid("x".repeat(5001), true), false);
});

test("review credential never enters stored original or copyable technical details", () => {
  assert.equal(withoutReviewCredential(report).text_review_token, undefined);
  assert.equal(publicReportDetails(report).text_review_token, undefined);
  assert.equal(report.text_review_token, "vrev1.test.proof");
  assert.equal(withoutReviewCredential(report).forensics.ocr.text, original);
});

test("review errors preserve edits and distinguish expiry, account and quota", () => {
  assert.match(textReviewError({ response: { status: 410 } }), /prazo/);
  assert.match(textReviewError({ response: { status: 403 } }), /mesma conta/);
  assert.match(textReviewError({ response: { status: 429 } }), /continua aqui/);
  assert.match(textReviewError(new Error("offline")), /edição foi mantida/);
});

test("upload explicitly defers factual lookup, confirmation sends edited text and provenance only", async () => {
  const previous = api.defaults.adapter;
  const calls = [];
  api.defaults.adapter = async (config) => {
    calls.push(config);
    return { data: report, status: 200, statusText: "OK", headers: {}, config };
  };
  try {
    const file = new Blob(["control"], { type: "image/png" });
    await analyzeUpload(file, { reviewText: true });
    assert.equal(calls[0].url, "/upload");
    assert.equal(calls[0].data.get("review_text"), "true");
    await analyzeReviewedText(original, report.text_review_token);
    assert.equal(calls[1].url, "/check-extracted-text");
    assert.deepEqual(JSON.parse(calls[1].data), { text: original, review_token: report.text_review_token });
    await analyzeUpload(file);
    assert.equal(calls[2].data.get("review_text"), null);
  } finally { api.defaults.adapter = previous; }
});

test("review UI has accessible labels, original media controls, cleanup and resets confirmation on edit", () => {
  const component = readFileSync(new URL("../src/components/report/ExtractedTextReview.jsx", import.meta.url), "utf8");
  assert.match(component, /htmlFor="reviewed-text"/);
  assert.match(component, /aria-describedby="review-help review-count"/);
  assert.match(component, /setConfirmed\(false\)/);
  assert.match(component, /URL\.revokeObjectURL\(url\)/);
  assert.match(component, /<audio controls/);
  assert.match(component, /<video controls/);
  assert.match(component, /A análise original de imagem\/voz não muda/);
  assert.match(component, /mínimo de 10/);
});

test("review state resets on account change and does not persist credentials after navigation", () => {
  const home = readFileSync(new URL("../src/pages/Home.jsx", import.meta.url), "utf8");
  assert.match(home, /setPendingReview\(null\); setReviewBusy\(false\)/);
  assert.match(home, /mounted\.current && isAnalysisScopeCurrent\(scope\)/);
  assert.match(home, /storeSessionReport\(withoutReviewCredential\(report\)/);
  assert.doesNotMatch(home, /localStorage\.setItem/);
});
