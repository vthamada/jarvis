import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const markup = readFileSync(new URL("../live-index.html", import.meta.url), "utf8");
const style = readFileSync(new URL("../live-style.css", import.meta.url), "utf8");
const nodes = [], stack = [], voids = new Set(["meta", "link", "input", "br"]);
for (const match of markup.matchAll(/<\/?([a-z][a-z0-9-]*)\b([^>]*)>/gi)) {
  const tag = match[1].toLowerCase();
  if (match[0].startsWith("</")) {
    const node = stack.pop(); assert.equal(node?.tag, tag, `balanced ${tag}`);
    node.closeStart = match.index; node.end = match.index + match[0].length;
  } else {
    const attributes = Object.fromEntries(Array.from(match[2].matchAll(/([^\s=]+)(?:="([^"]*)")?/g),
      (attribute) => [attribute[1], attribute[2] ?? true]));
    const node = { tag, attributes, parent: stack.at(-1), start: match.index,
      openEnd: match.index + match[0].length, closeStart: match.index + match[0].length };
    nodes.push(node); if (!voids.has(tag)) stack.push(node);
  }
}
assert.equal(stack.length, 0);
const byId = (id) => nodes.find((node) => node.attributes.id === id);
const descendant = (node, ancestor) => {
  for (let parent = node?.parent; parent; parent = parent.parent) if (parent === ancestor) return true;
  return false;
};
const content = (node) => markup.slice(node.openEnd, node.closeStart);

test("new compact layout has unique IDs and default unpaired shell", () => {
  const ids = nodes.map((node) => node.attributes.id).filter(Boolean);
  assert.equal(new Set(ids).size, ids.length);
  assert.equal(byId("live-shell").tag, "main");
  assert.equal(byId("live-shell").attributes["data-paired"], "false");
  for (const id of ["live-pairing-details", "live-pairing-summary", "live-canonical-details", "live-canonical-summary"]) assert.ok(byId(id));
});

test("pairing uses native accessible disclosure, initially open", () => {
  const details = byId("live-pairing-details"), summary = byId("live-pairing-summary");
  assert.equal(details.tag, "details"); assert.equal(details.attributes.open, true);
  assert.equal(summary.tag, "summary"); assert.equal(summary.parent, details);
  assert.ok(descendant(byId("pair-title"), summary));
  assert.ok(descendant(byId("live-pair-form"), details));
  assert.ok(descendant(byId("live-pair-help"), details));
  assert.ok(descendant(byId("live-secret"), byId("live-pair-form")));
  assert.equal(byId("live-secret").attributes["aria-describedby"], "live-pair-help");
});

test("refresh and disconnect remain outside collapsible pairing setup", () => {
  for (const id of ["live-refresh", "live-disconnect"]) {
    assert.equal(descendant(byId(id), byId("live-pairing-details")), false);
    assert.equal(byId(id).tag, "button"); assert.equal(byId(id).attributes.type, "button");
  }
});

test("canonical disclosure starts open and contains the exact final output only", () => {
  const details = byId("live-canonical-details"), summary = byId("live-canonical-summary");
  assert.equal(details.tag, "details"); assert.equal(details.attributes.open, true);
  assert.equal(summary.tag, "summary"); assert.equal(summary.parent, details);
  assert.match(content(summary), /Síntese final canônica · integral, sem alterações/);
  const final = byId("live-final"); assert.equal(final.tag, "pre"); assert.equal(final.parent, details);
  assert.equal(content(final), "");
  assert.equal(nodes.filter((node) => node.parent === details).length, 2);
});

test("human projection, registered query and evidence labels are outside final disclosure", () => {
  for (const id of ["live-projection", "live-result-query", "live-metadata", "live-governance"]) {
    assert.equal(descendant(byId(id), byId("live-canonical-details")), false);
    assert.ok(descendant(byId(id), byId("live-result")));
  }
  assert.ok(byId("live-projection").start < byId("live-canonical-details").start);
  assert.match(markup, /Complemento não verificado/); assert.match(markup, /não autentica origem/);
});

test("query, consent and send retain native form semantics without default consent", () => {
  const form = byId("live-form"), query = byId("live-query"), consent = byId("live-generative-consent");
  assert.equal(form.tag, "form"); assert.ok(descendant(query, form)); assert.ok(descendant(consent, form));
  assert.equal(query.tag, "textarea"); assert.equal(query.attributes.rows, "3");
  assert.equal(query.attributes["aria-describedby"], "live-query-help");
  assert.equal(consent.attributes.type, "checkbox"); assert.equal(consent.attributes.checked, undefined);
  assert.equal(consent.attributes["aria-describedby"], "live-generative-help");
  assert.ok(nodes.some((node) => node.tag === "label" && node.attributes.for === consent.attributes.id));
  assert.equal(byId("live-send").attributes.type, "submit"); assert.ok(descendant(byId("live-send"), form));
});

