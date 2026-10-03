import test from "node:test";
import assert from "node:assert/strict";
import {animatedScoreAt, normalizeScore, safeSourceUrl, buildReportEvidence} from "../src/utils/reportEvidence.js";

test("refuted claims show attributed evidence, dates and exclusions", () => {
  const result = buildReportEvidence({verdict: "False", veracity_status: "refuted", analysis_status: "partial",
    claim_assessments: [{claim: "Afirmação sintética de teste", status: "refuted", explanation: "Duas fontes refutam.", evidence: [{}, {}], excluded_evidence: []}],
    fact_checks: [{claim_text: "Afirmação sintética de teste", rating: "Falso", publisher: "Teste", review_date: "2026-09-01", url: "https://example.com/fixture"}]});
  assert.equal(result.veracityStatus, "refuted");
  assert.equal(result.findings[0].title, "Refutada nas checagens");
  assert.equal(result.sources[0].date, "2026-09-01");
  assert.match(result.interpretation, /refutam/);
});
test("OCR truth stays separate from unknown media origin", () => {
  const result = buildReportEvidence({content_type: "image", verdict: "Suspicious", analysis_status: "inconclusive",
    authenticity_status: "undetermined", veracity_status: "unverified",
    content_analysis: {origin: "ocr", veracity_status: "supported", summary: "Corroborada nas checagens", claim_assessments: [],
      fact_checks: [{claim_text: "Texto", rating: "Verdadeiro", url: "https://example.com/fixture"}]}});
  assert.equal(result.inconclusive, true);
  assert.equal(result.veracityStatus, "supported");
  assert.equal(result.contentOrigin, "ocr");
  assert.equal(result.sources.length, 1);
});

