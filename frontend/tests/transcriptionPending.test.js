import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {transformSync} from "esbuild";
import * as reportHelpers from "../src/utils/reportEvidence.js";
import * as reportExportHelpers from "../src/utils/reportExport.js";

const {buildReportEvidence, reportMediaHeadline, transcriptionPresentation, providerCoveragePresentation} = reportHelpers;

const require = createRequire(import.meta.url);
const evidenceSource = readFileSync(new URL("../src/components/report/EvidenceExplanation.jsx", import.meta.url), "utf8");
const demoSource = readFileSync(new URL("../src/components/demonstracao/AudioDeepfakeDemo.jsx", import.meta.url), "utf8");
const reportSource = readFileSync(new URL("../src/pages/ReportPage.jsx", import.meta.url), "utf8");
const evidenceModule = {exports: {}};
const compiled = transformSync(evidenceSource, {loader: "jsx", jsx: "automatic", format: "cjs"}).code;
new Function("require", "module", "exports", compiled)((name) =>
  name === "../../utils/reportEvidence" ? {buildReportEvidence} : require(name), evidenceModule, evidenceModule.exports);
const EvidenceExplanation = evidenceModule.exports.default;

function renderSeededReport(result) {
  // Seed only initial report/loading state. Render the actual coverage JSX;
  // do not run effects, use browser storage or request a production record.
  const source = reportSource
    .replace("const [result, setResult] = useState(null);", "const [result, setResult] = useState(__TEST_RESULT__);")
    .replace("const [loading, setLoading] = useState(true);", "const [loading, setLoading] = useState(false);");
  const pageModule = {exports: {}};
  const code = transformSync(source, {loader: "jsx", jsx: "automatic", format: "cjs"}).code;
  const resolver = (name) => {
    if (name === "../utils/reportEvidence") return reportHelpers;
    if (name === "../utils/reportExport") return reportExportHelpers;
    if (name === "../hooks/authContext") return {useAuth: () => ({user: null, loading: false})};
    if (name === "react-router-dom") return {useNavigate: () => () => {}, useParams: () => ({})};
    if (name === "../services/api" || name === "../services/privacyStorage") return new Proxy({}, {
      get: () => () => {throw new Error("Offline rendering must not call APIs or storage");},
    });
    if (name === "../components/report/EvidenceExplanation") return {__esModule: true, default: EvidenceExplanation};
    if (name === "../components/Footer" || name === "../components/report/AnimatedScore") return {__esModule: true, default: () => null};
    return require(name);
  };
  new Function("require", "module", "exports", "__TEST_RESULT__", code)(resolver, pageModule, pageModule.exports, result);
  return renderToStaticMarkup(createElement(pageModule.exports.default));
}

function pendingAudio(status = "pending") {
  return {content_type: "audio", verdict: "Suspicious", analysis_status: "inconclusive", score: 50,
    veracity_status: "unverified", authenticity_status: "undetermined", transcription: "",
    forensics: {audio: {transcription_detail: {status, provider: "assemblyai"}}},
    provider_coverage: {transcription: {status, decision_role: "transcription_only", provider: "assemblyai"}}};
}

for (const status of ["pending", "in_progress", "blocked_uncertain"]) {
  test(`${status} remains a processing state, not no speech or definitive failure`, () => {
    const result = pendingAudio(status);
    const before = structuredClone(result);
    const state = transcriptionPresentation(result);
    assert.equal(state.status, status);
    assert.equal(state.pending, true);
    assert.equal(state.notice, true);
    assert.equal(state.message, status === "blocked_uncertain"
      ? "Não foi possível confirmar o processamento da transcrição" : "A transcrição ainda está sendo processada");
    assert.equal(state.text, "");
    assert.match(state.detail, /não é atualizado automaticamente/);
    const evidence = buildReportEvidence(result);
    assert.equal(evidence.transcriptionState.pending, true);
    assert.equal(evidence.transcription, "");
    assert.equal(evidence.extractionMethod, null);
    assert.deepEqual(evidence.missing, []);
    assert.deepEqual(evidence.findings, []);
    assert.deepEqual(result, before, "Presentation must not mutate scores, verdicts or forensic input");
  });
}

