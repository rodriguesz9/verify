import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {animatedScoreAt, normalizeScore, safeSourceUrl, buildReportEvidence, visibleDetectorScore, reportMediaHeadline} from "../src/utils/reportEvidence.js";

test("extraction notices require actual text, not merely the type of media", () => {
  assert.equal(buildReportEvidence({content_type: "image", veracity_status: "unverified", forensics: {}}).extractionMethod, null);
  assert.equal(buildReportEvidence({content_type: "audio", transcription: "   "}).extractionMethod, null);
  assert.equal(buildReportEvidence({content_type: "image", content_analysis: {origin: "ocr"}}).extractionMethod, null);
  assert.equal(buildReportEvidence({content_type: "image", forensics: {ocr: {text: "Texto visível"}}}).extractionMethod, "OCR");
  assert.equal(buildReportEvidence({content_type: "audio", transcription: "Mensagem de controle"}).extractionMethod, "transcrição");
  assert.equal(buildReportEvidence({content_type: "video", audio_analysis: {transcription: "Trecho falado"}}).extractionMethod, "transcrição");
});

test("full literal OCR and video transcript remain available for human review", () => {
  const text = "Nao pague taxa.\nValor: R$ 123,45\nData: 03/10/2026";
  const ocr = buildReportEvidence({content_type: "image", forensics: {ocr: {text}},
    provider_coverage: {ocr: {status: "success", provider: "tesseract", decision_role: "ocr_only"}}});
  assert.equal(ocr.extractedText, text);
  assert.equal(ocr.extractionProvider, "tesseract");
  const video = buildReportEvidence({content_type: "video", audio_analysis: {transcription: text}});
  assert.equal(video.extractedText, text);
  assert.equal(video.transcription, text);
});

test("successful empty fact-check retrieval is not misreported as provider failure", () => {
  const report = buildReportEvidence({provider_coverage: {google_fact_check: {
    status: "no_results", queries: [{status: "no_results"}]}}});
  assert.equal(report.missing.length, 0);
  assert.equal(report.findings.length, 1);
  assert.match(report.findings[0].detail, /consulta respondeu/);
  assert.match(report.findings[0].detail, /não significa/);
  assert.match(report.findings[0].origin, /1 consultas/);
});

test("fact-check errors and partial retrieval show actual missing coverage", () => {
  const unavailable = buildReportEvidence({provider_coverage: {google_fact_check: {status: "error", reason: "HTTP 403"}}});
  assert.match(unavailable.missing[0], /HTTP 403/);
  const partial = buildReportEvidence({provider_coverage: {google_fact_check: {status: "success",
    queries: [{status: "success"}, {status: "timeout"}]}}});
  assert.match(partial.missing[0], /1 consultas não concluídas/);
});

test("no text and silent input are reading outcomes, not provider failures or truth labels", () => {
  const report = buildReportEvidence({provider_coverage: {
    ocr: {status: "no_text", decision_role: "ocr_only"},
    transcription: {status: "no_speech", decision_role: "transcription_only"}}});
  assert.equal(report.findings.length, 2);
  assert.equal(report.missing.length, 0);
  assert.ok(report.findings.every((item) => item.origin.includes("não é veredito")));
  const silence = buildReportEvidence({content_type: "audio", transcription: "", provider_coverage: {
    transcription: {status: "no_speech", provider: "local_signal_gate", decision_role: "transcription_only"}}});
  assert.equal(silence.missing.length, 0);
  assert.equal(silence.findings.length, 1);
});

test("experimental detector response is not described as evidence weighing on verdict", () => {
  const report = buildReportEvidence({content_type: "image", provider_coverage: {
    huggingface: {status: "success", ai_score: .99, decision_role: "experimental_signal", voting_eligible: false}
  }});
  assert.equal(report.findings.length, 1);
  assert.match(report.findings[0].detail, /não participa do veredito/);
  assert.doesNotMatch(report.findings[0].detail, /99/);
  assert.equal(visibleDetectorScore({ai_score: 1, voting_eligible: false}), null);
  assert.equal(visibleDetectorScore({ai_score: 1, decision_role: "experimental_signal"}), null);
  assert.equal(visibleDetectorScore({ai_score: .99}), .99);
  assert.equal(visibleDetectorScore({ai_score: Infinity}), null);
});

