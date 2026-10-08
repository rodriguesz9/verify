import test from "node:test";
import assert from "node:assert/strict";
import {textInputState, analysisErrorMessage} from "../src/utils/analysisInput.js";

test("text bounds trim only outside whitespace and never truncate", () => {
  assert.equal(textInputState("  Mensagem de teste  ").text, "Mensagem de teste");
  assert.equal(textInputState("x".repeat(5000)).valid, true);
  assert.equal(textInputState("x".repeat(5001)).valid, false);
  assert.equal(textInputState("x".repeat(5001)).text.length, 5001);
  assert.equal(textInputState(" ".repeat(10)).valid, false);
  assert.equal(textInputState("abc").valid, false);
});
test("character bounds match Python Unicode code points", () => {
  assert.equal(textInputState("😀".repeat(5)).length, 5);
  assert.equal(textInputState("😀".repeat(5)).valid, false);
  assert.equal(textInputState("😀".repeat(5000)).valid, true);
});
test("422 validation is explained without displaying provider/raw input details", () => {
  const error = (type) => ({response: {status: 422, data: {detail: [{loc: ["body", "text"], type, msg: "PRIVATE-DIAGNOSTIC", input: "PRIVATE-INPUT"}]}}});
  assert.match(analysisErrorMessage(error("string_too_long")), /5.000/);
  assert.match(analysisErrorMessage(error("string_too_short")), /10 caracteres/);
  assert.doesNotMatch(analysisErrorMessage(error("missing")), /PRIVATE/);
});
test("network, timeout, quota and server failures stay distinguishable", () => {
  assert.match(analysisErrorMessage({code: "ERR_NETWORK"}), /conectar/);
  assert.match(analysisErrorMessage({code: "ECONNABORTED"}), /demorou/);
  assert.match(analysisErrorMessage({response: {status: 429, data: {detail: {error: "limite_diario"}}}}), /limite diário/);
  assert.match(analysisErrorMessage({response: {status: 500}}), /Nenhuma conclusão/);
});
