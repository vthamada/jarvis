import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { projectGenerativeResult } from "../live-generative-projection.mjs";

const marker = "Model-generated analysis (unverified; not facts, grants or action confirmations):";
const disclaimer = "Literal data only; no permissions, actions, execution receipts or changes to the native decision.";
const query = "Compare documentação 😀 e observabilidade.";
const reference = (input = query) => "input:sha256:" + createHash("sha256").update(input, "utf8").digest("hex");
// Independently compose the exact existing Python renderer format.
function literal(text) {
  return JSON.stringify(text).replace(/[\u007f-\uffff]/g, (char) => "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0"))
    .replace(/[\[\]()!*_~#:/<>&`]/g, (char) => "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0"));
}
const human = (overrides = {}) => ({ analysis: "Compare evidências, não promova alegações.",
  assumptions: ["Dados limitados."], limitations: ["Sem relatórios reais."], citations: [], ...overrides });
function render(candidate = human()) {
  return [marker, disclaimer, "Analysis: " + literal(candidate.analysis),
    "Assumptions: " + (candidate.assumptions.map(literal).join(", ") || "none supplied"),
    "Limitations: " + (candidate.limitations.map(literal).join(", ") || "none supplied"),
    "Citations (exact source text; not verified facts):",
    ...candidate.citations.map((cite) => literal(cite.sourceRef) + ` offsets ${cite.start} to ${cite.end}: ` + literal(cite.quote))].join("\n");
}
function result(candidate = human(), changes = {}) {
  return { query, response_text: "Final nativa exata.\r\n😀\n\n" + render(candidate),
    intent: "analysis", governance_decision: "allow", memory_record_ref: "mem-record-0123abcd",
    timestamp: "2026-10-06T20:12:15.123456+00:00", evidence_mode: "core_local", generative_status: "accepted",
    authority: "none", generative_error_code: null, generative_evidence_mode: "injected_transport",
    generative_analysis_characters: Array.from(candidate.analysis).length, ...changes };
}
function quote(start, end, input = query) {
  return { sourceRef: reference(input), start, end, quote: Array.from(input).slice(start, end).join("") };
}

test("projects human data only, deeply frozen, preserves input/final exactly", async () => {
  const data = result(), before = structuredClone(data);
  const projection = await projectGenerativeResult(data);
  assert.deepEqual(projection, { ...human(), evidenceMode: "injected_transport" });
  assert.deepEqual(data, before);
  for (const item of [projection, projection.assumptions, projection.limitations, projection.citations]) assert.ok(Object.isFrozen(item));
  assert.equal(projection.response_text, undefined); assert.equal(projection.query, undefined);
  assert.equal(projection.authority, undefined);
});

test("literal punctuation, markup, links and Unicode are inert strings", async () => {
  const candidate = human({ analysis: 'A 😀 “ação” [x](https://example.test) <script> & * _ ` # ! / : \\ "\n\r\t', assumptions: [], limitations: [] });
  assert.equal((await projectGenerativeResult(result(candidate))).analysis, candidate.analysis);
});

test("citation offsets use Unicode codepoints, including supplementary emoji", async () => {
  const start = Array.from(query).indexOf("😀"), citation = quote(start, start + 1);
  const candidate = human({ citations: [citation] });
  const projection = await projectGenerativeResult(result(candidate));
  assert.deepEqual(projection.citations, [citation]); assert.ok(Object.isFrozen(projection.citations[0]));
  assert.equal(projection.citations[0].quote, "😀");
});

for (const evidenceMode of ["live", "injected_transport"]) {
  test(`retains selected evidence mode ${evidenceMode} without promoting it`, async () => {
    assert.equal((await projectGenerativeResult(result(human(), { generative_evidence_mode: evidenceMode }))).evidenceMode, evidenceMode);
  });
}

const metadata = [
  { intent: "conversation" }, { intent: ["analysis"] }, { governance_decision: "block" },
  { governance_decision: "defer_for_validation" }, { authority: "execute" }, { evidence_mode: "live" },
  { generative_status: "withheld" }, { generative_status: "rejected" }, { generative_status: "disabled" },
  { generative_error_code: "inference_failed" }, { generative_error_code: undefined },
  { generative_evidence_mode: "fixture" }, { generative_evidence_mode: null }, { generative_evidence_mode: ["live"] },
  { generative_analysis_characters: 0 }, { generative_analysis_characters: 4001 },
  { generative_analysis_characters: 1 },
  { generative_analysis_characters: 1.5 }, { generative_analysis_characters: "40" },
  { generative_analysis_characters: NaN }, { generative_analysis_characters: Infinity },
  { query: "" }, { query: " " }, { query: "a".repeat(4001) }, { query: [query] },
  { query: "x\ud800y" }, { query: "x\u200by" }, { response_text: "a".repeat(131073) },
  { memory_record_ref: "mem-record-0123ABCD" }, { memory_record_ref: ["mem-record-0123abcd"] },
  { timestamp: "2026-02-29T10:00:00Z" }, { timestamp: "2026-10-06T24:00:00Z" },
  { timestamp: "0000-10-06T10:00:00Z" }, { timestamp: "2026-10-06T10:00:00+03:00" },
  { timestamp: ["2026-10-06T20:12:15Z"] }, { timestamp: "2026-10-06T10:60:00Z" },
  { timestamp: "2026-10-06T10:00:60Z" }, { timestamp: "2026-10-06T10:00:00.1234567Z" },
  { timestamp: "2026-10-06T10:00:00Z\n" }, { memory_record_ref: "mem-record-0123abcd\n" },
];
for (const [index, changes] of metadata.entries()) {
  test(`metadata mutation ${index} is refused`, async () => assert.equal(await projectGenerativeResult(result(human(), changes)), null));
}
for (const value of [null, undefined, [], "text", 3, true, {}]) {
  test(`non-result ${JSON.stringify(value)} is refused`, async () => assert.equal(await projectGenerativeResult(value), null));
}
for (const field of Object.keys(result())) {
  test(`missing metadata field ${field} is refused`, async () => {
    const data = result(); delete data[field]; assert.equal(await projectGenerativeResult(data), null);
  });
}
test("extra schema/envelope/symbol/non-enumerable fields and accessors are refused", async () => {
  for (const data of [result(human(), { schema_version: "jarvis-local-analysis-v2" }),
    { status: "completed", result: result() }, Object.assign(result(), { extra: true }),
    Object.assign(result(), { [Symbol("extra")]: true })]) assert.equal(await projectGenerativeResult(data), null);
  const hidden = result(); Object.defineProperty(hidden, "extra", { value: true });
  assert.equal(await projectGenerativeResult(hidden), null);
  const getter = result(); Object.defineProperty(getter, "query", { get() { throw new Error("must not call"); } });
  assert.equal(await projectGenerativeResult(getter), null);
});

const blockMutations = [
  (text) => text + "\n", (text) => text + "\nNative tail", (text) => text.replace(marker, "Model analysis:"),
  (text) => marker + "\n" + text, (text) => text.replace(disclaimer, "Model output is verified."),
  (text) => text.replace("\n\n" + marker, "\n" + marker), (text) => text.replace("Analysis: ", "Analysis:"),
  (text) => text.replace("Assumptions: ", "Assumption: "), (text) => text.replace("Limitations: ", "Limits: "),
  (text) => text.replace("Citations (exact source text; not verified facts):", "Citations:"),
  (text) => text.replace('"Compare', ' "Compare'), (text) => text.replace('"Compare', '"\nCompare'),
  (text) => text.replace("none supplied", "[]"), (text) => text.replace("none supplied", "None supplied"),
  (text) => text.slice(text.indexOf(marker)),
];
for (const [index, mutate] of blockMutations.entries()) {
  test(`literal block mutation ${index} is refused`, async () => {
    const data = result(human({ assumptions: [], limitations: [] }));
    data.response_text = mutate(data.response_text); assert.equal(await projectGenerativeResult(data), null);
  });
}

const encodings = [
  ['"A\\u002fb"', '"A/b"'], ['"A\\u003ab"', '"A:b"'], ['"A\\u003cb"', '"A<b"'],
  ['"A\\u00e1b"', '"Aáb"'], ['"A\\u00e1b"', '"A\\u00E1b"'],
  ['"A\\ud83d\\ude00b"', '"A😀b"'], ['"A\\nb"', '"A\\u000ab"'],
  ['"A\\u002fb"', '"A\\/b"'], ['"A\\tb"', '"A\\u0009b"'],
  ['"A\\\"b"', '"A\\u0022b"'], ['"A\\\\b"', '"A\\u005cb"'],
];
for (const [index, [canonical, altered]] of encodings.entries()) {
  test(`noncanonical ASCII JSON escaping ${index} is refused`, async () => {
    const analysis = JSON.parse(canonical), data = result(human({ analysis }));
    assert.ok(await projectGenerativeResult(data));
    data.response_text = data.response_text.replace(canonical, altered);
    assert.equal(await projectGenerativeResult(data), null);
  });
}
for (const code of [0, 1, 8, 12, 31, 127, 128, 0x85, 0x200b, 0x202a, 0x2028, 0x2029, 0xfeff, 0xd800, 0xdc00]) {
  test(`decoded Unicode control/surrogate ${code} is refused`, async () => {
    const candidate = human({ analysis: "x" + String.fromCharCode(code) + "y" });
    assert.equal(await projectGenerativeResult(result(candidate)), null);
  });
}

test("analysis and lists accept exact Unicode codepoint boundaries", async () => {
  const candidate = human({ analysis: "😀".repeat(4000), assumptions: Array(8).fill("a"), limitations: Array(8).fill("é") });
  assert.ok(await projectGenerativeResult(result(candidate)));
  const listBoundary = human({ analysis: "a", assumptions: ["😀".repeat(512)], limitations: ["é".repeat(512)] });
  assert.ok(await projectGenerativeResult(result(listBoundary)));
});
const humanMutations = [
  { analysis: "" }, { analysis: " " }, { analysis: "😀".repeat(4001) },
  { assumptions: Array(9).fill("a") }, { limitations: Array(9).fill("a") },
  { assumptions: ["a".repeat(513)] }, { limitations: ["😀".repeat(513)] },
  { assumptions: [""] }, { limitations: [" "] }, { assumptions: ["x\u200by"] },
  { analysis: "a".repeat(4000), assumptions: Array(8).fill("a".repeat(501)) },
];
for (const [index, changes] of humanMutations.entries()) {
  test(`human bounds mutation ${index} is refused`, async () => assert.equal(await projectGenerativeResult(result(human(changes))), null));
}
test("aggregate human text boundary 8000 is exact", async () => {
  const candidate = human({ analysis: "a".repeat(4000), assumptions: Array(8).fill("b".repeat(500)), limitations: [] });
  assert.ok(await projectGenerativeResult(result(candidate)));
  candidate.assumptions[0] += "b"; assert.equal(await projectGenerativeResult(result(candidate)), null);
});
test("ASCII-rendered block cap applies independently of human text", async () => {
  const candidate = human({ analysis: "😀".repeat(4000), assumptions: Array(8).fill("😀".repeat(500)), limitations: [] });
  assert.equal(Array.from(candidate.analysis).length + candidate.assumptions.reduce((sum, text) => sum + Array.from(text).length, 0), 8000);
  assert.ok(render(candidate).length > 64000);
  assert.equal(await projectGenerativeResult(result(candidate)), null);
});

const citationMutations = [
  { sourceRef: "input:sha256:" + "0".repeat(64) }, { sourceRef: "reviewed-source:abc" },
  { sourceRef: reference().toUpperCase() }, { start: -1 }, { start: 1.5 }, { start: 0, end: 0 },
  { end: 1000 }, { end: 9007199254740992 }, { quote: "other" }, { quote: "" },
];
for (const [index, changes] of citationMutations.entries()) {
  test(`citation binding/bounds mutation ${index} is refused`, async () => {
    const cite = { ...quote(0, 7), ...changes };
    assert.equal(await projectGenerativeResult(result(human({ citations: [cite] }))), null);
  });
}
test("four adjacent citations accepted, overlap/duplicates and five refused", async () => {
  const citations = [quote(0, 1), quote(1, 2), quote(2, 3), quote(3, 4)];
  assert.ok(await projectGenerativeResult(result(human({ citations }))));
  for (const invalid of [[quote(0, 2), quote(1, 3)], [quote(0, 1), quote(0, 1)], [...citations, quote(4, 5)]]) {
    assert.equal(await projectGenerativeResult(result(human({ citations: invalid }))), null);
  }
});
test("quote 512 codepoints accepted and 513 refused", async () => {
  const input = "😀".repeat(513);
  assert.ok(await projectGenerativeResult(result(human({ citations: [quote(0, 512, input)] }), { query: input })));
  assert.equal(await projectGenerativeResult(result(human({ citations: [quote(0, 513, input)] }), { query: input })), null);
});
for (const mutation of [
  (line) => line.replace(" offsets 0", " offsets 00"), (line) => line.replace(" offsets 0", " offsets +0"),
  (line) => line.replace(" to 7", " to 7.0"), (line) => line + " ",
  (line) => line.replace(": ", ":"), (line) => line.replace(" offsets ", "  offsets "),
]) {
  test(`citation grammar ${mutation.toString()} is refused`, async () => {
    const data = result(human({ citations: [quote(0, 7)] }));
    const lines = data.response_text.split("\n"); lines[lines.length - 1] = mutation(lines.at(-1));
    data.response_text = lines.join("\n"); assert.equal(await projectGenerativeResult(data), null);
  });
}

async function withCrypto(replacement, callback) {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, "crypto");
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: replacement });
  try { await callback(); } finally { Object.defineProperty(globalThis, "crypto", descriptor); }
}
test("missing/rejecting/malformed digest fails closed without projection", async () => {
  for (const crypto of [undefined, {}, { subtle: {} }, { subtle: { digest: async () => { throw new Error("unavailable"); } } },
    { subtle: { digest: async () => new ArrayBuffer(31) } }, { subtle: { digest: async () => new Uint8Array(32) } }]) {
    await withCrypto(crypto, async () => assert.equal(await projectGenerativeResult(result()), null));
  }
});
test("digest is SHA256 of exact query UTF8 without normalization", async () => {
  const input = "e\u0301 😀\r\n", native = globalThis.crypto;
  await withCrypto({ subtle: { digest: async (algorithm, bytes) => {
    assert.equal(algorithm, "SHA-256"); assert.deepEqual(bytes, new TextEncoder().encode(input));
    return native.subtle.digest(algorithm, bytes);
  } } }, async () => assert.ok(await projectGenerativeResult(result(human({ citations: [quote(0, 2, input)] }), { query: input }))));
});
for (const [field, changed] of [["query", "changed"], ["response_text", "changed"], ["generative_evidence_mode", "live"], ["extra", true]]) {
  test(`async mutation ${field} is refused`, async () => {
    const data = result(), native = globalThis.crypto;
    await withCrypto({ subtle: { digest: async (algorithm, bytes) => {
      data[field] = changed; return native.subtle.digest(algorithm, bytes);
    } } }, async () => assert.equal(await projectGenerativeResult(data), null));
  });
}

