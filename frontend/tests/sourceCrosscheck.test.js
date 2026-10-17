import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {transformSync} from "esbuild";
import * as helpers from "../src/utils/reportEvidence.js";
import * as exportHelpers from "../src/utils/reportExport.js";

const require = createRequire(import.meta.url);
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const evidenceSource = read("../src/components/report/EvidenceExplanation.jsx");
const pageSource = read("../src/pages/ReportPage.jsx");
function component(source, resolve, result) {
  const module = {exports: {}};
  const compiled = transformSync(source, {loader: "jsx", jsx: "automatic", format: "cjs"}).code;
  new Function("require", "module", "exports", "__TEST_RESULT__", compiled)(resolve, module, module.exports, result);
  return module.exports.default;
}
const Evidence = component(evidenceSource, (name) => name === "../../utils/reportEvidence" ? helpers : require(name));
function renderPage(result) {
  const source = pageSource
    .replace("const [result, setResult] = useState(null);", "const [result, setResult] = useState(__TEST_RESULT__);")
    .replace("const [loading, setLoading] = useState(true);", "const [loading, setLoading] = useState(false);");
  const resolve = (name) => {
    if (name === "../utils/reportEvidence") return helpers;
    if (name === "../utils/reportExport") return exportHelpers;
    if (name === "../hooks/authContext") return {useAuth: () => ({user: null, loading: false})};
    if (name === "react-router-dom") return {useNavigate: () => () => {}, useParams: () => ({})};
    if (name === "../services/api" || name === "../services/privacyStorage") return new Proxy({}, {
      get: () => () => {throw new Error("Offline rendering must not call APIs or storage");},
    });
    if (name === "../components/report/EvidenceExplanation") return {__esModule: true, default: Evidence};
    if (name === "../components/report/AnimatedScore") return {__esModule: true,
      default: ({value}) => createElement("span", {"data-test-score": value === null ? "not-determined" : value}, String(value))};
    if (name === "../components/Footer") return {__esModule: true, default: () => null};
    return require(name);
  };
  return renderToStaticMarkup(createElement(component(source, resolve, result)));
}
const visibleDefault = (html) => html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/g, "");
const literal = "Não houve cobrança de R$ 123,45 em 13/10/2026.";
function fixture(state = "corroborated", changes = {}) {
  const claimState = state === "mixed" ? "corroborated" : state;
  const source = (family, index) => ({source_id: `source-${index}`, excerpt_id: `excerpt-${index}`,
    url: `https://${family}/noticia`, title: `Documento de controle ${index}`,
    excerpt: state === "refuted" ? "Houve cobrança de R$ 123,45 em 13/10/2026." : literal,
    context: `Contexto de controle. ${state === "refuted" ? "Houve cobrança de R$ 123,45 em 13/10/2026." : literal}`,
    relation: state === "refuted" ? "refutes" : "supports",
    reason: state === "refuted" ? "A fonte afirma a cobrança negada no texto enviado, na mesma data e valor."
      : "O trecho corresponde à afirmação com data e valor preservados.", publisher_family: family,
    source_role: "retrieved_reference", retrieved_at: "2026-10-13T13:00:00Z"});
  return {content_type: "text", verdict: state === "corroborated" ? "Authentic" : state === "refuted" ? "False" : "Suspicious",
    analysis_status: state === "insufficient" ? "inconclusive" : "partial", score: 0,
    score_semantics: "not_calibrated_source_corroboration", veracity_decision_basis: "retrieved_sources",
    veracity_decision_coverage_complete: state !== "insufficient",
    veracity_status: ({corroborated: "supported", refuted: "refuted", conflicting: "conflicting", mixed: "mixed"})[state] || "unverified",
    authenticity_status: "not_applicable", query_input: literal, source_corroboration: {
      version: "source_corroboration_v1", decision_role: "grounded_source_comparison", state, status: "success",
      claims: [{claim_id: "claim-0", claim: literal, state: claimState, status: claimState,
        explanation: "Compare a mesma data, valor e negação nos documentos.", evidence: [source("example.com", 0), source("example.org", 1)]}],
      coverage: {literal_claim_count: 1, selected_claim_count: 1, omitted_claim_count: 0, selected_source_count: 2,
        eligible_family_count: 2, complete_claim_coverage: true, assessed_claim_count: 1, grounded_evidence_count: 2},
      limitations: [], provider_coverage: {openrouter: {status: "success", model_used: "PRIVATE-VENDOR/MODEL:free"}},
    }, claim_assessments: [{claim: literal, status: state === "corroborated" ? "supported" : "refuted",
      evidence_mode: "retrieved_sources", evidence: [{}, {}]}],
    provider_coverage: {google_fact_check: {status: "no_results", queries: [{status: "no_results"}]},
      source_crosscheck: {status: "success", decision_role: "grounded_source_comparison", reason: "PRIVATE-VENDOR/MODEL:free"}}, ...changes};
}