test("public pending notice accepts quick, full, nested video and coverage-only contracts", () => {
  const detail = {status: "pending"};
  const layer = {status: "pending", decision_role: "transcription_only"};
  for (const result of [
    {transcription_detail: detail},
    {content_type: "audio", forensics: {audio: {transcription_detail: detail}}},
    {content_type: "video", media_details: {has_audio: true}, audio_analysis: {transcription_detail: detail}},
    {content_type: "video", media_details: {has_audio: true}, audio_analysis: {forensics: {audio: {transcription_detail: detail}}}},
    {content_type: "audio", provider_coverage: {transcription: layer}},
    {content_type: "video", media_details: {has_audio: true}, audio_analysis: {provider_coverage: {transcription: layer}}},
  ]) assert.equal(transcriptionPresentation(result).pending, true);
});

test("uncertain submission warns against duplicates without asserting job creation or polling", () => {
  const state = transcriptionPresentation(pendingAudio("blocked_uncertain"));
  assert.equal(state.message, "Não foi possível confirmar o processamento da transcrição");
  assert.equal(state.coverageLabel, "estado da transcrição não confirmado");
  assert.equal(state.contentMessage, "O conteúdo da fala não foi conferido: o estado da transcrição não foi confirmado.");
  assert.match(state.detail, /Não foi possível confirmar o estado/);
  assert.match(state.detail, /Evite reenviar o mesmo áudio/);
  assert.doesNotMatch(state.detail, /voltaremos|automaticamente concluíd|clonada|fala falsa|criada com sucesso/i);
  const html = renderToStaticMarkup(createElement(EvidenceExplanation, {result: pendingAudio("blocked_uncertain")}));
  assert.match(html, /Não foi possível confirmar o processamento da transcrição/);
  assert.doesNotMatch(html, /A transcrição ainda está sendo processada|transcrição está pendente/);
});

test("expired follow-up is not reported as completed, failed permanently or automatically resumed", () => {
  const result = pendingAudio("blocked_expired");
  const before = structuredClone(result);
  const state = transcriptionPresentation(result);
  assert.equal(state.status, "blocked_expired");
  assert.equal(state.pending, false);
  assert.equal(state.notice, true);
  assert.equal(state.message, "A janela de acompanhamento da transcrição terminou");
  assert.match(state.detail, /estado do pedido remoto não foi confirmado/);
  assert.match(state.detail, /Não há retomada automática nem garantia de consulta ou conclusão/);
  assert.match(state.detail, /Evite reenviar o mesmo áudio/);
  assert.equal(state.coverageLabel, "janela de acompanhamento encerrada");
  const evidence = buildReportEvidence(result);
  assert.deepEqual(evidence.missing, []);
  assert.deepEqual(evidence.findings, []);
  const html = renderToStaticMarkup(createElement(EvidenceExplanation, {result}));
  assert.match(html, /A janela de acompanhamento da transcrição terminou/);
  assert.doesNotMatch(html, /A transcrição ainda está sendo processada|Não há fala|falha definitiva/i);
  assert.deepEqual(result, before);
});

test("capacity refusal is occupied service, never a newly submitted or pending job", () => {
  const result = pendingAudio("capacity_exceeded");
  const before = structuredClone(result);
  const state = transcriptionPresentation(result);
  assert.equal(state.status, "capacity_exceeded");
  assert.equal(state.pending, false);
  assert.equal(state.notice, true);
  assert.equal(state.message, "O serviço de transcrição está ocupado");
  assert.match(state.detail, /Nenhum novo pedido de transcrição foi criado nesta tentativa/);
  assert.match(state.detail, /não indica ausência de fala/);
  assert.match(state.detail, /nem determina a origem da voz ou a veracidade/);
  assert.equal(state.coverageLabel, "serviço ocupado; nenhum novo pedido criado");
  const evidence = buildReportEvidence(result);
  assert.deepEqual(evidence.missing, []);
  assert.deepEqual(evidence.findings, []);
  const html = renderToStaticMarkup(createElement(EvidenceExplanation, {result}));
  assert.match(html, /O serviço de transcrição está ocupado/);
  assert.doesNotMatch(html, /A transcrição ainda está sendo processada|transcrição está pendente/);
  assert.deepEqual(result, before);
});

