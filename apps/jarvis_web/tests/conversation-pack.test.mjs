import test from "node:test";
import assert from "node:assert/strict";
import { createHash, webcrypto } from "node:crypto";
import { CONVERSATION_PACK_MAX_BYTES, CONVERSATION_PACK_ORIGIN_LABEL,
  createConversationPackController, parseConversationPack, readConversationPackFile,
  renderConversationPack } from "../conversation-pack.mjs";

const encoder = new TextEncoder();
const crypto = webcrypto;
const hash = (query, response) => createHash("sha256")
  .update("jarvis-conversation-pack-v1\0" + query + "\0" + response, "utf8").digest("hex");
const ref = (kind, character = "a") => kind + ":sha256:" + character.repeat(64);
const content = (query = "Compare documentação e observabilidade 😀.", response = "Final nativa exata.\r\nAnálise não verificada.") => ({
  schema_version: "jarvis-conversation-pack-v1", authority: "none", operator_authenticated: false,
  runtime_capability_promoted: false, origin: "canonical_core_export", content_included: true,
  content_withheld: false, principal_ref: ref("principal"), session_ref: ref("session"),
  request_ref: ref("request"), memory_record_ref: ref("memory-record"),
  timestamp: "2026-10-06T14:12:13.123456+00:00", intent: "analysis", governance_decision: "allow",
  generative_status: "disabled", generative_error_code: null, generative_evidence_mode: null,
  generative_analysis_characters: 0, request_character_count: [...query].length,
  response_character_count: [...response].length, content_sha256: hash(query, response),
  query, response_text: response,
});
const metadata = (withheld = false) => {
  const pack = content();
  delete pack.query; delete pack.response_text;
  return { ...pack, content_included: false, content_withheld: withheld, content_sha256: null };
};
const source = (pack = content()) => JSON.stringify(pack);
const file = (pack = content()) => new Blob([source(pack)], { type: "application/json" });
const parse = (value) => parseConversationPack(value, { crypto });
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const fakeFile = (text = source(), changes = {}) => ({ size: encoder.encode(text).byteLength,
  arrayBuffer: async () => encoder.encode(text).buffer,
  get text() { throw new Error("TEXT_DECODING_MUST_NOT_BE_USED"); },
  get name() { throw new Error("PRIVATE_NAME_MUST_NOT_BE_READ"); }, ...changes });

test("strict pack preserves exact unicode content and cryptographic domain separated hash", async () => {
  const pack = content("  Café 😀\r\n\t ", "Resposta <b>exata</b> 😀 ");
  const result = await parse(" \r\n" + source(pack) + "\t ");
  assert.deepEqual(result, pack);
  assert.equal(Object.isFrozen(result), true);
  assert.throws(() => { result.query = "modified"; }, TypeError);
  assert.deepEqual(await readConversationPackFile(file(pack), { crypto }), pack);
});

for (const withheld of [false, true]) {
  test(`metadata-only pack ${withheld} does not invent content or require hash`, async () => {
    const pack = metadata(withheld);
    assert.deepEqual(await parseConversationPack(source(pack), { crypto: null }), pack);
    assert.equal(Object.hasOwn(pack, "query"), false);
  });
}

for (const mode of ["fixture", "injected_transport", "live"]) {
  test(`accepted model mode ${mode} stays declared unverified origin`, async () => {
    const pack = { ...content(), generative_status: "accepted", generative_evidence_mode: mode,
      generative_analysis_characters: 25 };
    assert.deepEqual(await parse(source(pack)), pack);
  });
}

for (const status of ["withheld", "rejected"]) {
  test(`non-accepted status ${status} requires fixed error only`, async () => {
    const pack = { ...content(), generative_status: status, generative_error_code: "scope_denied" };
    assert.deepEqual(await parse(source(pack)), pack);
  });
}

for (const key of Object.keys(content())) {
  test(`missing exact field ${key}`, async () => {
    const pack = content(); delete pack[key];
    await assert.rejects(parse(source(pack)), /invalid_conversation_pack_/);
  });
  test(`duplicate or escaped duplicate key ${key} rejected before hashing`, async () => {
    const pack = content();
    const escaped = "\\u" + key.charCodeAt(0).toString(16).padStart(4, "0") + key.slice(1);
    let hashes = 0;
    const counting = { subtle: { digest() { hashes += 1; throw new Error("unused"); } } };
    for (const duplicate of [JSON.stringify(key), '"' + escaped + '"']) {
      const text = source(pack).slice(0, -1) + "," + duplicate + ":" + JSON.stringify(pack[key]) + "}";
      await assert.rejects(parseConversationPack(text, { crypto: counting }), /invalid_conversation_pack_json/);
    }
    assert.equal(hashes, 0);
  });
}