test("grounded source presentation preserves literal negation, value, date, relations and consultation", () => {
  const result = fixture();
  const before = structuredClone(result);
  const cross = helpers.sourceCorroborationPresentation(result);
  assert.equal(cross.claims[0].claim, literal);
  assert.equal(cross.claims[0].evidence[0].excerpt, literal);
  assert.equal(cross.claims[0].evidence[0].relationLabel, "Sustenta esta afirmação");
  assert.equal(cross.claims[0].evidence[0].retrievedAt, "2026-10-13T13:00:00Z");
  assert.match(cross.scope, /1 de 1 afirmações selecionadas e 2 documentos/);
  assert.deepEqual(result, before);
});

test("single original record is not presented as two independent confirmations", () => {
  const result = fixture("corroborated", {original_record_only: true});
  result.source_corroboration.claims[0].evidence.splice(1);
  const headline = helpers.reportFactualHeadline(result);
  assert.equal(headline.title, "Confirmada no registro original");
  assert.match(headline.headline, /É uma fonte primária, não duas confirmações independentes/);
  assert.equal(helpers.sourceCorroborationPresentation(result).originalRecordOnly, true);
});

test("source decisions show grounded headlines, never an invented certainty percentage or Google-only rating", () => {
  for (const [state, title] of [["corroborated", "Corroborada nas fontes consultadas"],
    ["refuted", "Refutada nas fontes consultadas"], ["conflicting", "Fontes discordam"], ["mixed", "Conteúdo misto"],
    ["insufficient", "Evidência insuficiente"]]) {
    const result = fixture(state);
    assert.equal(helpers.reportFactualHeadline(result).title, title);
    const html = renderPage(result), visible = visibleDefault(html);
    assert.match(visible, new RegExp(title));
    assert.match(html, /data-test-score="not-determined"/);
    assert.doesNotMatch(visible, /Duas checagens editoriais|Checagens editoriais distintas|2 avaliações correspondentes|PRIVATE-VENDOR|0%|0\/100/);
    assert.match(visible, /Cruzamento de fontes/);
    assert.match(visible, /duas IAs concordarem.*não é uma prova/);
  }
});

test("real source body quotation, relation, original link and consultation date render publicly", () => {
  const html = renderPage(fixture("refuted")), visible = visibleDefault(html);
  assert.match(visible, /Contradiz esta afirmação/);
  assert.match(visible, /Não houve cobrança de R\$ 123,45 em 13\/10\/2026\./);
  assert.match(visible, /href="https:\/\/example\.org\/noticia"/);
  assert.match(visible, /datetime="2026-10-13T13:00:00Z"/i);
  assert.match(visible, /13\/10\/2026/);
  assert.match(visible, /data da consulta, não necessariamente a data de publicação/);
  assert.match(html, /Contexto do trecho/);
  assert.doesNotMatch(html, /<details\b[^>]*\bopen(?:=|\s|>)/);
  assert.doesNotMatch(visible, /Nenhuma evidência específica de falsidade foi registrada/);
});

test("unsafe or invented citations are never displayed as grounded document sources", () => {
  const result = fixture();
  result.source_corroboration.claims[0].evidence = [
    {...result.source_corroboration.claims[0].evidence[0], url: "javascript:alert(1)"},
    {...result.source_corroboration.claims[0].evidence[0], url: "https://user:secret@example.com"},
    {...result.source_corroboration.claims[0].evidence[0], relation: "similar_topic"},
    {...result.source_corroboration.claims[0].evidence[0], excerpt: ""},
  ];
  result.llm_sources = [{url: "https://invented.invalid", excerpt: "Invented"}];
  const cross = helpers.sourceCorroborationPresentation(result);
  assert.deepEqual(cross.claims[0].evidence, []);
  const visible = visibleDefault(renderPage(result));
  assert.match(visible, /Não houve trecho de fonte aceito/);
  assert.doesNotMatch(visible, /javascript:|user:secret|invented\.invalid/);
});

test("unknown source contract version, role or state cannot override saved legacy verdicts", () => {
  for (const change of [{version: "unexpected"}, {decision_role: "llm_vote"}, {state: "certain"}]) {
    const result = fixture();
    result.source_corroboration = {...result.source_corroboration, ...change};
    assert.equal(helpers.sourceCorroborationPresentation(result), null);
    assert.equal(helpers.reportFactualHeadline(result), null);
  }
  const legacy = fixture("insufficient", {verdict: "False", veracity_status: "refuted", veracity_decision_basis: "claim_reviews"});
  assert.equal(helpers.reportFactualHeadline(legacy), null);
  assert.equal(helpers.reportFactualHeadline({content_type: "text", verdict: "Authentic", veracity_status: "supported"}), null);
});

