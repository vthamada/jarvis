// Independent local review. No microphone, persistence, upload, identity or Core authority.
const MAX_SOURCE_BYTES = 32768;
const MAX_TEXT_POINTS = 4000;
const MAX_PACKAGE_BYTES = 131072;
const MAX_REVISION = 2147483647;
const REVIEW_WINDOW_MS = 120000;
const encoder = new TextEncoder();
const invalidCategory = /[\p{Cc}\p{Cf}\p{Cs}]/u;
const failure = (code) => new Error(code);
const refuse = (code) => { throw failure(code); };
const importErrors = new Set(["invalid_transcript_source", "invalid_transcript_encoding",
  "invalid_transcript_json", "invalid_transcript_document", "invalid_transcript_duration",
  "invalid_transcript_segment", "invalid_transcript_time", "invalid_transcript_text",
  "invalid_transcript_file", "transcript_crypto_unavailable"]);

export function validateTranscriptText(text) {
  if (typeof text !== "string" || !text.trim() || [...text].length > MAX_TEXT_POINTS ||
      [...text].some((char) => invalidCategory.test(char) && !"\n\r\t".includes(char))) {
    refuse("invalid_transcript_text");
  }
  return text;
}

// JSON.parse alone silently accepts duplicate keys. Bound depth and reject duplicates first.
function strictJson(source) {
  let offset = 0;
  const whitespace = () => { while (/[ \t\n\r]/.test(source[offset] ?? "!")) offset += 1; };
  const string = () => {
    const start = offset++;
    let escaped = false;
    while (offset < source.length) {
      const char = source[offset++];
      if (!escaped && char === '"') {
        try { return JSON.parse(source.slice(start, offset)); }
        catch { refuse("invalid_transcript_json"); }
      }
      if (!escaped && char === "\\") escaped = true;
      else escaped = false;
    }
    refuse("invalid_transcript_json");
  };
  const value = (depth) => {
    if (depth > 12) refuse("invalid_transcript_json");
    whitespace();
    const char = source[offset];
    if (char === '"') return string();
    if (char === "{" || char === "[") {
      const object = char === "{";
      const result = object ? Object.create(null) : [];
      const seen = new Set();
      const closing = object ? "}" : "]";
      offset += 1; whitespace();
      if (source[offset] === closing) { offset += 1; return result; }
      while (offset < source.length) {
        if (object) {
          if (source[offset] !== '"') refuse("invalid_transcript_json");
          const key = string();
          if (seen.has(key)) refuse("invalid_transcript_json");
          seen.add(key); whitespace();
          if (source[offset++] !== ":") refuse("invalid_transcript_json");
          result[key] = value(depth + 1);
        } else result.push(value(depth + 1));
        whitespace();
        if (source[offset] === closing) { offset += 1; return result; }
        if (source[offset++] !== ",") refuse("invalid_transcript_json");
        whitespace();
      }
      refuse("invalid_transcript_json");
    }
    for (const [literal, result] of [["true", true], ["false", false], ["null", null]]) {
      if (source.startsWith(literal, offset)) { offset += literal.length; return result; }
    }
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(source.slice(offset));
    if (!match) refuse("invalid_transcript_json");
    offset += match[0].length;
    const number = Number(match[0]);
    if (!Number.isFinite(number)) refuse("invalid_transcript_json");
    return number;
  };
  const result = value(0);
  whitespace();
  if (offset !== source.length) refuse("invalid_transcript_json");
  return result;
}

const exactKeys = (value, keys) => value !== null && typeof value === "object" &&
  !Array.isArray(value) && Object.keys(value).length === keys.length &&
  keys.every((key) => Object.hasOwn(value, key));
const number = (value) => typeof value === "number" && Number.isFinite(value);