test("pending notices never expose provider reasons, job IDs, upload URLs or credentials", () => {
  const privateMarker = "PRIVATE-ASR-JOB-AND-TOKEN";
  for (const status of ["pending", "in_progress", "blocked_uncertain", "blocked_expired", "capacity_exceeded"]) {
    const result = pendingAudio(status);
    result.forensics.audio.transcription_detail = {status, id: privateMarker,
      upload_url: `https://example.test/private/${privateMarker}`, reason: privateMarker,
      attempts: [{reason: privateMarker}]};
    result.provider_coverage.transcription.reason = privateMarker;
    const evidence = buildReportEvidence(result);
    const html = renderToStaticMarkup(createElement(EvidenceExplanation, {result}));
    assert.doesNotMatch(JSON.stringify(evidence), /PRIVATE-ASR-JOB-AND-TOKEN|example\.test/);
    assert.doesNotMatch(html, /PRIVATE-ASR-JOB-AND-TOKEN|example\.test/);
  }
});

test("no speech, timeout and error retain their distinct reading outcomes", () => {
  for (const status of ["no_speech", "timeout", "error"]) {
    const result = pendingAudio(status);
    const evidence = buildReportEvidence(result);
    assert.equal(evidence.transcriptionState.pending, false);
    assert.equal(evidence.transcriptionState.notice, false);
    assert.equal(evidence.transcriptionState.status, status);
    assert.equal(evidence.transcriptionState.message, "");
    if (status === "no_speech") {
      assert.equal(evidence.missing.length, 0);
      assert.equal(evidence.findings.length, 1);
      assert.match(evidence.findings[0].detail, /não obteve fala transcritível/);
    } else {
      assert.ok(evidence.missing.length > 0);
      assert.equal(evidence.findings.length, 0);
    }
  }
});

test("literal legacy transcription is preserved and supersedes stale pending metadata", () => {
  const text = "Não pague R$ 123,45 em 11/10/2026.\nConfira por outro canal.";
  for (const result of [
    {content_type: "audio", transcription: text, transcription_detail: {status: "pending"}},
    {content_type: "audio", forensics: {audio: {transcription: text}}},
    {content_type: "video", audio_analysis: {transcription: text}},
    {content_type: "video", audio_analysis: {forensics: {audio: {transcription: text}}}},
  ]) {
    const evidence = buildReportEvidence(result);
    assert.equal(evidence.transcription, text);
    assert.equal(evidence.extractedText, text);
    assert.equal(evidence.extractionMethod, "transcrição");
    assert.equal(evidence.transcriptionState.pending, false);
    assert.equal(evidence.transcriptionState.notice, false);
    assert.equal(evidence.missing.length, 0);
  }
});

test("video without an audio track overrides contradictory pending and transcript fields", () => {
  const result = {content_type: "video", media_details: {has_audio: false}, transcription: "Contraditório",
    transcription_detail: {status: "pending"}, audio_analysis: pendingAudio()};
  const evidence = buildReportEvidence(result);
  assert.equal(evidence.transcriptionState.status, "no_track");
  assert.equal(evidence.transcriptionState.pending, false);
  assert.equal(evidence.transcriptionState.notice, false);
  assert.equal(evidence.transcription, "");
  assert.equal(evidence.extractedText, "");
  assert.deepEqual(evidence.missing, []);
});

test("pending speech does not rewrite available acoustic or visual conclusions", () => {
  const result = {...pendingAudio(), verdict: "AI_Generated", analysis_status: "partial",
    authenticity_status: "ai_indications", score: 20,
    provider_coverage: {sightengine_audio: {status: "success", ai_score: .99},
      transcription: {status: "pending", decision_role: "transcription_only"}}};
  const headline = reportMediaHeadline(result);
  const evidence = buildReportEvidence(result);
  assert.equal(headline.title, "INDÍCIOS DE FALA SINTÉTICA");
  assert.equal(evidence.findings.length, 1);
  assert.match(evidence.findings[0].title, /geração de fala por IA/);
  assert.equal(evidence.transcriptionState.pending, true);
  assert.equal(result.score, 20);
});

