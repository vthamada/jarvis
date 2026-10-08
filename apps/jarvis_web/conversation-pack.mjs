// Manual offline display only. SHA256 checks consistency, never origin or authority.
export const CONVERSATION_PACK_ORIGIN_LABEL = "pacote offline — origem não autenticada";
export const CONVERSATION_PACK_MAX_BYTES = 262144;
const schema = "jarvis-conversation-pack-v1";
const encoder = new TextEncoder();
const hashPattern = /^[a-f0-9]{64}$/;
const codePattern = /^[a-z][a-z0-9_]{0,79}$/;
const statuses = new Set(["disabled", "accepted", "withheld", "rejected"]);
const modes = new Set(["fixture", "injected_transport", "live"]);
const decisions = new Set(["allow", "block", "defer_for_validation"]);
const keys = ["schema_version", "authority", "operator_authenticated",
  "runtime_capability_promoted", "origin", "content_included", "content_withheld",
  "principal_ref", "session_ref", "request_ref", "memory_record_ref", "timestamp", "intent",
  "governance_decision", "generative_status", "generative_error_code", "generative_evidence_mode",
  "generative_analysis_characters", "request_character_count", "response_character_count",
  "content_sha256"];
const errorCodes = new Set(["invalid_conversation_pack_json", "invalid_conversation_pack_schema",
  "invalid_conversation_pack_unicode", "invalid_conversation_pack_size",
  "invalid_conversation_pack_timestamp", "invalid_conversation_pack_counts",
  "invalid_conversation_pack_hash", "conversation_pack_crypto_unavailable",
  "invalid_conversation_pack_file", "invalid_conversation_pack_encoding",
  "conversation_pack_context_mismatch", "conversation_pack_stale"]);
const refuse = (code) => { throw new Error(code); };
const current = (isCurrent) => { if (!isCurrent()) refuse("conversation_pack_stale"); };

function unicode(text) {
  for (const character of text) {
    const point = character.codePointAt(0);
    if (point >= 0xd800 && point <= 0xdfff) refuse("invalid_conversation_pack_unicode");
  }
}

// This wire contract is flat and contains only strings, booleans, null and
// integer number literals. Parsing keys before assigning catches escaped duplicates.
function strictJson(source) {
  let offset = 0;
  const whitespace = () => { while (/[ \t\n\r]/.test(source[offset] ?? "!")) offset += 1; };
  const string = () => {
    if (source[offset] !== '"') refuse("invalid_conversation_pack_json");
    const start = offset++;
    let escaped = false;
    while (offset < source.length) {
      const character = source[offset++];
      if (!escaped && character === '"') {
        try { return JSON.parse(source.slice(start, offset)); }
        catch { refuse("invalid_conversation_pack_json"); }
      }
      if (!escaped && character === "\\") escaped = true;
      else escaped = false;
    }
    refuse("invalid_conversation_pack_json");
  };
  const primitive = () => {
    whitespace();
    if (source[offset] === '"') return string();
    for (const [literal, value] of [["true", true], ["false", false], ["null", null]]) {
      if (source.startsWith(literal, offset)) { offset += literal.length; return value; }
    }
    const match = /^-?(?:0|[1-9]\d*)/.exec(source.slice(offset));
    if (!match) refuse("invalid_conversation_pack_json");
    offset += match[0].length;
    const number = Number(match[0]);
    if (!Number.isSafeInteger(number)) refuse("invalid_conversation_pack_json");
    return number;
  };
  whitespace();
  if (source[offset++] !== "{") refuse("invalid_conversation_pack_json");
  whitespace();
  const result = Object.create(null);
  const seen = new Set();
  if (source[offset] === "}") offset += 1;
  else {
    while (offset < source.length) {
      const key = string();
      if (seen.has(key)) refuse("invalid_conversation_pack_json");
      seen.add(key);
      if (seen.size > keys.length + 2) refuse("invalid_conversation_pack_schema");
      whitespace();
      if (source[offset++] !== ":") refuse("invalid_conversation_pack_json");
      result[key] = primitive();
      whitespace();
      if (source[offset] === "}") { offset += 1; break; }
      if (source[offset++] !== ",") refuse("invalid_conversation_pack_json");
      whitespace();
    }
  }
  whitespace();
  if (offset !== source.length || source[offset - 1]?.trim() === "{") {
    refuse("invalid_conversation_pack_json");
  }
  // Also catches a final key/value with no object closing delimiter.
  if (!source.trimEnd().endsWith("}")) refuse("invalid_conversation_pack_json");
  return result;
}

