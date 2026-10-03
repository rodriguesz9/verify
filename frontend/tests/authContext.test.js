import test from "node:test";
import assert from "node:assert/strict";
import {createElement} from "react";
import {renderToString} from "react-dom/server";
import {AuthCtx, useAuth} from "../src/hooks/authContext.js";

function Consumer() {
  const {user} = useAuth();
  return createElement("span", null, user?.name || "visitante");
}
test("auth consumers read the shared provider context", () => {
  const html = renderToString(createElement(AuthCtx.Provider, {value: {user: {name: "Usuário de teste"}}}, createElement(Consumer)));
  assert.match(html, /Usuário de teste/);
});
test("missing provider produces a clear error instead of silently dropping auth", () => {
  assert.throws(() => renderToString(createElement(Consumer)), /dentro de AuthProvider/);
});