export function parseTranscriptSource(input) {
  if (!(input instanceof Uint8Array) || input.byteLength === 0 ||
      input.byteLength > MAX_SOURCE_BYTES) refuse("invalid_transcript_source");
  const bytes = new Uint8Array(input);
  if (bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    refuse("invalid_transcript_encoding");
  }
  let source;
  try { source = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { refuse("invalid_transcript_encoding"); }
  const document = strictJson(source);
  if (!exactKeys(document, ["review_required", "language", "audio_duration_seconds", "segments"]) ||
      document.review_required !== true || document.language !== "Portuguese" ||
      !Array.isArray(document.segments) || document.segments.length < 1 ||
      document.segments.length > 1000) refuse("invalid_transcript_document");
  const duration = document.audio_duration_seconds;
  if (!number(duration) || duration <= 0 || duration > 900) refuse("invalid_transcript_duration");
  let previousStart = 0;
  const texts = [];
  const segments = [];
  for (const segment of document.segments) {
    if (!exactKeys(segment, ["start_seconds", "end_seconds", "timestamps_estimated", "text"]) ||
        typeof segment.timestamps_estimated !== "boolean") refuse("invalid_transcript_segment");
    const start = segment.start_seconds;
    const end = segment.end_seconds;
    if (!number(start) || !number(end) || start < previousStart || start > end || end > duration) {
      refuse("invalid_transcript_time");
    }
    texts.push(validateTranscriptText(segment.text));
    previousStart = start;
    segments.push({ start_seconds: start, end_seconds: end,
      timestamps_estimated: segment.timestamps_estimated });
  }
  const text = validateTranscriptText(texts.join("\n"));
  return { bytes, text, segments, audio_duration_seconds: duration, language: "Portuguese" };
}

function standardBase64(bytes) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let output = "";
  for (let index = 0; index < bytes.length; index += 3) {
    const a = bytes[index], b = bytes[index + 1], c = bytes[index + 2];
    output += alphabet[a >> 2] + alphabet[((a & 3) << 4) | ((b ?? 0) >> 4)] +
      (b === undefined ? "=" : alphabet[((b & 15) << 2) | ((c ?? 0) >> 6)]) +
      (c === undefined ? "=" : alphabet[c & 63]);
  }
  return output;
}

async function sha256(bytes) {
  try {
    const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
    return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  } catch { refuse("transcript_crypto_unavailable"); }
}