test("unrelated retrieved checks are labelled excluded, never as evidence supporting verdict", () => {
  const accepted = {url: "https://example.com/matched", claim_text: "Afirmação enviada", rating: "Verdadeiro"};
  const unrelated = {url: "https://example.com/other", claim_text: "Outra afirmação", rating: "Falso"};
  const report = buildReportEvidence({claim_assessments: [{claim: "Afirmação enviada", status: "unverified", evidence: [accepted],
    excluded_evidence: [{...unrelated, exclusion_reason: "Afirmação diferente; similaridade não basta."}]}], fact_checks: [accepted, unrelated]});
  assert.match(report.sources[0].kind, /correspondente/);
  assert.equal(report.sources[0].note, "");
  assert.match(report.sources[1].kind, /não usado na decisão/);
  assert.match(report.sources[1].note, /Afirmação diferente/);
});

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

test("video coverage preserves configuration failures and exact partial frame counts", () => {
  const report = buildReportEvidence({content_type: "video", provider_coverage: {
    hive: {status: "not_configured", reason: "Secret Key ausente."},
    sightengine: {status: "partial", analyzed_frames: 1, sampled_frames: 3, failure_reasons: ["Prazo excedido."]}},
    audio_analysis: {provider_coverage: {transcription: {status: "not_configured", decision_role: "transcription_only"}}}});
  assert.match(report.missing[0], /Secret Key ausente/);
  assert.match(report.missing[1], /1 de 3 quadros amostrados/);
  assert.match(report.missing[1], /Prazo excedido/);
  assert.ok(report.missing.some(item => item.includes("Transcrição da fala: serviço não configurado")));
  assert.equal(report.findings.length, 0);
});

test("presence of an audio track does not invent transcription or voice authenticity", () => {
  const report = buildReportEvidence({content_type: "video", media_details: {has_audio: true}});
  assert.equal(report.audioTrackPresent, true);
  assert.equal(report.transcription, "");
  assert.equal(buildReportEvidence({content_type: "video", media_details: {has_audio: false}}).audioTrackPresent, false);
  for (const value of [undefined, "true", 1]) {
    assert.equal(buildReportEvidence({content_type: "video", media_details: {has_audio: value}}).audioTrackPresent, null);
  }
  assert.equal(buildReportEvidence({content_type: "audio", media_details: {has_audio: true}}).audioTrackPresent, null);
});

test("static and truncated page extraction are explained without claiming site verification", () => {
  const report = buildReportEvidence({source_extraction: {method: "static_html", truncated: true}});
  assert.equal(report.findings.length, 1);
  assert.match(report.findings[0].detail, /sem executar JavaScript/);
  assert.match(report.findings[0].detail, /primeiros 5.000 caracteres/);
  assert.match(report.findings[0].origin, /não é uma evidência/);
  const plain = buildReportEvidence({source_extraction: {method: "plain_text", truncated: false}});
  assert.match(plain.findings[0].detail, /sem interpretar marcações como HTML/);
  assert.match(plain.findings[0].detail, /não certifica a legitimidade/);
});

test("video with only synthetic speech indications never attributes them to visual frames", () => {
  const report = buildReportEvidence({content_type: "video", verdict: "AI_Generated", analysis_status: "partial",
    authenticity_status: "ai_indications", detector_disagreement: true, media_details: {has_audio: true},
    visual_authenticity_status: "undetermined", visual_analysis_status: "inconclusive", visual_detector_disagreement: false,
    audio_analysis: {authenticity_status: "ai_indications", analysis_status: "partial", detector_disagreement: true,
      provider_coverage: {hive: {status: "success", ai_score: .98, deepfake_score: 1}}}});
  assert.equal(report.visualOrigin.status, "undetermined");
  assert.equal(report.visualOrigin.detectorDisagreement, false);
  assert.equal(report.audioOrigin.status, "ai_indications");
  assert.equal(report.audioOrigin.detectorDisagreement, true);
  assert.match(report.interpretation, /origem das imagens continua não determinada/);
  assert.match(report.interpretation, /não significa que todo o vídeo foi gerado por IA/);
  const voiceFinding = report.findings.find(item => item.title.includes("áudio/hive"));
  assert.match(voiceFinding.title, /geração de fala por IA/);
  assert.match(voiceFinding.detail, /não sobre imagens/);
  assert.ok(report.findings.every(item => !item.title.includes("manipulação facial")));
});

