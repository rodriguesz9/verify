import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {transformSync} from "esbuild";
import * as reportHelpers from "../src/utils/reportEvidence.js";
import * as reportExportHelpers from "../src/utils/reportExport.js";

const require = createRequire(import.meta.url);
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const evidenceSource = read("../src/components/report/EvidenceExplanation.jsx");
const pageSource = read("../src/pages/ReportPage.jsx");
const audioSource = read("../src/components/demonstracao/AudioDeepfakeDemo.jsx");

function component(source, resolve, result) {
  const module = {exports: {}};
  const compiled = transformSync(source, {loader: "jsx", jsx: "automatic", format: "cjs"}).code;
  new Function("require", "module", "exports", "__TEST_RESULT__", compiled)(resolve, module, module.exports, result);
  return module.exports.default;
}

const EvidenceExplanation = component(evidenceSource, (name) =>
  name === "../../utils/reportEvidence" ? reportHelpers : require(name));

function renderPage(result) {
  const source = pageSource
    .replace("const [result, setResult] = useState(null);", "const [result, setResult] = useState(__TEST_RESULT__);")
    .replace("const [loading, setLoading] = useState(true);", "const [loading, setLoading] = useState(false);");
  const resolve = (name) => {
    if (name === "../utils/reportEvidence") return reportHelpers;
    if (name === "../utils/reportExport") return reportExportHelpers;
    if (name === "../hooks/authContext") return {useAuth: () => ({user: null, loading: false})};
    if (name === "react-router-dom") return {useNavigate: () => () => {}, useParams: () => ({})};
    if (name === "../services/api" || name === "../services/privacyStorage") return new Proxy({}, {
      get: () => () => {throw new Error("Rendering must not access APIs or storage");},
    });
    if (name === "../components/report/EvidenceExplanation") return {__esModule: true, default: EvidenceExplanation};
    if (name === "../components/Footer" || name === "../components/report/AnimatedScore") return {__esModule: true, default: () => null};
    return require(name);
  };
  return renderToStaticMarkup(createElement(component(source, resolve, result)));
}

function renderAudio(result) {
  const source = audioSource.replace("const [result, setResult] = useState(null);", "const [result, setResult] = useState(__TEST_RESULT__);");
  const resolve = (name) => {
    if (name === "../../utils/reportEvidence") return reportHelpers;
    if (name === "../../services/api") return {verifyAudioQuick: () => {throw new Error("Rendering must not call an API");}};
    if (name === "../../services/mediaLifecycle.js") return {createMediaLifecycle: () => ({})};
    return require(name);
  };
  return renderToStaticMarkup(createElement(component(source, resolve, result)));
}

// These components use native, initially closed <details>. Removing their
// subtrees models the visible default text; it does not pretend the data was
// deleted or replace a browser accessibility/layout check.
const visibleDefault = (html) => html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/g, "");

function screenshotControl() {
  return {content_type: "image", verdict: "Suspicious", analysis_status: "inconclusive", score: null,
    authenticity_status: "undetermined", veracity_status: "unverified", summary: "Confira a publicação original.",
    whatsapp_share_text: "Controle de apresentação, não resultado real.", provider_coverage: {
      sightengine: {status: "success", ai_score: .001, deepfake_score: .001},
      huggingface: {status: "unavailable", reason: "Modelo Hugging Face indisponível (HTTP 402).", decision_role: "experimental_signal", voting_eligible: false},
      hive: {status: "not_configured", reason: "Hive v3 exige Secret Key e autorização de custo em HIVE_V3_MEDIA_TYPES."},
      hive_deepfake: {status: "not_configured", reason: "Hive v3 exige Secret Key e autorização de custo em HIVE_V3_MEDIA_TYPES."},
      ocr: {status: "unavailable", decision_role: "ocr_only", reason: "Nenhum provider de OCR retornou texto válido."},
      gemini_vision: {status: "timeout", decision_role: "inspection_only", reason: "Tempo limite da chamada atingido."},
    }};
}

test("public report keeps the inconclusive result without provider cards, scores or configuration errors", () => {
  const result = screenshotControl();
  const before = structuredClone(result);
  const html = renderPage(result);
  const visible = visibleDefault(html);
  assert.match(visible, /ANÁLISE INCONCLUSIVA/);
  assert.match(visible, /Não foi possível chegar a uma conclusão/);
  assert.match(visible, /Não foi possível concluir todas as etapas/);
  assert.doesNotMatch(visible, /Sightengine|Hugging\s?Face|Huggingface|Hive|gemini_vision|HIVE_V3_MEDIA_TYPES|HTTP 402|0\.1%|não calibrado|provider de OCR/i);
  assert.match(html, /Detalhes técnicos da cobertura/);
  assert.match(html, /HIVE_V3_MEDIA_TYPES/);
  assert.match(html, /HTTP 402/);
  assert.doesNotMatch(html, /<details\b[^>]*\bopen(?:=|\s|>)/);
  assert.deepEqual(result, before, "Public presentation must not edit forensic records or verdicts");
});

