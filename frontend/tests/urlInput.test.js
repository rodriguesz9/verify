import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { analysisUrlInput, MAX_ANALYSIS_URL_LENGTH } from "../src/utils/urlInput.js";

const boundary = "https://example.test/" + "x".repeat(512 - "https://example.test/".length);

test("complete URL is accepted at 512 and refused at 513 without silently slicing", () => {
  const valid = analysisUrlInput(boundary);
  assert.equal(MAX_ANALYSIS_URL_LENGTH, 512);
  assert.equal(valid.valid, true);
  assert.equal(valid.normalized, boundary);
  assert.equal(valid.length, 512);
  const rejected = analysisUrlInput(boundary + "FINAL");
  assert.equal(rejected.valid, false);
  assert.equal(rejected.normalized, boundary + "FINAL");
  assert.match(rejected.error, /512/);
  assert.match(rejected.error, /mantido inteiro/);
});

test("automatic https protocol participates in length, surrounding spaces do not", () => {
  const bare = boundary.slice("https://".length);
  assert.equal(analysisUrlInput(bare).normalized, boundary);
  assert.equal(analysisUrlInput(bare).length, 512);
  assert.equal(analysisUrlInput(bare + "x").valid, false);
  assert.equal(analysisUrlInput("  " + boundary + "\n").normalized, boundary);
  const uppercase = boundary.replace("https://", "HTTPS://");
  assert.equal(analysisUrlInput(uppercase).normalized, uppercase);
  assert.equal(analysisUrlInput(uppercase).valid, true);
});

test("minimum length and Unicode code-point counts match backend string validation", () => {
  for (const value of ["", "   ", "abcd", undefined, null, 123]) {
    assert.equal(analysisUrlInput(value).valid, false);
  }
  const unicode = "https://example.test/" + "🧪".repeat(512 - "https://example.test/".length);
  assert.equal(analysisUrlInput(unicode).length, 512);
  assert.equal(analysisUrlInput(unicode).valid, true);
  assert.equal(analysisUrlInput(unicode + "x").valid, false);
  // Remote canonical percent-encoding and redirect length are rechecked by API.
});

test("URL UI shows accessible label, total length and explicit refusal without maxLength truncation", () => {
  const home = readFileSync(new URL("../src/pages/Home.jsx", import.meta.url), "utf8");
  assert.match(home, /if \(tab === 1\) return urlInput\.valid/);
  assert.match(home, /htmlFor="analysis-url"/);
  assert.match(home, /id="analysis-url-count"/);
  assert.match(home, /id="analysis-url-help"/);
  assert.match(home, /id="analysis-url-error"/);
  const input = home.match(/<input\s+id="analysis-url"[\s\S]*?\/>/)[0];
  assert.match(input, /aria-invalid=\{Boolean\(urlInput\.error\)\}/);
  assert.match(input, /aria-describedby=/);
  assert.doesNotMatch(input, /maxLength|\.slice\(|\.substring\(/);
});