const invalidFields = [
  ["schema_version", "jarvis-conversation-pack-v2"], ["authority", "granted"],
  ["operator_authenticated", true], ["operator_authenticated", 0],
  ["runtime_capability_promoted", true], ["runtime_capability_promoted", "false"],
  ["origin", "authenticated_live_core"], ["content_included", 1], ["content_withheld", "false"],
  ["principal_ref", "principal:sha256:" + "A".repeat(64)],
  ["session_ref", ref("principal")], ["request_ref", "request:sha256:" + "a".repeat(63)],
  ["memory_record_ref", ref("memory-record") + "x"], ["intent", "Analysis"],
  ["intent", "analysis-brief"], ["intent", "a".repeat(65)], ["intent", ""],
  ["governance_decision", "approved"], ["generative_status", "completed"],
  ["generative_error_code", "PRIVATE URL https://secret.invalid"],
  ["generative_error_code", "a".repeat(81)], ["generative_evidence_mode", "fixture"],
  ["generative_analysis_characters", 1], ["request_character_count", 0],
  ["request_character_count", 16001], ["response_character_count", 0],
  ["response_character_count", 131073], ["response_character_count", true],
  ["generative_analysis_characters", -1], ["generative_analysis_characters", 8001],
  ["content_sha256", null], ["content_sha256", "A".repeat(64)],
  ["content_sha256", "b".repeat(64)], ["query", "different query"], ["response_text", "different response"],
];
for (const [index, [key, value]] of invalidFields.entries()) {
  test(`invalid field type/binding ${index} ${key}`, async () => {
    await assert.rejects(parse(source({ ...content(), [key]: value })), /invalid_conversation_pack_/);
  });
}

const inconsistent = [
  { content_withheld: true },
  { generative_status: "accepted" },
  { generative_status: "accepted", generative_evidence_mode: "fixture", generative_analysis_characters: 1,
    governance_decision: "block" },
  { generative_status: "accepted", generative_evidence_mode: "fixture", generative_analysis_characters: 1,
    generative_error_code: "scope_denied" },
  { generative_status: "accepted", generative_evidence_mode: "unknown", generative_analysis_characters: 1 },
  { generative_status: "withheld", generative_error_code: null },
  { generative_status: "rejected", generative_error_code: null },
  { generative_status: "disabled", generative_error_code: "scope_denied" },
];
for (const [index, change] of inconsistent.entries()) {
  test(`inconsistent status flags ${index}`, async () => {
    await assert.rejects(parse(source({ ...content(), ...change })), /invalid_conversation_pack_schema/);
  });
}

for (const text of ["", "null", "[]", "{}{}", "{} trailing", '{"a":1,}', '{"a":01}',
  '{"a":1.0}', '{"a":1e0}', '{"a":NaN}', '{"a":Infinity}', '{"a":1e999}', '{"a":undefined}',
  '{"a":[]}', '{"a":{}}', '{"a":"\\x00"}', '{"a":"unterminated}', '{"a":"x"',
  '{"a":"\u0000"}', "\ufeff" + source(), source().replace('"analysis"', '"anal\ud800ysis"')]) {
  test(`invalid JSON grammar ${text.slice(0, 24)}`, async () => {
    await assert.rejects(parse(text), /invalid_conversation_pack_/);
  });
}

for (const key of ["extra", "__proto__", "constructor", "actions", "grant", "url", "model", "account"]) {
  test(`unknown flat property ${key} never grants effects`, async () => {
    const raw = source().slice(0, -1) + "," + JSON.stringify(key) + ':"PRIVATE"}';
    await assert.rejects(parse(raw), /invalid_conversation_pack_schema/);
    assert.equal({}.PRIVATE, undefined);
  });
}