test("separate visual and audio statuses survive opposite outcomes and disagreements", () => {
  const report = buildReportEvidence({content_type: "video", media_details: {has_audio: true},
    authenticity_status: "ai_indications", detector_disagreement: true,
    visual_authenticity_status: "manipulation_indications", visual_analysis_status: "partial", visual_detector_disagreement: true,
    audio_analysis: {authenticity_status: "undetermined", analysis_status: "inconclusive", detector_disagreement: false}});
  assert.equal(report.visualOrigin.status, "manipulation_indications");
  assert.match(report.visualOrigin.label, /quadros amostrados/);
  assert.match(report.visualOrigin.explanation, /pelo menos um quadro/);
  assert.equal(report.audioOrigin.status, "undetermined");
  assert.equal(report.audioOrigin.detectorDisagreement, false);
  assert.match(report.audioOrigin.label, /não determinada/);
  assert.match(report.interpretation, /não verificam o vídeo inteiro/);
});

test("legacy video does not infer visual or acoustic origin from overall result", () => {
  for (const change of [{}, {visual_authenticity_status: "ai_indications"},
    {visual_analysis_status: "partial"}, {visual_authenticity_status: "unexpected", visual_analysis_status: "partial"}]) {
    const report = buildReportEvidence({content_type: "video", verdict: "AI_Generated", analysis_status: "partial",
      authenticity_status: "ai_indications", detector_disagreement: true, ...change});
    assert.equal(report.visualOrigin.status, "not_separated");
    assert.match(report.visualOrigin.label, /não separada neste relatório/);
    assert.equal(report.visualOrigin.detectorDisagreement, null);
    assert.equal(report.audioOrigin.status, "undetermined");
    assert.match(report.interpretation, /Não podemos atribuir um sinal do áudio às imagens/);
    assert.equal(report.audioTrackPresent, null);
  }
});

test("missing audio track overrides contradictory voice fields without inventing speech or coverage", () => {
  const report = buildReportEvidence({content_type: "video", media_details: {has_audio: false}, transcription: "Inconsistent legacy field",
    visual_authenticity_status: "undetermined", visual_analysis_status: "inconclusive",
    audio_analysis: {authenticity_status: "ai_indications", analysis_status: "partial", detector_disagreement: true,
      transcription: "Inconsistent legacy field", provider_coverage: {hive: {status: "success", ai_score: .99}},
      forensics: {hive: {segments: [{start_seconds: 0, end_seconds: 1, ai_generated_score: .99}]}}}});
  assert.equal(report.audioOrigin.status, "no_track");
  assert.match(report.audioOrigin.explanation, /Não existe faixa de áudio/);
  assert.equal(report.audioOrigin.detectorDisagreement, null);
  assert.equal(report.transcription, "");
  assert.equal(report.extractionMethod, null);
  assert.ok(report.findings.every(item => !item.id.startsWith("audio-segment") && !item.title.includes("áudio/hive")));
});

test("failed or inconclusive dimensions remain undetermined even if a contradictory label says AI", () => {
  for (const state of ["inconclusive", "error", "timeout", undefined]) {
    const report = buildReportEvidence({content_type: "video", media_details: {has_audio: true},
      visual_authenticity_status: "ai_indications", visual_analysis_status: "inconclusive",
      audio_analysis: {authenticity_status: "ai_indications", analysis_status: state, transcription: "Fala legível"}});
    assert.equal(report.visualOrigin.status, "undetermined");
    assert.equal(report.audioOrigin.status, "undetermined");
    assert.equal(report.transcription, "Fala legível");
    assert.match(report.audioOrigin.explanation, /Transcrição disponível não comprova/);
  }
});

test("failed visual layer with separate fields is undetermined, not an AI or legacy conclusion", () => {
  for (const state of ["error", "timeout", "unavailable", "disabled"]) {
    const report = buildReportEvidence({content_type: "video", authenticity_status: "ai_indications",
      visual_authenticity_status: "ai_indications", visual_analysis_status: state});
    assert.equal(report.visualOrigin.status, "undetermined");
    assert.equal(report.visualOrigin.analysisStatus, state);
    assert.match(report.visualOrigin.label, /não determinada/);
  }
});