function timestamp(value) {
  if (typeof value !== "string") return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(?:Z|\+00:00)$/.exec(value);
  if (!match) return false;
  const [year, month, day, hour, minute, second] = match.slice(1).map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year >= 1 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1] &&
    hour <= 23 && minute <= 59 && second <= 59;
}

const integer = (value, lower, upper) => Number.isSafeInteger(value) && value >= lower && value <= upper;
const reference = (value, prefix) => typeof value === "string" &&
  value.startsWith(prefix + ":sha256:") && hashPattern.test(value.slice(prefix.length + 8));
const copy = (value) => Object.freeze({ ...value });

function textCount(value, expected) {
  if (typeof value !== "string" || !value.trim()) refuse("invalid_conversation_pack_counts");
  let count = 0;
  for (const character of value) {
    if (/[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u.test(character) && !"\r\n\t".includes(character)) {
      refuse("invalid_conversation_pack_unicode");
    }
    count += 1;
  }
  if (count !== expected) refuse("invalid_conversation_pack_counts");
}

async function digest(query, response, crypto) {
  try {
    if (!crypto?.subtle || typeof crypto.subtle.digest !== "function") throw new Error();
    const bytes = encoder.encode(schema + "\0" + query + "\0" + response);
    const result = await crypto.subtle.digest("SHA-256", bytes);
    if (!(result instanceof ArrayBuffer) || result.byteLength !== 32) throw new Error();
    return [...new Uint8Array(result)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  } catch { refuse("conversation_pack_crypto_unavailable"); }
}

export async function parseConversationPack(source, { crypto = globalThis.crypto,
  isCurrent = () => true } = {}) {
  current(isCurrent);
  if (typeof source !== "string" || source.length === 0 || source.length > CONVERSATION_PACK_MAX_BYTES) {
    refuse("invalid_conversation_pack_size");
  }
  unicode(source);
  const size = encoder.encode(source).byteLength;
  if (size === 0 || size > CONVERSATION_PACK_MAX_BYTES) refuse("invalid_conversation_pack_size");
  const value = strictJson(source);
  const expected = value.content_included === true ? [...keys, "query", "response_text"] : keys;
  if (Object.keys(value).length !== expected.length || !expected.every((key) => Object.hasOwn(value, key)) ||
      value.schema_version !== schema || value.authority !== "none" ||
      value.operator_authenticated !== false || value.runtime_capability_promoted !== false ||
      value.origin !== "canonical_core_export" || typeof value.content_included !== "boolean" ||
      typeof value.content_withheld !== "boolean" ||
      (value.content_included && value.content_withheld) ||
      !reference(value.principal_ref, "principal") || !reference(value.session_ref, "session") ||
      !reference(value.request_ref, "request") || !reference(value.memory_record_ref, "memory-record") ||
      typeof value.intent !== "string" || !/^[a-z][a-z_]{0,63}$/.test(value.intent) ||
      !decisions.has(value.governance_decision) || !statuses.has(value.generative_status) ||
      !(value.generative_error_code === null || (typeof value.generative_error_code === "string" &&
        codePattern.test(value.generative_error_code)))) refuse("invalid_conversation_pack_schema");
  if (!timestamp(value.timestamp)) refuse("invalid_conversation_pack_timestamp");
  if (!integer(value.request_character_count, 1, 16000) ||
      !integer(value.response_character_count, 1, 131072) ||
      !integer(value.generative_analysis_characters, 0, 8000) ||
      value.generative_analysis_characters > value.response_character_count) {
    refuse("invalid_conversation_pack_counts");
  }
  if (value.generative_status === "accepted") {
    if (value.governance_decision !== "allow" || !modes.has(value.generative_evidence_mode) ||
        value.generative_analysis_characters === 0 ||
        value.generative_error_code !== null) refuse("invalid_conversation_pack_schema");
  } else if (value.generative_evidence_mode !== null || value.generative_analysis_characters !== 0 ||
      (value.generative_status === "disabled" ? value.generative_error_code !== null :
        value.generative_error_code === null)) refuse("invalid_conversation_pack_schema");
  if (value.content_included) {
    textCount(value.query, value.request_character_count);
    textCount(value.response_text, value.response_character_count);
    if (typeof value.content_sha256 !== "string" || !hashPattern.test(value.content_sha256)) {
      refuse("invalid_conversation_pack_hash");
    }
    current(isCurrent);
    const actual = await digest(value.query, value.response_text, crypto);
    current(isCurrent);
    if (actual !== value.content_sha256) {
      refuse("invalid_conversation_pack_hash");
    }
  } else if (value.content_sha256 !== null) refuse("invalid_conversation_pack_hash");
  current(isCurrent);
  return copy(value);
}

export async function readConversationPackFile(file, options = {}) {
  let size, read, source, buffer;
  try {
    current(options.isCurrent ?? (() => true));
    size = file?.size;
    if (!integer(size, 1, CONVERSATION_PACK_MAX_BYTES) || typeof file.arrayBuffer !== "function") {
      refuse("invalid_conversation_pack_file");
    }
    read = file.arrayBuffer.bind(file);
    buffer = await read();
    current(options.isCurrent ?? (() => true));
    if (!(buffer instanceof ArrayBuffer)) {
      refuse("invalid_conversation_pack_file");
    }
    if (file.size !== size || buffer.byteLength !== size) {
      refuse("invalid_conversation_pack_size");
    }
    try {
      source = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(new Uint8Array(buffer));
    } catch { refuse("invalid_conversation_pack_encoding"); }
  } catch (error) {
    if (errorCodes.has(error?.message)) throw new Error(error.message);
    refuse("invalid_conversation_pack_file");
  }
  return parseConversationPack(source, options);
}

export function createConversationPackController({ onState = () => {}, crypto = globalThis.crypto } = {}) {
  if (typeof onState !== "function") refuse("invalid_conversation_pack_schema");
  let generation = 0;
  let state = { status: "empty", errorCode: null, pack: null, context: null };
  const getState = () => copy({ ...state, pack: state.pack ? copy(state.pack) : null,
    context: state.context ? copy(state.context) : null, originLabel: CONVERSATION_PACK_ORIGIN_LABEL });
  const publish = () => { try { onState(getState()); } catch { /* Rendering cannot grant authority. */ } };
  const clear = () => {
    generation += 1;
    state = { status: "empty", errorCode: null, pack: null, context: null };
    publish();
    return getState();
  };
  const importFile = async (file) => {
    const version = ++generation;
    state = { ...state, status: "loading", errorCode: null, pack: null };
    publish();
    if (version !== generation) return getState();
    try {
      const pack = await readConversationPackFile(file, { crypto, isCurrent: () => version === generation });
      if (version !== generation) return getState();
      if (state.context && (state.context.principal_ref !== pack.principal_ref ||
          state.context.session_ref !== pack.session_ref)) refuse("conversation_pack_context_mismatch");
      state = { status: "ready", errorCode: null, pack,
        context: { principal_ref: pack.principal_ref, session_ref: pack.session_ref } };
    } catch (error) {
      if (version !== generation) return getState();
      state = { ...state, status: "error", pack: null,
        errorCode: errorCodes.has(error?.message) ? error.message : "invalid_conversation_pack_file" };
    }
    publish();
    return getState();
  };
  return Object.freeze({ importFile, clear, getState });
}

export function renderConversationPack(state, { status, query, response, metadata } = {}) {
  if (status) status.textContent = CONVERSATION_PACK_ORIGIN_LABEL + " · " +
    ({ empty: "nenhum pacote", loading: "validando pacote", ready: "pacote validado localmente",
      error: "pacote recusado — conteúdo anterior removido" }[state?.status] ?? "pacote indisponível");
  if (query) query.textContent = "";
  if (response) response.textContent = "";
  if (metadata) metadata.textContent = "";
  if (state?.status !== "ready" || !state.pack) return;
  const pack = state.pack;
  if (metadata) metadata.textContent = `decisão declarada: ${pack.governance_decision}; ` +
    `análise: ${pack.generative_status}; conteúdo: ${pack.content_included ? "incluído" : "omitido"}`;
  if (!pack.content_included) return;
  if (query) query.textContent = pack.query;
  if (response) response.textContent = pack.response_text;
}
