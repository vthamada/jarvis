import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createTranscriptReview, handleTranscriptPageHide, parseTranscriptSource,
  validateTranscriptText } from "../transcript-review.mjs";

const encoder = new TextEncoder();
const doc = (text = "  Olá, JARVIS!\r\n Áudio 😀  ") => ({ review_required: true,
  language: "Portuguese", audio_duration_seconds: 12.5,
  segments: [{ start_seconds: 0, end_seconds: 8, timestamps_estimated: false, text }] });
const bytes = (document = doc()) => encoder.encode(JSON.stringify(document));
const hash = (value) => createHash("sha256").update(value).digest("hex");
const file = (data = bytes()) => ({ size: data.byteLength,
  arrayBuffer: async () => data.slice().buffer,
  get name() { throw new Error("secret file name must never be inspected"); } });
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
function rig() {
  let time = 0;
  const review = createTranscriptReview({ clock: () => time });
  return { review, time: (value) => { time = value; },
    async ready(data = bytes()) { review.setConsent(true); return review.importFile(file(data)); } };
}

test("exact UTF8 source and reviewed text export with real cryptographic hashes", async () => {
  const { review, ready } = rig();
  const original = encoder.encode(` \r\n${JSON.stringify(doc(), null, 2)}\r\n `);
  const imported = await ready(original);
  assert.equal(imported.text, doc().segments[0].text);
  assert.equal(imported.source_sha256, hash(original));
  const edited = "  Texto revisado 😀\r\n\t com espaços  ";
  const view = review.revise(edited);
  const output = JSON.parse(await review.exportPackage(view));
  assert.deepEqual(Object.keys(output).sort(), ["schema_version", "authority", "source_origin",
    "document_utf8_b64", "source_sha256", "reviewed_text", "reviewed_sha256", "review_revision"].sort());
  assert.equal(output.schema_version, "jarvis-transcript-handoff-v1");
  assert.equal(output.authority, "none"); assert.equal(output.source_origin, "unverified");
  assert.equal(output.reviewed_text, edited); assert.equal(output.reviewed_sha256, hash(edited));
  assert.equal(output.review_revision, 2);
  assert.equal(output.document_utf8_b64, Buffer.from(original).toString("base64"));
  assert.deepEqual(Buffer.from(output.document_utf8_b64, "base64"), Buffer.from(original));
  assert.equal(output.source_sha256, hash(original));
  assert.equal(review.getSnapshot().state, "exported");
  assert.throws(() => review.getReview(), /transcript_review_unavailable/);
  await assert.rejects(review.exportPackage(view), /transcript_review_unavailable/);
});

test("no consent means no file IO, revision or export", async () => {
  const { review } = rig();
  let read = false;
  await assert.rejects(review.importFile({ get size() { read = true; return 1; } }),
    /transcript_review_consent_required/);
  assert.equal(read, false);
  assert.throws(() => review.revise("hello"), /transcript_review_consent_required/);
  await assert.rejects(review.exportPackage(), /transcript_review_consent_required/);
  assert.throws(() => review.setConsent("true"), /invalid_transcript_consent/);
});

test("segment text joined exactly with newline including overlapping legal ranges", () => {
  const document = doc("first\r\n ");
  document.segments.push({ start_seconds: 3, end_seconds: 4, timestamps_estimated: true,
    text: " second😀 " });
  assert.equal(parseTranscriptSource(bytes(document)).text, "first\r\n \n second😀 ");
});

for (const text of ["", " ", "\u0000", "hello\u0007", "hello\u007f", "a\u0085", "a\u200b",
  "a\u202e", "a\ufeff", "a\ud800", "a\udfff", "a".repeat(4001)]) {
  test(`refuse invalid Unicode text ${JSON.stringify(text).slice(0, 22)}`, () => {
    assert.throws(() => validateTranscriptText(text), /invalid_transcript_text/);
  });
}

test("Unicode limit is codepoints, not UTF16 code units or UTF8 bytes", () => {
  assert.equal(validateTranscriptText("😀".repeat(4000)), "😀".repeat(4000));
  assert.throws(() => validateTranscriptText("😀".repeat(4001)), /invalid_transcript_text/);
  const document = doc("a".repeat(3999));
  document.segments.push({ start_seconds: 0, end_seconds: 1, timestamps_estimated: false, text: "b" });
  assert.throws(() => parseTranscriptSource(bytes(document)), /invalid_transcript_text/);
});

