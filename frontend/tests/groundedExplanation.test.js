import test from "node:test";
import assert from "node:assert/strict";
import {groundedReportExplanation} from "../src/utils/reportEvidence.js";

const claim = "Elizabeth II não morreu em 9 de setembro de 2022.";
function report() {
  const source = {url: "https://example.test/body", excerpt: claim, relation: "supports", source_role: "retrieved_reference"};
  return {content_type: "text", verdict: "Authentic", veracity_status: "supported",
    claim_assessments: [{claim, status: "supported", evidence_mode: "retrieved_sources", evidence: [source]}],
    report_explanation: {version: "grounded_text_explanation_v1", decision_role: "explanation_only", new_provider_calls: 0,
      claims: [{claim, status: "supported", references: [{url: source.url, excerpt: claim}]}]},
    plain_explanation: "PRIVATE ERROR: never use arbitrary prose", provider_coverage: {model: {reason: "PRIVATE KEY"}}};
}

test("detailed explanation preserves literal negation and dates, without modifying the decision", () => {
  const original = report(), before = structuredClone(original);
  const result = groundedReportExplanation(original);
  assert.ok(result.text.includes(claim));
  assert.ok(result.text.includes("Trecho citado pela análise"));
  assert.ok(!result.text.includes("PRIVATE"));
  assert.deepEqual(original, before);
});

test("unversioned, media, changed claim or status, oversized and unknown records are ignored", () => {
  for (const change of [r => {r.content_type = "image";}, r => {delete r.report_explanation.version;},
    r => {r.report_explanation.decision_role = "model_opinion";}, r => {r.report_explanation.new_provider_calls = 1;},
    r => {r.report_explanation.claims[0].status = "refuted";}, r => {r.report_explanation.claims[0].claim = "Other claim";},
    r => {r.report_explanation.claims = Array(6).fill(r.report_explanation.claims[0]);}]) {
    const value = report(); change(value); assert.equal(groundedReportExplanation(value), null);
  }
  assert.equal(groundedReportExplanation({}), null);
});

test("invented citations, excluded and submitted sources cannot enter the public explanation", () => {
  for (const mutate of [r => {r.report_explanation.claims[0].references[0].url = "https://invented.test";},
    r => {r.claim_assessments[0].evidence[0].exclusion_reason = "not usable";},
    r => {r.claim_assessments[0].evidence[0].source_role = "submitted_source";},
    r => {r.report_explanation.claims[0].references[0].url = "javascript:alert(1)";},
    r => {r.report_explanation.claims[0].references[0].url = "https://user:secret@example.test";}]) {
    const value = report(); mutate(value);
    const result = groundedReportExplanation(value);
    assert.ok(!result.text.includes("Fonte consultada:"));
  }
});

test("invented or shortened quote is not a literal source passage", () => {
  const value = report();
  value.report_explanation.claims[0].references[0].excerpt = claim.replace("não ", "");
  assert.ok(!groundedReportExplanation(value).text.includes("Trecho citado pela análise"));
  assert.ok(groundedReportExplanation(value).text.includes("Fonte consultada:"));
});
