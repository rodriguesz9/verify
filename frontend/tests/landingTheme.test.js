import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const theme = readFileSync(new URL("../src/index.css", import.meta.url), "utf8");
const landing = readFileSync(new URL("../src/pages/landing.css", import.meta.url), "utf8");

function variable(name) {
  const match = theme.match(new RegExp(`--${name}:\\s*([^;]+);`));
  assert.ok(match, `Missing theme variable: ${name}`);
  const alias = match[1].trim().match(/^var\(--([\w-]+)\)$/);
  return alias ? variable(alias[1]) : match[1].trim();
}

function luminance(hex) {
  const rgb = hex.replace("#", "").match(/../g).map(value => parseInt(value, 16) / 255);
  const linear = rgb.map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return linear[0] * .2126 + linear[1] * .7152 + linear[2] * .0722;
}

function contrast(a, b) {
  const values = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (values[0] + .05) / (values[1] + .05);
}

test("landing and shared navigation use the original blue/cyan branding", () => {
  assert.equal(variable("brand-accent").toUpperCase(), "#00D4FF");
  assert.match(landing, /\.landing-primary \{[^}]*background: var\(--brand-accent\)/);
  assert.match(theme, /\.site-nav-account \{[^}]*background: var\(--brand-accent\)/);
  assert.doesNotMatch(landing, /#(?:7eecc3|63e6c0|81edc5|154c3f)/i);
});

test("blue buttons, links and active Easy Mode retain readable text contrast", () => {
  assert.ok(contrast(variable("brand-accent"), variable("brand-accent-text")) >= 4.5);
  assert.ok(contrast(variable("brand-accent-hover"), variable("brand-accent-text")) >= 4.5);
  for (const background of ["#102733", "#0d1d27", "#113d52"]) {
    assert.ok(contrast(variable("brand-link"), background) >= 4.5);
  }
  assert.ok(contrast("#95e8fa", "#103543") >= 4.5);
});

test("restoring brand colors preserves the illustrative warning color and motion safeguards", () => {
  assert.match(landing, /\.example-alert \{ color: #ffd58a; background: #ffba4315;/);
  assert.match(theme, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(theme, /html\[data-elderly-mode="true"\] \*[^\n]*animation: none !important/);
});