export function createTranscriptReview({ clock = () => performance.now() } = {}) {
  let state = "idle", generation = 0, consent = false, disposed = false;
  let current = null, error = null, deadline = null, lastTime = -Infinity;
  const events = [];
  const listeners = new Set();
  const record = (name) => {
    events.push({ name, generation, state, authority: "none" });
    if (events.length > 256) events.splice(0, events.length - 256);
  };
  const invalidate = (next, code = null) => {
    generation += 1; current = null; deadline = null; state = next; error = code;
  };
  const now = () => {
    let time;
    try { time = clock(); } catch { time = NaN; }
    if (typeof time !== "number" || !Number.isFinite(time) || time < lastTime) {
      invalidate("error", "invalid_transcript_clock");
      record("transcript_review_refused");
      refuse("invalid_transcript_clock");
    }
    lastTime = time;
    return time;
  };
  const expire = () => {
    if (deadline !== null && now() >= deadline) {
      invalidate("expired", "transcript_deadline_exceeded");
      record("transcript_review_expired");
    }
  };
  const snapshot = () => {
    if (!disposed) { try { expire(); } catch { /* Fixed error is visible without content. */ } }
    return { mode: "local_transcript_review", state, generation, review_consent: consent,
      revision: current?.revision ?? null, error_code: error, authority: "none",
      source_origin: "unverified", hardware_audio: false, speaker_identification: false,
      network_used: false, events: events.map((event) => ({ ...event })) };
  };
  const emit = () => {
    for (const listener of listeners) {
      try { listener(snapshot()); } catch { /* Observers cannot alter this operation's outcome. */ }
    }
  };
  const requireActive = (states) => {
    if (disposed) refuse("transcript_review_disposed");
    expire();
    if (!consent) refuse("transcript_review_consent_required");
    if (!states.includes(state)) refuse("transcript_review_unavailable");
  };
  const fence = (ticket, revision = null, text = null) => {
    requireActive(revision === null ? ["loading"] : ["exporting"]);
    if (generation !== ticket || (revision !== null &&
        (current?.revision !== revision || current?.text !== text))) {
      refuse("transcript_review_stale");
    }
  };
  const api = {
    getSnapshot: snapshot,
    getReview() {
      requireActive(["reviewed"]);
      return { text: current.text, generation, revision: current.revision,
        source_sha256: current.source_sha256,
        segments: current.segments.map((segment) => ({ ...segment })),
        audio_duration_seconds: current.audio_duration_seconds, language: "Portuguese" };
    },
    subscribe(listener) {
      if (typeof listener !== "function") refuse("invalid_transcript_listener");
      if (disposed) return () => {};
      listeners.add(listener);
      try { listener(snapshot()); } catch { /* Content-free observer only. */ }
      return () => listeners.delete(listener);
    },
    setConsent(value) {
      if (disposed) refuse("transcript_review_disposed");
      if (typeof value !== "boolean") refuse("invalid_transcript_consent");
      consent = value;
      if (!value) invalidate("revoked");
      record(value ? "transcript_consent_granted" : "transcript_consent_revoked");
      emit(); return value;
    },
    async importFile(file) {
      if (disposed) refuse("transcript_review_disposed");
      if (!consent) refuse("transcript_review_consent_required");
      invalidate("loading");
      const ticket = generation;
      record("transcript_import_started");
      try {
        deadline = now() + REVIEW_WINDOW_MS;
        emit();
        fence(ticket);
        const size = file?.size;
        if (!Number.isInteger(size) || size < 1 || size > MAX_SOURCE_BYTES ||
            typeof file?.arrayBuffer !== "function") refuse("invalid_transcript_file");
        const buffer = await file.arrayBuffer();
        fence(ticket);
        if (!(buffer instanceof ArrayBuffer) || buffer.byteLength !== size) {
          refuse("invalid_transcript_file");
        }
        const parsed = parseTranscriptSource(new Uint8Array(buffer));
        const hash = await sha256(parsed.bytes);
        fence(ticket);
        current = { ...parsed, source_sha256: hash, revision: 1 };
        state = "reviewed"; record("transcript_review_required"); emit();
        if (generation !== ticket || state !== "reviewed") refuse("transcript_review_stale");
        return api.getReview();
      } catch (cause) {
        if (generation === ticket && state === "loading") {
          const code = cause instanceof Error && importErrors.has(cause.message)
            ? cause.message : "transcript_import_failed";
          invalidate("error", code); record("transcript_import_refused"); emit();
        }
        // Never echo arbitrary file/reader/clock failures or source contents.
        refuse(error ?? "transcript_review_stale");
      }
    },
    revise(text) {
      requireActive(["reviewed", "exporting"]);
      validateTranscriptText(text);
      if (current.revision >= MAX_REVISION) refuse("transcript_revision_limit_exceeded");
      current.text = text; current.revision += 1; state = "reviewed";
      record("transcript_candidate_edited"); emit();
      return api.getReview();
    },
    async exportPackage({ generation: ticket, revision, text } = {}) {
      requireActive(["reviewed"]);
      if (!Number.isInteger(ticket) || ticket !== generation || !Number.isInteger(revision) ||
          revision !== current.revision || text !== current.text) refuse("transcript_review_stale");
      state = "exporting"; record("transcript_export_started"); emit();
      try {
        fence(ticket, revision, text);
        const reviewedHash = await sha256(encoder.encode(text));
        fence(ticket, revision, text);
        const output = JSON.stringify({ schema_version: "jarvis-transcript-handoff-v1",
          authority: "none", source_origin: "unverified",
          document_utf8_b64: standardBase64(current.bytes), source_sha256: current.source_sha256,
          reviewed_text: text, reviewed_sha256: reviewedHash, review_revision: revision });
        if (encoder.encode(output).length > MAX_PACKAGE_BYTES) refuse("transcript_package_limit_exceeded");
        invalidate("exported");
        const exportedGeneration = generation;
        record("transcript_package_exported"); emit();
        if (generation !== exportedGeneration || state !== "exported") refuse("transcript_review_stale");
        return output;
      } catch (cause) {
        if (generation === ticket && state === "exporting") {
          invalidate("error", "transcript_export_failed"); record("transcript_export_refused"); emit();
        }
        refuse(error ?? "transcript_review_stale");
      }
    },
    cancel() {
      if (disposed) return false;
      invalidate("cancelled"); record("transcript_review_cancelled"); emit(); return true;
    },
    reset() {
      if (disposed) return false;
      consent = false; invalidate("idle"); record("transcript_review_reset"); emit(); return true;
    },
    dispose() {
      if (disposed) return;
      consent = false; invalidate("disposed"); disposed = true;
      record("transcript_review_disposed"); emit(); listeners.clear();
    },
  };
  return api;
}

export function handleTranscriptPageHide(controller, { persisted = false } = {}) {
  if (persisted) controller.reset();
  else controller.dispose();
}