test("partial claim coverage cannot receive global approval; a truncated page is limited to its analyzed excerpt", () => {
  for (const state of ["corroborated", "refuted"]) {
    const partial = fixture(state);
    partial.source_corroboration.coverage.complete_claim_coverage = false;
    partial.veracity_decision_coverage_complete = false;
    assert.equal(helpers.reportFactualHeadline(partial).title, "Evidência insuficiente");
    assert.match(helpers.sourceCorroborationPresentation(partial).limitations.join(" "), /Não é uma aprovação do conteúdo inteiro/);
    const truncated = fixture(state, {content_type: "url", source_extraction: {method: "static_html", truncated: true}});
    assert.equal(helpers.reportFactualHeadline(truncated).title,
      state === "corroborated" ? "Trecho corroborado nas fontes consultadas" : "Trecho refutado nas fontes consultadas");
    assert.match(helpers.reportFactualHeadline(truncated).headline, /vale somente para o trecho analisado/);
    assert.match(visibleDefault(renderPage(truncated)), /restante não foi checado/);
  }
  const combined = fixture("corroborated", {veracity_decision_basis: "mixed_evidence"});
  combined.source_corroboration.coverage.complete_claim_coverage = false;
  assert.equal(helpers.reportFactualHeadline(combined).title, "Corroborada nas fontes consultadas");
  for (const value of [undefined, false, "true", 1]) {
    assert.equal(helpers.reportFactualHeadline({...combined, veracity_decision_coverage_complete: value}).title, "Evidência insuficiente");
  }
});

test("incomplete source layer cannot overwrite an existing editorial ClaimReview decision", () => {
  const result = fixture("insufficient", {verdict: "False", veracity_status: "refuted", analysis_status: "partial",
    veracity_decision_basis: "claim_reviews", claim_assessments: [{claim: literal, status: "refuted", evidence: [{}, {}]}]});
  const report = helpers.buildReportEvidence(result);
  assert.equal(report.veracityStatus, "refuted");
  assert.equal(report.findings.find((item) => item.id === "claim-0").title, "Refutada nas checagens");
  assert.equal(helpers.reportFactualHeadline(result), null);
  assert.match(visibleDefault(renderPage(result)), /AFIRMAÇÃO REFUTADA/);
});

test("a source-backed statement cannot certify the image or voice that carried it", () => {
  const content = fixture();
  const result = {content_type: "image", verdict: "Suspicious", analysis_status: "inconclusive", authenticity_status: "undetermined",
    media_signal: {version: "1", scope: "image", state: "no_high_signal"}, content_analysis: {...content, origin: "ocr"}};
  const report = helpers.buildReportEvidence(result), visible = visibleDefault(renderPage(result));
  assert.equal(helpers.reportFactualHeadline(result), null);
  assert.equal(report.veracityLabel, "Corroborada nas fontes consultadas");
  assert.match(visible, /Sem indícios fortes nas consultas feitas/);
  assert.match(visible, /não prova autenticidade/);
  assert.match(visible, /Corroborada nas fontes consultadas/);
  assert.doesNotMatch(visible, /INFORMAÇÃO CORROBORADA|mídia autêntica garantida/);
});

test("a financial risk warning takes priority over positive source findings, including inconclusive factual coverage", () => {
  const result = fixture("corroborated", {verdict: "Scam", analysis_status: "inconclusive", veracity_status: "unverified",
    scam_analysis: {detected_patterns: [{category: "Pedido financeiro", description: "Confirme antes de pagar.", matched_excerpt: "Pague taxa."}]}});
  assert.equal(helpers.reportFactualHeadline(result), null);
  assert.match(helpers.buildReportEvidence(result).interpretation, /sinais associados a golpes/);
  const visible = visibleDefault(renderPage(result));
  assert.match(visible, /ALERTA: SINAIS DE GOLPE/);
  assert.match(visible, /Não envie dinheiro/);
  assert.match(visible, /não comprovam quem enviou/);
});

test("a restored report uses the same additive contract without changing old signed records", () => {
  const original = fixture("mixed", {veracity_decision_basis: "mixed_evidence"});
  const restored = JSON.parse(JSON.stringify(original));
  assert.equal(helpers.reportFactualHeadline(restored).title, "Conteúdo misto");
  assert.deepEqual(helpers.buildReportEvidence(restored).sourceCorroboration, helpers.buildReportEvidence(original).sourceCorroboration);
  assert.deepEqual(restored, original);
});

test("source cards have accessible headings, constrained layout and no fabricated progress", () => {
  assert.match(evidenceSource, /aria-labelledby="source-crosscheck-heading"/);
  assert.match(evidenceSource, /id="source-crosscheck-heading"/);
  assert.match(evidenceSource, /min-w-0 rounded-xl/);
  assert.match(evidenceSource, /<time dateTime=\{source\.retrievedAt\}/);
  assert.doesNotMatch(evidenceSource, /dangerouslySetInnerHTML/);
  assert.match(pageSource, /reportFactualHeadline\(result\)/);
});