test("visual scores refer to sampled frames and cannot imply full-video coverage", () => {
  const report = buildReportEvidence({content_type: "video", provider_coverage: {hive: {status: "success", ai_score: .9}}});
  assert.match(report.findings[0].detail, /quadros amostrados, não todas as imagens/);
  assert.equal(report.audioOrigin.status, "undetermined");
});

test("video dimension cards have accessible headings and constrained responsive layout", () => {
  const component = readFileSync(new URL("../src/components/report/EvidenceExplanation.jsx", import.meta.url), "utf8");
  assert.match(component, /aria-labelledby="video-visual-origin-heading"/);
  assert.match(component, /id="video-visual-origin-heading"/);
  assert.match(component, /aria-labelledby="video-audio-origin-heading"/);
  assert.match(component, /id="video-audio-origin-heading"/);
  assert.match(component, /evidence\.visualOrigin\.label/);
  assert.match(component, /evidence\.audioOrigin\.label/);
  assert.match(component, /report-evidence min-w-0 break-words/);
  assert.match(component, /lg:grid-cols-3/);
});

test("main video badge attributes audio-only indications to synthetic speech, never to all images", () => {
  const base = {content_type: "video", verdict: "AI_Generated", analysis_status: "partial", authenticity_status: "ai_indications",
    media_details: {has_audio: true}, audio_analysis: {analysis_status: "partial", authenticity_status: "ai_indications"}};
  const separated = reportMediaHeadline({...base, visual_analysis_status: "inconclusive", visual_authenticity_status: "undetermined"});
  assert.equal(separated.title, "INDÍCIOS DE FALA SINTÉTICA");
  assert.match(separated.headline, /origem das imagens continua não determinada/);
  assert.match(separated.headline, /não significa que todo o vídeo foi gerado por IA/);
  const legacyVisual = reportMediaHeadline(base);
  assert.equal(legacyVisual.title, "INDÍCIOS DE FALA SINTÉTICA");
  assert.match(legacyVisual.headline, /origem visual não está separada/);
});

test("video badge retains positive visual indications while constraining them to samples", () => {
  const visual = {content_type: "video", visual_authenticity_status: "ai_indications", visual_analysis_status: "partial"};
  assert.equal(reportMediaHeadline(visual).title, "INDÍCIOS DE IA EM QUADROS AMOSTRADOS");
  assert.equal(reportMediaHeadline({...visual, audio_analysis: {authenticity_status: "ai_indications", analysis_status: "partial"}}).title,
    "INDÍCIOS DE IA NAS IMAGENS E NO ÁUDIO");
  const manipulated = {...visual, visual_authenticity_status: "manipulation_indications"};
  assert.equal(reportMediaHeadline(manipulated).title, "INDÍCIOS DE MANIPULAÇÃO EM QUADROS");
  assert.match(reportMediaHeadline(manipulated).headline, /quadros amostrados/);
  const missing = reportMediaHeadline({content_type: "video", verdict: "AI_Generated", authenticity_status: "ai_indications"});
  assert.equal(missing.title, "ORIGEM DO VÍDEO NÃO DETERMINADA");
  assert.match(missing.headline, /não separa a conclusão visual/);
});

test("audio headline refers to voice and does not certify cloning or change image/text badges", () => {
  const positive = reportMediaHeadline({content_type: "audio", verdict: "AI_Generated", authenticity_status: "ai_indications", analysis_status: "partial"});
  assert.equal(positive.title, "INDÍCIOS DE FALA SINTÉTICA");
  assert.match(positive.headline, /não comprova clonagem/);
  assert.doesNotMatch(positive.headline, /vídeo|quadros/);
  const missing = reportMediaHeadline({content_type: "audio", verdict: "AI_Generated"});
  assert.equal(missing.title, "ORIGEM DA VOZ NÃO DETERMINADA");
  assert.equal(reportMediaHeadline({content_type: "image", verdict: "AI_Generated"}), null);
  assert.equal(reportMediaHeadline({content_type: "text", verdict: "Scam"}), null);
  const page = readFileSync(new URL("../src/pages/ReportPage.jsx", import.meta.url), "utf8");
  assert.match(page, /reportMediaHeadline\(result\)/);
  assert.match(page, /const badge = mediaHeadline \? \{\.\.\.defaultBadge, \.\.\.mediaHeadline\}/);
});