for (const stamp of ["0000-01-01T00:00:00Z", "2026-02-29T00:00:00Z", "2026-04-31T00:00:00Z",
  "2026-00-01T00:00:00Z", "2026-13-01T00:00:00Z", "2026-01-00T00:00:00Z",
  "2026-01-01T24:00:00Z", "2026-01-01T00:60:00Z", "2026-01-01T00:00:60Z",
  "2026-01-01T00:00:00.1234567Z", "2026-01-01T00:00:00.Z", "2026-01-01T00:00:00-00:00",
  "2026-01-01T00:00:00+03:00", "2026-01-01 00:00:00Z", "2026-01-01T00:00:00z", 1]) {
  test(`invalid UTC timestamp ${stamp}`, async () => {
    await assert.rejects(parse(source({ ...content(), timestamp: stamp })), /invalid_conversation_pack_timestamp/);
  });
}
for (const stamp of ["0001-01-01T00:00:00Z", "2000-02-29T23:59:59.1Z", "2024-02-29T12:12:12+00:00"]) {
  test(`valid precise calendar timestamp ${stamp}`, async () => {
    assert.equal((await parse(source({ ...content(), timestamp: stamp }))).timestamp, stamp);
  });
}

for (const text of ["a\u0000", "a\u007f", "a\u0085", "a\u200b", "a\u202e", "a\ufeff", "a\ud800", "a\udfff",
  "a\u2028", "a\u2029"]) {
  test(`invalid content Unicode ${JSON.stringify(text)}`, async () => {
    await assert.rejects(parse(source(content(text, "response"))), /invalid_conversation_pack_unicode/);
  });
}

test("counts use codepoints and exact UTF8 hash, not JS UTF16 length", async () => {
  const pack = content("😀".repeat(16000), "r".repeat(131072));
  assert.deepEqual(await parse(source(pack)), pack);
  await assert.rejects(parse(source({ ...pack, request_character_count: pack.query.length })),
    /invalid_conversation_pack_counts/);
});

test("analysis count cannot exceed declared or included final response count", async () => {
  const included = { ...content("q", "short"), generative_status: "accepted",
    generative_evidence_mode: "fixture", generative_analysis_characters: 6 };
  await assert.rejects(parse(source(included)), /invalid_conversation_pack_counts/);
  const omitted = { ...metadata(), generative_status: "accepted", generative_evidence_mode: "live",
    generative_analysis_characters: 2, response_character_count: 1 };
  await assert.rejects(parse(source(omitted)), /invalid_conversation_pack_counts/);
});

test("encoded byte limits are exact including whitespace and multibyte content", async () => {
  const base = source(metadata());
  const full = base + " ".repeat(CONVERSATION_PACK_MAX_BYTES - encoder.encode(base).byteLength);
  assert.deepEqual(await parse(full), metadata());
  await assert.rejects(parse(full + " "), /invalid_conversation_pack_size/);
  await assert.rejects(parse(source(content("q", "😀".repeat(65536)))), /invalid_conversation_pack_size/);
});

for (const unavailable of [null, {}, { subtle: {} }, { subtle: { digest: async () => { throw new Error("PRIVATE"); } } },
  { subtle: { digest: async () => new ArrayBuffer(31) } }, { subtle: { digest: async () => new Uint8Array(32) } }]) {
  test("included content fails closed for unavailable/invalid crypto", async () => {
    await assert.rejects(parseConversationPack(source(), { crypto: unavailable }),
      /conversation_pack_crypto_unavailable/);
  });
}

test("file actual UTF8 bytes checked before parsing and original names are never read", async () => {
  assert.deepEqual(await readConversationPackFile(fakeFile(), { crypto }), content());
  await assert.rejects(readConversationPackFile(fakeFile(source(), { size: 1 }), { crypto }),
    /invalid_conversation_pack_size/);
  const bomBytes = encoder.encode("\ufeff" + source()).byteLength;
  await assert.rejects(readConversationPackFile(fakeFile(source(), { size: bomBytes }), { crypto }),
    /invalid_conversation_pack_size/);
  let reads = 0;
  for (const size of [0, -1, 1.5, true, CONVERSATION_PACK_MAX_BYTES + 1]) {
    await assert.rejects(readConversationPackFile({ size, arrayBuffer() { reads += 1; } }, { crypto }),
      /invalid_conversation_pack_file/);
  }
  assert.equal(reads, 0);
  await assert.rejects(readConversationPackFile(fakeFile(source(), { arrayBuffer: async () => { throw new Error("PRIVATE"); } })),
    /invalid_conversation_pack_file/);
});