test("indicator clamps bounds, preserves zero and never invents missing scores", () => {
  assert.equal(normalizeScore(0), 0);
  assert.equal(normalizeScore(90), 90);
  assert.equal(normalizeScore(110), 100);
  assert.equal(normalizeScore(-1), 0);
  for (const value of [undefined, null, NaN, Infinity, "90"]) assert.equal(normalizeScore(value), null);
});
test("animation grows monotonically to exactly 90 without overshooting", () => {
  let previous = 0;
  for (let step = 0; step <= 100; step++) {
    const current = animatedScoreAt(90, step / 100);
    assert.ok(current >= previous && current <= 90);
    previous = current;
  }
  assert.equal(animatedScoreAt(90, 0), 0);
  assert.equal(animatedScoreAt(90, 1), 90);
  assert.equal(animatedScoreAt(90, 2), 90);
});
test("sources reject executable schemes and credentials", () => {
  for (const value of ["javascript:alert(1)", "data:text/html,unsafe", "https://user:secret@example.com", "", null]) {
    assert.equal(safeSourceUrl(value), null);
  }
  assert.equal(safeSourceUrl("https://example.com/article"), "https://example.com/article");
});
test("report does not turn inconclusive coverage into falsehood", () => {
  const report = buildReportEvidence({
    content_type: "image", verdict: "Suspicious", analysis_status: "inconclusive",
    provider_coverage: {hive: {status: "error", ai_score: null}},
  }, "fake-clonado.png");
  assert.equal(report.checkedContent, "");
  assert.equal(report.findings.length, 0);
  assert.match(report.interpretation, /não é prova de conteúdo falso/);
  assert.equal(report.missing.length, 1);
});
test("actual pattern excerpt is preserved and duplicate generic flags are removed", () => {
  const report = buildReportEvidence({
    verdict: "Scam",
    scam_analysis: {detected_patterns: [{category: "Pedido de taxa", description: "Risco de pagamento antecipado.", matched_excerpt: "Pague uma taxa"}]},
    red_flags: ["Alerta: Pedido de taxa - Risco de pagamento antecipado."],
  }, "Pague uma taxa agora.");
  assert.equal(report.findings.length, 1);
  assert.equal(report.findings[0].quote, "Pague uma taxa");
  assert.match(report.interpretation, /não comprovam/);
});
test("references invented by an LLM are not presented as retrieved evidence", () => {
  const report = buildReportEvidence({
    fact_check_evidence: [{publisher: "Inventado", url: "https://example.com"}],
    fact_checks: [{publisher: "Fonte consultada", claim_text: "Afirmação A", rating: "Falso", url: "https://example.com/a"}],
    serper_news: [{title: "Notícia relacionada", source: "Jornal", link: "https://example.com/b"}],
  });
  assert.equal(report.sources.length, 2);
  assert.equal(report.sources[0].rating, "Falso");
  assert.ok(report.sources.every((source) => source.publisher !== "Inventado"));
});
test("video explains exact sampled timestamps and does not infer full coverage", () => {
  const report = buildReportEvidence({
    content_type: "video", forensics: {video: {sampled_frames: 3, timestamps_seconds: [0, 1.5, 2.7]}},
  });
  assert.equal(report.sampledFrames, 3);
  assert.deepEqual(report.timestamps, [0, 1.5, 2.7]);
});
test("audio separates speech-risk indicators from voice authenticity", () => {
  const report = buildReportEvidence({
    content_type: "audio", transcription: "Mensagem fictícia", content_risk: {indicators: ["Pedido financeiro"]},
  });
  assert.match(report.findings[0].origin, /não detecta clonagem/);
  assert.equal(report.transcription, "Mensagem fictícia");
});
test("video shows separate audio coverage and actual temporal observations", () => {
  const report = buildReportEvidence({content_type: "video", provider_coverage: {hive: {status: "success", ai_score: null}},
    audio_analysis: {provider_coverage: {hive: {status: "partial", ai_score: .98}},
      forensics: {hive: {segments: [{start_seconds: 0, end_seconds: 10, ai_generated_score: .98},
        {start_seconds: 10, end_seconds: 20, ai_generated_score: .02}, null, {start_seconds: -1, end_seconds: 20, ai_generated_score: 2}]}}},
    content_analysis: {claims: ["Conteúdo de teste"]}});
  assert.deepEqual(report.claims, ["Conteúdo de teste"]);
  assert.equal(report.findings.filter((finding) => finding.id.startsWith("audio-segment")).length, 2);
  assert.ok(report.missing.some((item) => item.includes("áudio/hive")));
  assert.ok(report.findings.some((item) => item.title.includes("áudio/hive")));
});
test("malformed legacy lists are safely ignored", () => {
  const report = buildReportEvidence({
    red_flags: {}, claims: null, fact_checks: [null, 42], serper_news: "invalid",
    provider_coverage: {hive: null}, limitations: ["Limite", null],
    scam_analysis: {detected_patterns: [null, "invalid"]},
  });
  assert.equal(report.findings.length, 0);
  assert.equal(report.sources.length, 0);
  assert.deepEqual(report.limitations, ["Limite"]);
});
test("preconfigured safety guidance stays separate from retrieved fact checks", () => {
  const report = buildReportEvidence({
    scam_analysis: {detected_patterns: [{guidance: [{title: "Orientação oficial", url: "https://www.bcb.gov.br/meubc"}]}]},
  });
  assert.equal(report.sources.length, 0);
  assert.equal(report.guidance.length, 1);
});

test("free AI helper is transparent but never displayed as a truth detector", () => {
  const report = buildReportEvidence({provider_coverage: {openrouter: {status: "success", decision_role: "search_hints_only",
    model_used: "vendor/model:free", ai_score: 1}}});
  assert.equal(report.findings.length, 1);
  assert.match(report.findings[0].detail, /Não decidiu o veredito/);
  assert.match(report.findings[0].detail, /vendor\/model:free/);
  assert.doesNotMatch(report.findings[0].title, /Sinal de geração/);
});

test("media content search failure remains visible and distinct from authenticity", () => {
  const report = buildReportEvidence({content_type: "image", content_analysis: {provider_coverage: {
    openrouter: {status: "rate_limited", decision_role: "search_hints_only"},
    serper: {status: "no_results", decision_role: "context_only"}}}});
  assert.equal(report.missing.length, 2);
  assert.ok(report.missing.every((item) => item.includes("não determina verdade ou falsidade")));
});

test("OCR and transcription are reading aids, not authenticity scores", () => {
  const report = buildReportEvidence({provider_coverage: {
    ocr: {status: "success", decision_role: "ocr_only", provider: "openrouter", ai_score: 1},
    speech: {status: "timeout", decision_role: "transcription_only", reason: "Prazo atingido", ai_score: 1}}});
  assert.equal(report.findings.length, 1);
  assert.match(report.findings[0].detail, /Não certifica/);
  assert.doesNotMatch(report.findings[0].title, /Sinal de geração/);
  assert.match(report.missing[0], /Prazo atingido/);
});