const invalidDocuments = [
  null, [], true, { ...doc(), extra: true }, { ...doc(), review_required: false },
  { ...doc(), review_required: 1 }, { ...doc(), language: "pt-BR" },
  { ...doc(), audio_duration_seconds: 0 }, { ...doc(), audio_duration_seconds: -1 },
  { ...doc(), audio_duration_seconds: 900.01 }, { ...doc(), audio_duration_seconds: true },
  { ...doc(), segments: [] }, { ...doc(), segments: {} },
  { ...doc(), segments: new Array(1001).fill(doc().segments[0]) },
  { ...doc(), segments: [{ ...doc().segments[0], extra: "x" }] },
  { ...doc(), segments: [{ ...doc().segments[0], timestamps_estimated: 0 }] },
  { ...doc(), segments: [{ ...doc().segments[0], start_seconds: -0.1 }] },
  { ...doc(), segments: [{ ...doc().segments[0], start_seconds: true }] },
  { ...doc(), segments: [{ ...doc().segments[0], start_seconds: 10, end_seconds: 8 }] },
  { ...doc(), segments: [{ ...doc().segments[0], end_seconds: 13 }] },
  { ...doc(), segments: [doc().segments[0], { ...doc().segments[0], start_seconds: 2 },
    { ...doc().segments[0], start_seconds: 1 }] },
];
for (const [index, document] of invalidDocuments.entries()) {
  test(`strict document refusal ${index}`, () => {
    assert.throws(() => parseTranscriptSource(bytes(document)), /invalid_transcript_/);
  });
}

const invalidJson = [
  '{"review_required":true,"review_required":true}',
  '{"review_required":true,"review_\\u0072equired":true}',
  '{"segments":[{"text":"a","text":"b"}]}',
  '[1,]', '{"a":1,}', '{"a":01}', '{"a":+1}', '{"a":.1}', '{"a":NaN}',
  '{"a":Infinity}', '{"a":1e999}', '{"a":undefined}', '{"a":"\u0000"}',
  '{"a":"\\x00"}', '{"a":"unterminated}', '{}{}', '{} trailing',
  `${"[".repeat(14)}0${"]".repeat(14)}`,
];
for (const [index, source] of invalidJson.entries()) {
  test(`strict JSON refusal ${index}`, () => {
    assert.throws(() => parseTranscriptSource(encoder.encode(source)), /invalid_transcript_json/);
  });
}

test("UTF8 fatal decode, BOM and bounded raw bytes", () => {
  for (const data of [new Uint8Array([0xc0, 0xaf]), new Uint8Array([0xed, 0xa0, 0x80]),
    new Uint8Array([0xef, 0xbb, 0xbf, ...bytes()])]) {
    assert.throws(() => parseTranscriptSource(data), /invalid_transcript_encoding/);
  }
  for (const data of [new Uint8Array(), new Uint8Array(32769), "{}", bytes().buffer]) {
    assert.throws(() => parseTranscriptSource(data), /invalid_transcript_source/);
  }
});

for (const supplied of [{}, { size: 0 }, { size: -1 }, { size: 32769 }, { size: true },
  { size: 1, arrayBuffer: async () => "x" }, { size: 1, arrayBuffer: async () => new ArrayBuffer(2) }]) {
  test(`file shape bound ${Object.keys(supplied).join("-")}:${supplied.size}`, async () => {
    const { review } = rig(); review.setConsent(true);
    await assert.rejects(review.importFile(supplied), /invalid_transcript_file/);
    assert.equal(review.getSnapshot().state, "error");
  });
}

test("arbitrary reader errors never echo private details even with valid-looking prefix", async () => {
  const { review } = rig(); review.setConsent(true);
  await assert.rejects(review.importFile({ size: 4, arrayBuffer() {
    throw new Error("invalid_transcript_PRIVATE_CONTENT_PATH"); } }), /^Error: transcript_import_failed$/);
  assert.ok(!JSON.stringify(review.getSnapshot()).includes("PRIVATE"));
});

for (const patch of [{ generation: -1 }, { generation: true }, { revision: 0 },
  { revision: true }, { text: "different" }, { text: "Olá, JARVIS!" }]) {
  test(`exact export binding ${Object.keys(patch)[0]}:${String(Object.values(patch)[0]).slice(0, 10)}`, async () => {
    const { review, ready } = rig(); const view = await ready();
    await assert.rejects(review.exportPackage({ ...view, ...patch }), /transcript_review_stale/);
    assert.equal(review.getSnapshot().state, "reviewed");
    assert.equal(JSON.parse(await review.exportPackage(view)).reviewed_text, view.text);
  });
}

test("same-text edit advances revision and invalidates former review", async () => {
  const { review, ready } = rig(); const old = await ready();
  const edited = review.revise(old.text);
  assert.equal(edited.revision, 2);
  await assert.rejects(review.exportPackage(old), /transcript_review_stale/);
  assert.equal(JSON.parse(await review.exportPackage(edited)).review_revision, 2);
});

