import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {transformSync} from "esbuild";
import * as helpers from "../src/utils/reportEvidence.js";

const require = createRequire(import.meta.url);
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const source = read("../src/components/report/AnimatedScore.jsx");
const module = {exports: {}};
new Function("require", "module", "exports", transformSync(source, {loader: "jsx", jsx: "automatic", format: "cjs"}).code)(
  (name) => name === "../../utils/reportEvidence" ? helpers
    : name === "../../hooks/useAccessibility" ? {useAccessibility: () => ({easyMode: false})}
    : require(name), module, module.exports);
const Score = module.exports.default;

test("unknown score has readable text without a fake bar or percentage", () => {
  const html = renderToStaticMarkup(createElement(Score, {value: null}));
  assert.match(html, /report-score-empty/);
  assert.match(html, /Não determinado/);
  assert.doesNotMatch(html, /progressbar|aria-valuenow|sm:w-64/);
});

test("report stacks title and score until a roomy desktop breakpoint", () => {
  const page = read("../src/pages/ReportPage.jsx");
  assert.match(page, /report-result-layout grid min-w-0/);
  assert.match(page, /lg:grid-cols-\[minmax\(0,1fr\)_15rem\]/);
  const css = read("../src/index.css");
  assert.match(css, /html\[data-elderly-mode="true"\] \.report-score-empty\s*\{\s*overflow-wrap: normal;\s*word-break: normal;/);
  assert.match(css, /\.report-result-title \{ overflow-wrap: anywhere;/);
});

test("easy mode also stops JavaScript score animation, not just CSS transitions", () => {
  assert.match(source, /preference\.matches \|\| easyMode/);
  assert.match(source, /\[target, easyMode\]/);
});

test("missing literal reproduction is not presented as a factual rejection", () => {
  const headline = helpers.reportSourceHeadline({content_type: "text", verdict: "Suspicious", veracity_status: "unverified",
    source_attribution: {status: "no_results", decision_role: "source_attribution_only", matches: [], coverage: {}}});
  assert.equal(headline.title, "Análise inconclusiva");
  assert.match(headline.headline, /não significa que o conteúdo seja falso/);
});

test("zero remains a real score, not unknown", () => {
  const html = renderToStaticMarkup(createElement(Score, {value: 0}));
  assert.match(html, /aria-valuenow="0"/);
  assert.doesNotMatch(html, /Não determinado/);
});

test("grounded conclusion can name evidence without an uncalibrated score", () => {
  const html = renderToStaticMarkup(createElement(Score, {value: null, label: "Resultado com fontes citadas", unavailableText: "Veja as evidências"}));
  assert.match(html, /Veja as evidências/);
  assert.doesNotMatch(html, /Não determinado|progressbar|aria-valuenow/);
  assert.match(read("../src/pages/ReportPage.jsx"), /groundedConclusion \? "Veja as evidências"/);
  assert.match(read("../src/pages/ReportPage.jsx"), /inconclusive \|\| diagnosisHeadline\?\.diagnostic \? "Resultado da análise"/);
});
