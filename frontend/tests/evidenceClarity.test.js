import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {transformSync} from "esbuild";
import * as helpers from "../src/utils/reportEvidence.js";

const require = createRequire(import.meta.url);
const source = readFileSync(new URL("../src/components/report/EvidenceExplanation.jsx", import.meta.url), "utf8");
const module = {exports: {}};
new Function("require", "module", "exports", transformSync(source, {loader: "jsx", jsx: "automatic", format: "cjs"}).code)(
  (name) => name === "../../utils/reportEvidence" ? helpers : require(name), module, module.exports);
const Evidence = module.exports.default;
const render = (result) => renderToStaticMarkup(createElement(Evidence, {result}));

const claim = "Em 11 de março de 2020, a OMS caracterizou a COVID-19 como uma pandemia.";
function fixture(attributionStatus = "no_results") {
  return {content_type: "text", analysis_status: "partial", veracity_status: "supported",
    veracity_decision_basis: "retrieved_sources", veracity_decision_coverage_complete: true,
    source_corroboration: {version: "source_corroboration_v1", decision_role: "grounded_source_comparison",
      state: "corroborated", status: "success", coverage: {complete_claim_coverage: true},
      claims: [{claim, state: "corroborated", evidence: [{url: "https://www.who.int/control",
        title: "Documento original de controle", publisher_family: "WHO", source_role: "retrieved_reference",
        relation: "supports", excerpt: "We have made the assessment that COVID-19 can be characterized as a pandemic."}]}]},
    source_attribution: {status: attributionStatus, decision_role: "source_attribution_only", matches: [],
      coverage: {selected_claim_count: 1, selected_url_count: 2, fetched_count: 2},
      limitations: ["Pesquisa limitada aos documentos selecionados."]}};
}

function literalDetailsOpening(html) {
  const summaryIndex = html.indexOf('<summary id="source-attribution-heading"');
  assert.ok(summaryIndex > 0);
  const tag = html.slice(0, summaryIndex).match(/<details\b[^>]*>$/);
  assert.ok(tag, "Literal research must use native details with an accessible summary");
  return tag[0];
}

test("absence of a literal copy is a closed supplementary search, not a conflicting verdict", () => {
  const result = fixture(), before = structuredClone(result), html = render(result);
  assert.doesNotMatch(literalDetailsOpening(html), /\bopen(?:=|\s|>)/);
  assert.match(literalDetailsOpening(html), /min-w-0/);
  assert.match(html, /Pesquisa de reprodução literal/);
  assert.match(html, /não encontrar uma cópia literal não confirma nem refuta a informação/);
  assert.match(html, /Nenhuma reprodução literal localizada/);
  assert.doesNotMatch(html, /Sem correspondência nas fontes consultadas/);
  assert.match(html, /Pesquisa limitada aos documentos selecionados/);
  assert.match(html, /1 frases selecionadas, 2 páginas selecionadas e 2 páginas com leitura concluída/);
  assert.match(html, /Cruzamento de fontes/);
  assert.match(html, /href="https:\/\/www\.who\.int\/control"/);
  assert.match(html, /Sustenta esta afirmação/);
  assert.match(html, /We have made the assessment that COVID-19 can be characterized as a pandemic\./);
  assert.deepEqual(result, before, "Presentation must not change evidence or verdicts");
});

test("empty published-check list does not imply absence of grounded documents", () => {
  const html = render(fixture());
  assert.match(html, /Checagens já publicadas e notícias relacionadas/);
  assert.match(html, /não retornou checagens já publicadas nem notícias relacionadas para esta lista/);
  assert.match(html, /Os documentos e trechos aceitos pelo cruzamento de fontes, quando disponíveis, estão na seção acima/);
  assert.match(html, /ausência nesta lista não determina o veredito/);
  assert.doesNotMatch(html, /Nenhuma referência externa de checagem/);
});

test("unavailable literal research remains explicit and cannot imply no matches", () => {
  for (const status of ["error", "not_configured"]) {
    const html = render(fixture(status));
    assert.doesNotMatch(literalDetailsOpening(html), /\bopen(?:=|\s|>)/);
    assert.match(html, status === "error" ? /A pesquisa de publicações não foi concluída/ : /A pesquisa de publicações não está habilitada/);
    assert.doesNotMatch(html, /Nenhuma reprodução literal localizada/);
  }
});

test("literal matches retain their exact text, source link and attribution-only warning", () => {
  const result = fixture("found");
  result.source_attribution.matches = [{url: "https://example.test/control", title: "Publicação de controle",
    claim, excerpt: claim, match_method: "literal_sentence", source_role: "retrieved_reference"}];
  const html = render(result);
  assert.match(html, /<section\b[^>]*aria-labelledby="source-attribution-heading"/);
  assert.match(html, /<h4 id="source-attribution-heading"/);
  assert.ok(html.includes(claim));
  assert.match(html, /href="https:\/\/example\.test\/control"/);
  assert.match(html, /correspondência literal/);
  assert.match(html, /não é uma avaliação de verdade ou falsidade/);
});

test("related sources remain visible without claiming they are confirmations", () => {
  const result = fixture();
  result.serper_news = [{title: "Notícia relacionada de controle", source: "Fonte de controle", link: "https://example.test/news"}];
  const html = render(result);
  assert.match(html, /Notícia relacionada de controle/);
  assert.match(html, /Notícia encontrada · não é confirmação automática/);
  assert.match(html, /href="https:\/\/example\.test\/news"/);
  assert.doesNotMatch(html, /A busca não retornou checagens/);
});