test("human-readable evidence preserves exact negations, money, date and retrieved sources", () => {
  const literal = "Não pague uma taxa. Valor R$ 123,45. Data 11/10/2026.";
  const result = {...screenshotControl(), forensics: {ocr: {text: literal}},
    provider_coverage: {ocr: {status: "success", decision_role: "ocr_only", provider: "tesseract"}},
    content_analysis: {origin: "ocr", veracity_status: "unverified", query_input: literal,
      claim_assessments: [{claim: literal, status: "unverified", explanation: "A afirmação não foi confirmada.", evidence: []}],
      fact_checks: [{claim_text: literal, publisher: "Fonte de controle", review_date: "2026-10-01", url: "https://example.com/controle"}]}};
  const visible = visibleDefault(renderPage(result));
  assert.match(visible, /Não pague uma taxa\. Valor R\$ 123,45\. Data 11\/10\/2026\./);
  assert.match(visible, /leitura do texto na imagem/);
  assert.match(visible, /não provar como o arquivo foi produzido/);
  assert.match(visible, /Fonte de controle/);
  assert.match(visible, /https:\/\/example\.com\/controle/);
  assert.doesNotMatch(visible, /tesseract|\bOCR\b/i);
});

test("a returned isolated detector score never becomes a public truth or AI finding", () => {
  const result = screenshotControl();
  result.provider_coverage.sightengine.ai_score = .99;
  const evidence = reportHelpers.buildReportEvidence(result);
  assert.equal(evidence.publicFindings.length, 0);
  assert.ok(evidence.technicalFindings.length > 0);
  assert.doesNotMatch(visibleDefault(renderPage(result)), /99\.0%|Sinal de geração por IA|INFORMAÇÃO CORROBORADA/);
});

test("concluded media indications remain visible without calibrating service scores", () => {
  const result = {...screenshotControl(), verdict: "AI_Generated", analysis_status: "partial", authenticity_status: "ai_indications"};
  const visible = visibleDefault(renderPage(result));
  assert.match(visible, /INDÍCIOS DE IA/);
  assert.match(visible, /Indícios sobre a produção do arquivo/);
  assert.match(visible, /nem determina a verdade/);
  assert.doesNotMatch(visible, /0\.1%|HTTP 402|HIVE_V3_MEDIA_TYPES|Sinal de geração por IA/);
});

test("experimental disabled provider alone is not described as a required failed stage", () => {
  const result = {content_type: "image", analysis_status: "partial", authenticity_status: "undetermined",
    provider_coverage: {huggingface: {status: "disabled", voting_eligible: false, decision_role: "experimental_signal"}}};
  const coverage = reportHelpers.publicCoveragePresentation(result);
  assert.equal(coverage.incomplete, false);
  assert.deepEqual(coverage.limitations, []);
  assert.doesNotMatch(coverage.detail, /origem.*confirmada|autêntica garantida/);
});

test("public audio demo keeps pending speech and acoustic uncertainty without showing providers", () => {
  const result = {analysis_status: "inconclusive", verdict: "inconclusivo", transcription: "", short_explanation: "Hive: HTTP 503.",
    transcription_detail: {status: "pending"}, provider_coverage: {
      sightengine_audio: {status: "success", ai_score: .99},
      transcription: {status: "pending", decision_role: "transcription_only", reason: "PRIVATE-ASR-JOB"}},
    indicators: ["Confirme pedidos de Pix por outro canal.", "Hive: HIVE_V3_MEDIA_TYPES ausente."]};
  const html = renderAudio(result);
  const visible = visibleDefault(html);
  assert.match(visible, /Origem da voz inconclusiva/);
  assert.match(visible, /A transcrição ainda está sendo processada/);
  assert.match(visible, /Confirme pedidos de Pix por outro canal/);
  assert.doesNotMatch(visible, /sightengine|Hive|99\.0%|HTTP 503|HIVE_V3_MEDIA_TYPES|PRIVATE-ASR-JOB/i);
  assert.doesNotMatch(html, /PRIVATE-ASR-JOB/);
  assert.doesNotMatch(html, /<details\b[^>]*\bopen(?:=|\s|>)/);
});

test("unknown audio contract is not displayed as confirmed synthetic or green authentic result", () => {
  const html = renderAudio({verdict: "unknown", provider_coverage: {}});
  assert.match(visibleDefault(html), /Origem da voz inconclusiva/);
  const resultCard = html.match(/<section class="mt-7[\s\S]*?<\/section>/)?.[0];
  assert.ok(resultCard);
  assert.match(resultCard, /border-\[#FFCB55\]/);
  assert.doesNotMatch(resultCard, /border-\[#00FF87\]|Indícios de fala sintética/);
});

test("operational diagnostics classifier does not erase ordinary risks or percentages in a message", () => {
  for (const value of ["HTTP 429", "HIVE_V3_MEDIA_TYPES", "Gemini: gemini-3.8-flash", "Hive: não disponível"]) {
    assert.equal(reportHelpers.isTechnicalReportText(value), true);
  }
  for (const value of ["Não pague R$ 123,45.", "Promessa de retorno de 90%", "Pedido de dinheiro urgente", undefined]) {
    assert.equal(reportHelpers.isTechnicalReportText(value), false);
  }
});