test("changing file size across asynchronous read is refused", async () => {
  const original = source();
  let reads = 0;
  const changing = { get size() { reads += 1; return encoder.encode(original).byteLength + (reads > 1 ? 1 : 0); },
    arrayBuffer: async () => encoder.encode(original).buffer };
  await assert.rejects(readConversationPackFile(changing, { crypto }), /invalid_conversation_pack_size/);
});

for (const malformed of [[0xff], [0xc0, 0xaf], [0xe0, 0x80, 0x80], [0xed, 0xa0, 0x80],
  [0xf1, 0x80, 0x80], [0xf4, 0x90, 0x80, 0x80]]) {
  test(`fatal UTF8 original bytes ${malformed.join("-")} cannot become replacement text`, async () => {
    // Truncated 3-byte prefix -> U+FFFD would preserve byte count and validate
    // the decoded content hash through a File.text-only import. Fatal decoding
    // of the original ArrayBuffer closes that ambiguity.
    const original = Buffer.from(source(content("\ufffd", "r")));
    const offset = original.indexOf(Buffer.from([0xef, 0xbf, 0xbd]));
    assert.notEqual(offset, -1);
    const raw = new Blob([original.subarray(0, offset), Uint8Array.from(malformed),
      original.subarray(offset + 3)]);
    await assert.rejects(readConversationPackFile(raw, { crypto }), /invalid_conversation_pack_encoding/);
  });
}

test("native file BOM is retained by decoder and refused as JSON, not silently stripped", async () => {
  await assert.rejects(readConversationPackFile(new Blob(["\ufeff", source()]), { crypto }),
    /invalid_conversation_pack_json/);
});

test("file proof requires ArrayBuffer and rejects text-only or disguised byte returns", async () => {
  await assert.rejects(readConversationPackFile({ size: 2, text: async () => "{}" }, { crypto }),
    /invalid_conversation_pack_file/);
  for (const result of ["{}", new Uint8Array(2), null, { byteLength: 2 }]) {
    await assert.rejects(readConversationPackFile({ size: 2, arrayBuffer: async () => result }, { crypto }),
      /invalid_conversation_pack_file/);
  }
});

test("controller first adoption, same context replacement and duplicates never accumulate", async () => {
  const seen = [];
  const controller = createConversationPackController({ crypto, onState: (state) => seen.push(state) });
  assert.equal(controller.getState().status, "empty");
  assert.equal((await controller.importFile(file())).status, "ready");
  assert.deepEqual(controller.getState().context, { principal_ref: ref("principal"), session_ref: ref("session") });
  const second = content("second", "replacement response");
  await controller.importFile(file(second));
  assert.equal(controller.getState().pack.response_text, second.response_text);
  await controller.importFile(file(second));
  assert.equal(controller.getState().pack.response_text, second.response_text);
  assert.equal(controller.getState().originLabel, CONVERSATION_PACK_ORIGIN_LABEL);
  assert.equal(Object.isFrozen(controller.getState()), true);
  assert.equal(Object.isFrozen(controller.getState().pack), true);
  assert.equal(Object.isFrozen(controller.getState().context), true);
  assert.throws(() => { seen[1].pack.query = "tampered"; }, TypeError);
});

for (const field of ["principal_ref", "session_ref"]) {
  test(`foreign ${field} never replaces context or shows imported content`, async () => {
    const controller = createConversationPackController({ crypto });
    await controller.importFile(file());
    const foreign = { ...content("foreign", "PRIVATE_FOREIGN_TEXT"), [field]: ref(field.replace("_ref", ""), "b") };
    const result = await controller.importFile(file(foreign));
    assert.equal(result.status, "error"); assert.equal(result.errorCode, "conversation_pack_context_mismatch");
    assert.equal(result.pack, null);
    assert.deepEqual(result.context, { principal_ref: ref("principal"), session_ref: ref("session") });
    controller.clear();
    assert.equal((await controller.importFile(file(foreign))).status, "ready");
  });
}

test("invalid replacement clears stale display but preserves context until explicit clear", async () => {
  const controller = createConversationPackController({ crypto });
  await controller.importFile(file());
  const result = await controller.importFile(fakeFile("{}"));
  assert.equal(result.status, "error"); assert.equal(result.pack, null);
  assert.notEqual(result.context, null);
  assert.equal(controller.clear().context, null);
});