for (const action of ["cancel", "reset", "dispose", "revoke", "bfcache", "pagehide"]) {
  test(`${action} erases reviewed data and refuses replay`, async () => {
    const { review, ready } = rig(); const view = await ready();
    if (action === "revoke") review.setConsent(false);
    else if (action === "bfcache") handleTranscriptPageHide(review, { persisted: true });
    else if (action === "pagehide") handleTranscriptPageHide(review);
    else review[action]();
    assert.throws(() => review.getReview(), /transcript_review_/);
    await assert.rejects(review.exportPackage(view), /transcript_review_/);
    if (action !== "cancel") assert.equal(review.getSnapshot().review_consent, false);
  });
}

test("local deadline exact boundary erases source/text and is not an exported authorization", async () => {
  const { review, ready, time } = rig(); const view = await ready();
  time(119999); assert.equal(review.getReview().text, view.text);
  time(120000); await assert.rejects(review.exportPackage(view), /transcript_review_unavailable/);
  assert.equal(review.getSnapshot().state, "expired");
  assert.equal(review.getSnapshot().revision, null);
});

for (const value of [NaN, Infinity, -1, "1", true]) {
  test(`invalid/backwards clock ${String(value)}`, async () => {
    const { review, ready, time } = rig(); await ready(); time(value);
    assert.throws(() => review.getReview(), /invalid_transcript_clock/);
    assert.equal(review.getSnapshot().state, "error");
    assert.equal(review.getSnapshot().revision, null);
  });
}

test("deadline includes file read and stale imports cannot replace latest review", async () => {
  const first = rig(); first.review.setConsent(true); const wait = deferred();
  const loading = first.review.importFile({ size: bytes().length, arrayBuffer: () => wait.promise });
  first.time(120000); wait.resolve(bytes().buffer);
  await assert.rejects(loading, /transcript_deadline_exceeded/);
  assert.equal(first.review.getSnapshot().state, "expired");
  const second = rig(); second.review.setConsent(true); const oldWait = deferred();
  const old = second.review.importFile({ size: bytes().length, arrayBuffer: () => oldWait.promise });
  const latest = await second.review.importFile(file(bytes(doc("new"))));
  oldWait.resolve(bytes().buffer); await assert.rejects(old, /transcript_review_stale/);
  assert.equal(second.review.getReview().text, latest.text);
});

for (const action of ["cancel", "reset", "dispose", "revoke"]) {
  test(`${action} during file read cannot revive consent or content`, async () => {
    const { review } = rig(); review.setConsent(true); const wait = deferred();
    const pending = review.importFile({ size: bytes().length, arrayBuffer: () => wait.promise });
    if (action === "revoke") review.setConsent(false); else review[action]();
    wait.resolve(bytes().buffer); await assert.rejects(pending, /transcript_review_/);
    assert.equal(review.getSnapshot().revision, null);
  });
}

async function withDigestGate(run) {
  const original = globalThis.crypto.subtle.digest;
  const gate = deferred();
  let called = 0;
  globalThis.crypto.subtle.digest = async function (...args) {
    called += 1; await gate.promise; return original.apply(this, args);
  };
  try { await run(gate, () => called); }
  finally { globalThis.crypto.subtle.digest = original; }
}

test("pending source digest invalidated by cancel before hash completion", async () => {
  await withDigestGate(async (gate, calls) => {
    const { review } = rig(); review.setConsent(true);
    const pending = review.importFile(file());
    await Promise.resolve(); assert.equal(calls(), 1); review.cancel(); gate.resolve();
    await assert.rejects(pending, /transcript_review_stale/);
    assert.equal(review.getSnapshot().state, "cancelled");
  });
});

for (const action of ["cancel", "reset", "dispose", "revoke", "revise", "expire"]) {
  test(`${action} during reviewed digest prevents package return`, async () => {
    const { review, ready, time } = rig(); const view = await ready();
    await withDigestGate(async (gate, calls) => {
      const pending = review.exportPackage(view);
      assert.equal(calls(), 1);
      if (action === "revoke") review.setConsent(false);
      else if (action === "revise") review.revise("edited during crypto");
      else if (action === "expire") time(120000);
      else review[action]();
      gate.resolve(); await assert.rejects(pending, /transcript_/);
      assert.equal(review.getSnapshot().state, action === "revise" ? "reviewed" :
        action === "revoke" ? "revoked" : action === "expire" ? "expired" :
          action === "cancel" ? "cancelled" : action === "reset" ? "idle" : "disposed");
    });
  });
}

test("parallel export calls consume only one matching package", async () => {
  const { review, ready } = rig(); const view = await ready();
  const first = review.exportPackage(view);
  await assert.rejects(review.exportPackage(view), /transcript_review_unavailable/);
  assert.equal(JSON.parse(await first).reviewed_text, view.text);
});