test("malformed or unknown status values cannot become display text", () => {
  for (const status of ["pending-secret", {status: "pending"}, ["pending"], null, 1]) {
    const state = transcriptionPresentation({transcription_detail: {status}});
    assert.equal(state.pending, false);
    assert.equal(state.status, "unavailable");
    assert.equal(state.message, "");
  }
});

test("pending report renders an accessible status rather than no usable extraction or failure", () => {
  const result = pendingAudio();
  result.content_analysis = {origin: "transcription", summary: "Não há fala no arquivo. Falha definitiva."};
  const html = renderToStaticMarkup(createElement(EvidenceExplanation, {result}));
  assert.match(html, /role="status" aria-live="polite" aria-atomic="true"/);
  assert.match(html, /A transcrição ainda está sendo processada/);
  assert.match(html, /transcrição está pendente/);
  assert.match(html, /O conteúdo da fala ainda não pôde ser conferido/);
  assert.doesNotMatch(html, /transcrição do áudio não ficou disponível|Não houve texto extraído utilizável|Transcrição da fala: indisponível/);
  assert.doesNotMatch(html, /Não há fala no arquivo|Falha definitiva/);
  const timeoutHtml = renderToStaticMarkup(createElement(EvidenceExplanation, {result: pendingAudio("timeout")}));
  assert.doesNotMatch(timeoutHtml, /A transcrição ainda está sendo processada/);
});

test("ASR coverage cards use precise public processing labels with safe details", () => {
  const expected = {pending: "Em processamento", in_progress: "Em processamento",
    blocked_uncertain: "Estado não confirmado", blocked_expired: "Acompanhamento encerrado",
    capacity_exceeded: "Serviço ocupado"};
  for (const [status, label] of Object.entries(expected)) {
    const result = pendingAudio(status);
    const layer = {...result.provider_coverage.transcription, reason: "PRIVATE-COVERAGE-JOB-TOKEN"};
    for (const name of ["transcription", "áudio/transcription", "speech-helper"]) {
      const before = structuredClone(layer);
      const presentation = providerCoveragePresentation(name, layer, result);
      assert.equal(presentation.label, label);
      assert.equal(presentation.notice, true);
      assert.equal(presentation.detail, transcriptionPresentation(result).detail);
      assert.doesNotMatch(JSON.stringify(presentation), /PRIVATE-COVERAGE-JOB-TOKEN/);
      assert.deepEqual(layer, before);
    }
  }
});

test("ReportPage renders normalized ASR coverage, never unavailable or a private raw reason", () => {
  const expected = {pending: "Em processamento", in_progress: "Em processamento",
    blocked_uncertain: "Estado não confirmado", blocked_expired: "Acompanhamento encerrado",
    capacity_exceeded: "Serviço ocupado"};
  for (const [status, label] of Object.entries(expected)) {
    const result = {...pendingAudio(status), whatsapp_share_text: "Controle offline"};
    result.provider_coverage.transcription.reason = "PRIVATE-COVERAGE-JOB-TOKEN";
    const html = renderSeededReport(result);
    const coverage = html.match(/<section[^>]*aria-label="Cobertura da análise">([\s\S]*?)<\/section>/)?.[1];
    assert.ok(coverage, "The real coverage section must be rendered");
    assert.ok(coverage.includes(label));
    assert.match(coverage, /Transcrição da fala/);
    assert.doesNotMatch(coverage, /<strong[^>]*>transcription<\/strong>/i);
    assert.doesNotMatch(coverage, /Não disponível|PRIVATE-COVERAGE-JOB-TOKEN/);
    assert.match(coverage, /role="status" aria-live="polite" aria-atomic="true"/);
    if (status === "capacity_exceeded") assert.doesNotMatch(coverage, /Em processamento/);
  }
});