test("clear during file.arrayBuffer stops hash and late commit", async () => {
  const gate = deferred();
  let hashes = 0;
  const controller = createConversationPackController({ crypto: { subtle: { digest() { hashes += 1; } } } });
  const pending = controller.importFile(fakeFile(source(), { arrayBuffer: () => gate.promise }));
  assert.equal(controller.getState().status, "loading");
  controller.clear(); gate.resolve(encoder.encode(source()).buffer); await pending;
  assert.equal(controller.getState().status, "empty"); assert.equal(hashes, 0);
});

test("clear or newer import during hash fences old result without touching current state", async () => {
  const gate = deferred();
  let hashes = 0;
  const delayedCrypto = { subtle: { digest: async (...args) => {
    hashes += 1;
    if (hashes === 1) await gate.promise;
    return webcrypto.subtle.digest(...args);
  } } };
  const controller = createConversationPackController({ crypto: delayedCrypto });
  const first = controller.importFile(file());
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(hashes, 1);
  const second = content("second", "current response");
  await controller.importFile(file(second));
  gate.resolve(); await first;
  assert.equal(controller.getState().pack.response_text, second.response_text);
  assert.equal(controller.getState().status, "ready");
});

test("newer file read beats an older invalid result and explicit clear beats hash", async () => {
  const gate = deferred();
  const controller = createConversationPackController({ crypto });
  const stale = controller.importFile(fakeFile("{}", { arrayBuffer: () => gate.promise }));
  await controller.importFile(file()); gate.resolve(encoder.encode("{}").buffer); await stale;
  assert.equal(controller.getState().status, "ready");
  const hashing = deferred();
  const cryptoGate = { subtle: { digest: async (...args) => { await hashing.promise; return webcrypto.subtle.digest(...args); } } };
  const other = createConversationPackController({ crypto: cryptoGate });
  const pending = other.importFile(file());
  await new Promise((resolve) => setImmediate(resolve));
  other.clear(); hashing.resolve(); await pending;
  assert.equal(other.getState().status, "empty"); assert.equal(other.getState().pack, null);
});

test("callback reentrancy cannot restart a cleared import and render errors cannot mutate state", async () => {
  let controller, reads = 0;
  controller = createConversationPackController({ crypto, onState: (state) => {
    if (state.status === "loading") controller.clear();
  } });
  const result = await controller.importFile(fakeFile(source(), { arrayBuffer() { reads += 1; } }));
  assert.equal(result.status, "empty"); assert.equal(reads, 0);
  const failing = createConversationPackController({ crypto, onState() { throw new Error("PRIVATE"); } });
  assert.equal((await failing.importFile(file())).status, "ready");
});

test("minimal DOM fixture uses only literal textContent and overwrites stale nodes", async () => {
  const node = () => ({ textContent: "OLD", set innerHTML(_value) { throw new Error("HTML_EXECUTION_FORBIDDEN"); } });
  const nodes = { status: node(), query: node(), response: node(), metadata: node() };
  const malicious = content('<script>globalThis.fetch("https://evil.invalid")</script>',
    '<img src=x onerror="grantAdmin()"> **Markdown** [link](https://evil.invalid)');
  const controller = createConversationPackController({ crypto });
  renderConversationPack(await controller.importFile(file(malicious)), nodes);
  assert.equal(nodes.query.textContent, malicious.query);
  assert.equal(nodes.response.textContent, malicious.response_text);
  assert.match(nodes.status.textContent, /pacote offline — origem não autenticada/);
  assert.doesNotMatch(nodes.status.textContent, /autenticada por|origem canônica autenticada/);
  renderConversationPack(await controller.importFile(fakeFile("{}")), nodes);
  assert.equal(nodes.query.textContent, ""); assert.equal(nodes.response.textContent, "");
  assert.match(nodes.status.textContent, /conteúdo anterior removido/);
  renderConversationPack(await controller.importFile(file(metadata(true))), nodes);
  assert.equal(nodes.query.textContent, ""); assert.equal(nodes.response.textContent, "");
  assert.match(nodes.metadata.textContent, /omitido/);
});

test("offline import never reads network, storage, file names or invokes action APIs", async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = () => { throw new Error("NETWORK_FORBIDDEN"); };
  try {
    const controller = createConversationPackController({ crypto });
    assert.equal((await controller.importFile(fakeFile())).status, "ready");
    assert.equal(Object.hasOwn(controller, "execute"), false);
    assert.equal(Object.hasOwn(controller, "grant"), false);
    assert.equal(Object.hasOwn(controller, "upload"), false);
    assert.equal(controller.clear().status, "empty");
  } finally { globalThis.fetch = oldFetch; }
});