test("memory, host egress and waiting warnings stay visible outside both disclosures", () => {
  for (const id of ["live-query-help", "live-generative-help", "live-notice", "live-ticket"]) {
    const node = byId(id); assert.ok(node);
    assert.equal(descendant(node, byId("live-canonical-details")), false);
    assert.equal(descendant(node, byId("live-pairing-details")), false);
    assert.equal(node.attributes.hidden, undefined);
  }
  assert.match(content(byId("live-query-help")), /registrado na memória canônica/);
  const consent = content(byId("live-generative-help"));
  for (const phrase of ["transporte do perfil selecionado pelo host", "sem envio de histórico",
    "não habilita voz, ferramentas ou ações", "não desfaz uma análise já iniciada", "Desativado por padrão"])
    assert.ok(consent.includes(phrase));
  const wait = nodes.find((node) => node.attributes.class === "muted wait-help");
  assert.ok(wait); assert.match(content(wait), /Não cancela o Core/);
  assert.match(content(wait), /não desfaz registros e não reenvia o pedido/);
  assert.equal(descendant(wait, byId("live-canonical-details")), false);
});

test("optional suggestions come after the operative composer and waiting controls", () => {
  const suggestions = nodes.find((node) => node.attributes.class === "suggestions");
  assert.ok(suggestions.start > byId("live-send").start);
  assert.ok(suggestions.start > byId("live-recover").start);
  assert.ok(suggestions.start > byId("live-notice").start);
  assert.equal(nodes.filter((node) => node.attributes["data-prompt"]).length, 2);
});

test("intro compaction is paired-only, without hiding essential composer warnings", () => {
  assert.match(style, /#live-shell\[data-paired="true"\] \.intro\s*\{/);
  assert.match(style, /#live-shell\[data-paired="true"\] \.intro-copy\s*\{\s*display:none/);
  assert.doesNotMatch(style, /#live-(?:query-help|generative-help|notice|form|send|generative-consent)[^{]*\{[^}]*display:\s*none/);
  assert.match(markup, /Sem modelo generativo, voz ou execução/);
  assert.match(markup, /não uma identidade humana/);
});

test("touch targets and keyboard focus include native disclosure summaries", () => {
  assert.match(style, /button\s*\{[^}]*min-height:44px/);
  assert.match(style, /summary\s*\{[^}]*min-height:44px/);
  assert.match(style, /\.consent\s*\{[^}]*min-height:44px/);
  assert.match(style, /summary:focus-visible\s*\{[^}]*outline:2px/);
  assert.match(style, /input\[type=checkbox\]:focus-visible/);
  assert.match(style, /\.skip:focus/);
  for (const summary of [byId("live-pairing-summary"), byId("live-canonical-summary")]) {
    assert.equal(summary.attributes.tabindex, undefined); assert.equal(summary.attributes["aria-hidden"], undefined);
  }
});

test("mobile CSS keeps full-width primary action and native text wrapping", () => {
  assert.match(style, /@media\(max-width:560px\)/);
  assert.match(style, /\.request-actions #live-send\s*\{\s*flex-basis:100%/);
  assert.match(style, /textarea\s*\{\s*font-size:16px/);
  assert.match(style, /pre\s*\{[^}]*white-space:pre-wrap[^}]*overflow-wrap:anywhere/);
  assert.match(style, /summary\s*\{[^}]*overflow-wrap:anywhere/);
  assert.doesNotMatch(style, /overflow-(?:y|x)\s*:|max-height\s*:|position\s*:\s*(?:fixed|sticky)|100vh/);
});

test("layout adds no external assets, content interpretation or voice/action surface", () => {
  assert.doesNotMatch(markup, /<audio|<iframe|<canvas|type="file"|\son[a-z]+\s*=|javascript:|https?:\/\//);
  assert.doesNotMatch(style, /@import|url\(/);
  assert.equal(nodes.filter((node) => node.tag === "script").length, 1);
  assert.equal(nodes.find((node) => node.tag === "script").attributes.src, "/live-app.mjs");
  assert.equal(nodes.find((node) => node.tag === "link").attributes.href, "/live-style.css");
});