test("content-free snapshots and observer events; observers cannot leak source or identity", async () => {
  const { review, ready } = rig(); const seen = [];
  const unsubscribe = review.subscribe((snapshot) => { seen.push(snapshot); throw new Error("private"); });
  const view = await ready(bytes(doc("unique secret content")));
  const snapshot = review.getSnapshot(); snapshot.events[0].name = "mutated";
  assert.notEqual(review.getSnapshot().events[0].name, "mutated");
  await review.exportPackage(view); unsubscribe();
  const metadata = JSON.stringify(seen);
  for (const forbidden of ["unique secret content", "source_sha256", "document_utf8_b64",
    "reviewed_text", "principal", "session", "signature", "email"]) {
    assert.ok(!metadata.includes(forbidden));
  }
  assert.equal(review.getSnapshot().network_used, false);
  assert.equal(review.getSnapshot().speaker_identification, false);
  for (let index = 0; index < 300; index += 1) review.reset();
  assert.equal(review.getSnapshot().events.length, 256);
});

test("observer revocation during export linearization prevents returned package", async () => {
  const { review, ready } = rig(); const view = await ready();
  review.subscribe((snapshot) => { if (snapshot.state === "exported") review.setConsent(false); });
  await assert.rejects(review.exportPackage(view), /transcript_review_stale/);
  assert.equal(review.getSnapshot().state, "revoked");
});

test("parser returns owned bytes and review views cannot mutate internal source/segments", async () => {
  const source = bytes(); const parsed = parseTranscriptSource(source);
  source.fill(0); assert.notEqual(parsed.bytes[0], 0);
  const { review, ready } = rig(); const view = await ready();
  view.text = "tampered"; view.segments[0].end_seconds = 900;
  assert.notEqual(review.getReview().text, view.text);
  assert.equal(review.getReview().segments[0].end_seconds, 8);
});

for (const padding of [0, 1, 2]) {
  test(`standard base64 preserves original bytes with padding case ${padding}`, async () => {
    const { review, ready } = rig();
    const source = encoder.encode(JSON.stringify(doc()) + " ".repeat(padding));
    const view = await ready(source);
    const output = JSON.parse(await review.exportPackage(view));
    assert.equal(output.document_utf8_b64, Buffer.from(source).toString("base64"));
  });
}

test("revocation followed by regrant never revives pending file read", async () => {
  const { review } = rig(); review.setConsent(true); const wait = deferred();
  const pending = review.importFile({ size: bytes().length, arrayBuffer: () => wait.promise });
  review.setConsent(false); review.setConsent(true); wait.resolve(bytes().buffer);
  await assert.rejects(pending, /transcript_review_stale/);
  assert.equal(review.getSnapshot().state, "revoked");
  assert.equal(review.getSnapshot().revision, null);
});

test("fresh import during pending export replaces old exact source and prevents old package", async () => {
  const { review, ready } = rig(); const view = await ready();
  await withDigestGate(async (gate, calls) => {
    const pendingExport = review.exportPackage(view);
    const nextSource = bytes(doc("fresh source"));
    const pendingImport = review.importFile(file(nextSource));
    await Promise.resolve(); assert.equal(calls(), 2); gate.resolve();
    await assert.rejects(pendingExport, /transcript_review_stale/);
    assert.equal((await pendingImport).text, "fresh source");
  });
  assert.equal(review.getReview().text, "fresh source");
});

test("crypto errors discard content and never echo arbitrary engine details", async () => {
  const original = globalThis.crypto.subtle.digest;
  const first = rig(); first.review.setConsent(true);
  globalThis.crypto.subtle.digest = async () => { throw new Error("private engine error"); };
  try {
    await assert.rejects(first.review.importFile(file()), /transcript_crypto_unavailable/);
    assert.equal(first.review.getSnapshot().revision, null);
    assert.ok(!JSON.stringify(first.review.getSnapshot()).includes("private"));
  } finally { globalThis.crypto.subtle.digest = original; }
  const second = rig(); const view = await second.ready();
  globalThis.crypto.subtle.digest = async () => { throw new Error("private engine error"); };
  try {
    await assert.rejects(second.review.exportPackage(view), /transcript_export_failed/);
    assert.equal(second.review.getSnapshot().revision, null);
    assert.ok(!JSON.stringify(second.review.getSnapshot()).includes("private"));
  } finally { globalThis.crypto.subtle.digest = original; }
});

test("observer revocation during import prevents file IO", async () => {
  const { review } = rig(); review.setConsent(true); let read = false;
  review.subscribe((snapshot) => { if (snapshot.state === "loading") review.setConsent(false); });
  await assert.rejects(review.importFile({ get size() { read = true; return 1; } }),
    /transcript_review_stale/);
  assert.equal(read, false);
});
