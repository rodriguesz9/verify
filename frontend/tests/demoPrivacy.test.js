import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const demo = readFileSync(new URL("../src/pages/DemonstracaoPage.jsx", import.meta.url), "utf8");
const report = readFileSync(new URL("../src/pages/ReportPage.jsx", import.meta.url), "utf8");
const whatsapp = readFileSync(new URL("../src/components/demonstracao/WhatsAppSimulator.jsx", import.meta.url), "utf8");

test("demo subscribes with cleanup and remounts every private interactive child after reset", () => {
  assert.match(demo, /useEffect\(\(\) => subscribeAnalysisReset\(\(\) => \{/);
  assert.match(demo, /setPrivacyEpoch\(\(epoch\) => epoch \+ 1\)/);
  const content = demo.match(/<div key=\{privacyEpoch\} className="transition-all">([\s\S]*?)<\/div>/)?.[1];
  assert.ok(content, "privacy key must apply to the content boundary, not only a header");
  for (const component of ["AudioDeepfakeDemo", "AuthenticitySealDemo", "WhatsAppSimulator", "ForensicTimeline"]) {
    assert.match(content, new RegExp(`<${component} />`));
  }
});

test("reset keeps accessibility/theme and selected demo tab outside the remount boundary", () => {
  const reset = demo.match(/useEffect\(\(\) => subscribeAnalysisReset\(\(\) => \{([\s\S]*?)\}\), \[\]\)/)?.[1];
  assert.ok(reset);
  assert.doesNotMatch(reset, /localStorage|sessionStorage|\.clear\(|setActiveTab/);
  assert.ok(demo.indexOf("<Navbar />") < demo.indexOf("<div key={privacyEpoch}"));
});

test("an anonymous report reset redirects only an already displayed report, not initial hydration", () => {
  assert.match(report, /const hasDisplayedReport = Boolean\(result\) && !loading/);
  const reset = report.match(/useEffect\(\(\) => subscribeAnalysisReset\(\(\) => \{([\s\S]*?)\}\), \[hasDisplayedReport, navigate\]\)/)?.[1];
  assert.ok(reset);
  assert.match(reset, /reportEpoch\.current \+= 1/);
  assert.match(reset, /setResult\(null\)/);
  assert.match(reset, /if \(hasDisplayedReport\) navigate\("\/app", \{ replace: true \}\)/);
  assert.match(report, /if \(authLoading\) return cancel/);
});

test("WhatsApp demo describes a text simulator with accessible controls, not a real gateway or instant truth", () => {
  assert.match(whatsapp, /Não envia mensagens ao WhatsApp real/);
  assert.match(whatsapp, /resultado será inconclusivo/);
  assert.match(whatsapp, /aria-label="Mensagem para testar no simulador"/);
  assert.match(whatsapp, /aria-label="Enviar mensagem de teste"/);
  assert.doesNotMatch(whatsapp, /verifico na hora|proteção ativa|digitando laudo|qualquer notícia, link, áudio/);
});

test("WhatsApp scroll stays inside the chat and respects easy mode and reduced motion", () => {
  assert.doesNotMatch(whatsapp, /scrollIntoView/);
  assert.match(whatsapp, /chat\.scrollTo\(\{ top: chat\.scrollHeight/);
  assert.match(whatsapp, /getAttribute\("data-elderly-mode"\)/);
  assert.match(whatsapp, /prefers-reduced-motion: reduce/);
  assert.match(whatsapp, /behavior: reduceMotion \? "auto" : "smooth"/);
});