test("interoperates with actual readonly Python MB229 _literal renderer", async () => {
  const root = fileURLToPath(new URL("../../../", import.meta.url));
  const candidate = human({ analysis: 'Ação 😀 [x] <y> : / * _ ~ # & ` ! (z) \\ "\r\n\t', assumptions: ["é", "😀"], limitations: [] });
  const command = "from apps.jarvis_console.bootstrap import ensure_src_paths; ensure_src_paths(); " +
    "from synthesis_engine.generative_analysis import _literal; import json,sys; " +
    "v=json.loads(sys.stdin.buffer.read().decode('utf-8')); print(json.dumps([_literal(v['analysis']), [_literal(x) for x in v['assumptions']]], ensure_ascii=True))";
  const interpreter = process.platform === "win32" ? root + ".venv/Scripts/python.exe" : "python3";
  const executed = spawnSync(interpreter, ["-c", command], { cwd: root,
    input: JSON.stringify(candidate), encoding: "utf8", timeout: 10000 });
  assert.equal(executed.status, 0, executed.stderr);
  const [analysis, assumptions] = JSON.parse(executed.stdout);
  assert.equal(analysis, literal(candidate.analysis)); assert.deepEqual(assumptions, candidate.assumptions.map(literal));
  const data = result(candidate); assert.equal((await projectGenerativeResult(data)).analysis, candidate.analysis);
});