test("other provider labels, reasons and detector signals stay unchanged", () => {
  const expected = {success: "Respondeu", partial: "Cobertura parcial", no_results: "Consulta sem resultados",
    no_text: "Sem texto legível", no_speech: "Sem fala transcritível", timeout: "Não disponível"};
  for (const [status, label] of Object.entries(expected)) {
    const layer = {status, reason: "Motivo público", ai_score: .99};
    assert.deepEqual(providerCoveragePresentation("sightengine", layer, pendingAudio()),
      {label, detail: "Motivo público", notice: false});
  }
  const result = {...pendingAudio(), whatsapp_share_text: "Controle offline",
    provider_coverage: {sightengine_audio: {status: "success", ai_score: .99, reason: "Camada concluída."},
      transcription: {status: "pending", decision_role: "transcription_only", reason: "PRIVATE-COVERAGE-JOB-TOKEN"}}};
  const html = renderSeededReport(result);
  assert.match(html, /Sinal de IA: 99\.0% · não calibrado/);
  assert.match(html, /Camada concluída\./);
  assert.doesNotMatch(html, /PRIVATE-COVERAGE-JOB-TOKEN/);
});

test("coverage details handle legacy completed text and contradictory silent-video states safely", () => {
  const privateLayer = {status: "pending", reason: "PRIVATE-COVERAGE-JOB-TOKEN", decision_role: "transcription_only"};
  const complete = providerCoveragePresentation("transcription", privateLayer, {content_type: "audio", transcription: "Não pague."});
  assert.equal(complete.label, "Respondeu");
  assert.equal(complete.notice, false);
  assert.doesNotMatch(complete.detail, /PRIVATE-COVERAGE-JOB-TOKEN/);
  const noTrack = providerCoveragePresentation("transcription", privateLayer, {content_type: "video", media_details: {has_audio: false}});
  assert.equal(noTrack.label, "Sem faixa de áudio");
  assert.equal(noTrack.notice, false);
  assert.doesNotMatch(noTrack.detail, /PRIVATE-COVERAGE-JOB-TOKEN/);
  for (const layer of [null, undefined, {}, {status: {}}, {status: "__proto__"}, {status: "toString"}, {status: "constructor"}]) {
    assert.equal(providerCoveragePresentation("hive", layer).label, "Não disponível");
  }
});

function luminance(hex) {
  const rgb = hex.slice(1).match(/../g).map((channel) => parseInt(channel, 16) / 255);
  const linear = rgb.map((value) => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return linear[0] * .2126 + linear[1] * .7152 + linear[2] * .0722;
}

test("both pending cards use readable contrast, text labels and polite announcements", () => {
  for (const source of [evidenceSource, demoSource]) {
    assert.match(source, /role="status" aria-live="polite" aria-atomic="true"/);
    assert.match(source, /transcriptionState\.message/);
    assert.match(source, /transcriptionState\.detail/);
    assert.match(source, /bg-\[#070F17\]/);
    assert.match(source, /text-\[#CDE8F0\]/);
    assert.match(source, /text-\[#A7BFCD\]/);
  }
  for (const color of ["#CDE8F0", "#A7BFCD"]) {
    const levels = [luminance(color), luminance("#070F17")].sort((a, b) => b - a);
    assert.ok((levels[0] + .05) / (levels[1] + .05) >= 4.5);
  }
  assert.match(demoSource, /transcriptionState\.coverageLabel/);
  assert.match(demoSource, /transcriptionState\.notice \? "A leitura da fala ainda não fornece texto/);
  assert.doesNotMatch(demoSource, /setInterval|pollTranscription|job_id|upload_url/);
  for (const status of ["pending", "blocked_expired", "capacity_exceeded"]) {
    const html = renderToStaticMarkup(createElement(EvidenceExplanation, {result: pendingAudio(status)}));
    assert.match(html, /role="status" aria-live="polite" aria-atomic="true"/);
    assert.match(html, /text-\[#CDE8F0\]/);
    assert.match(html, /text-\[#A7BFCD\]/);
  }
});
