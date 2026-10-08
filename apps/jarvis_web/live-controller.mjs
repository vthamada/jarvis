// Local Core analysis client. Pairing is not human identity or an execution grant.
const ticketPattern = /^web-request-[a-f0-9]{32}$/;
const sessionPattern = /^session:\/\/web-live\/[a-f0-9]{32}$/;
const hex = /^[a-f0-9]{64}$/;
const nativeSchema = "jarvis-local-analysis-v1", generativeSchema = "jarvis-local-analysis-v2";
const generativeErrors = new Set(["invalid_context", "invalid_composition", "input_sensitive", "cancelled",
  "invalid_clock", "timed_out", "invalid_result", "binding_mismatch", "inference_failed", "output_limit",
  "invalid_candidate", "invalid_citation", "candidate_limit", "output_sensitive", "render_limit",
  "context_changed", "result_changed", "inference_unavailable", "scope_denied", "reviewed_source_invalid"]);
const serviceErrors = new Set(["analysis_invalid", "analysis_busy", "analysis_ticket_refused",
  "analysis_closed", "analysis_outcome_unknown", "analysis_expired"]);
const httpErrors = new Set(["auth_unavailable", "pairing_unavailable", "pairing_rate_limited",
  "pairing_refused", "session_refused", "csrf_refused", "analysis_invalid", "analysis_busy",
  "analysis_ticket_refused", "analysis_closed", "request_invalid", "request_too_large",
  "origin_refused", "client_refused", "service_unavailable", "asset_unavailable", "server_busy", "generative_unavailable"]);
const clientErrors = new Set(["invalid_response", "network_error", "session_expired", "foreign_session",
  "invalid_query", "invalid_secret", "wait_stopped", "wait_timeout", "not_paired", "request_busy", "consent_required"]);
const fail = (code) => { throw new Error(code); };
const exact = (value, fields) => value !== null && typeof value === "object" && !Array.isArray(value) &&
  Object.keys(value).length === fields.length && fields.every((field) => Object.hasOwn(value, field));
const text = (value, max) => {
  if (typeof value !== "string" || !value.trim()) return false;
  let count = 0;
  for (const char of value) {
    if (/[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u.test(char) && !"\r\n\t".includes(char)) return false;
    if (++count > max) return false;
  }
  return true;
};
function utc(value) {
  if (typeof value !== "string") return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(?:Z|\+00:00)$/.exec(value);
  if (!match) return false;
  const [year, month, day, hour, minute, second] = match.slice(1).map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  return year > 0 && month > 0 && month <= 12 && day > 0 &&
    day <= [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1] &&
    hour <= 23 && minute <= 59 && second <= 59;
}
function session(value) {
  if (!exact(value, ["schema_version", "authenticated", "session_ref", "csrf_token",
    "expires_in_seconds", "last_ticket"]) || value.schema_version !== "jarvis-local-session-v1" ||
    value.authenticated !== true || typeof value.session_ref !== "string" || !sessionPattern.test(value.session_ref) ||
    typeof value.csrf_token !== "string" || !hex.test(value.csrf_token) ||
    !Number.isInteger(value.expires_in_seconds) || value.expires_in_seconds < 1 || value.expires_in_seconds > 900 ||
    !(value.last_ticket === null || (typeof value.last_ticket === "string" && ticketPattern.test(value.last_ticket)))) fail("invalid_response");
  return value;
}
function envelope(value, ticket, query = null, schema = nativeSchema) {
  if (!exact(value, ["schema_version", "status", "ticket", "error_code", "result"]) ||
    ![nativeSchema, generativeSchema].includes(value.schema_version) ||
    (schema !== null && value.schema_version !== schema) || typeof value.ticket !== "string" || !ticketPattern.test(value.ticket) ||
    (ticket !== null && value.ticket !== ticket) ||
    !["issued", "running", "completed", "failed"].includes(value.status)) fail("invalid_response");
  if (value.status === "failed") {
    if (!["analysis_outcome_unknown", "analysis_expired"].includes(value.error_code) || value.result !== null) fail("invalid_response");
  } else if (value.error_code !== null) fail("invalid_response");
  if (value.status !== "completed") {
    if (value.result !== null) fail("invalid_response");
    return value;
  }
  const result = value.result;
  const generative = value.schema_version === generativeSchema;
  const fields = ["query", "response_text", "intent", "governance_decision", "memory_record_ref",
    "timestamp", "evidence_mode", "generative_status", "authority"];
  if (generative) fields.push("generative_error_code", "generative_evidence_mode", "generative_analysis_characters");
  if (!exact(result, fields) ||
    !text(result.query, 4000) || !text(result.response_text, 131072) ||
    (query !== null && result.query !== query) ||
    typeof result.intent !== "string" || !/^[a-z][a-z_]{0,63}$/.test(result.intent) ||
    !["allow", "block", "defer_for_validation"].includes(result.governance_decision) ||
    typeof result.memory_record_ref !== "string" || !/^mem-record-[a-f0-9]{8}$/.test(result.memory_record_ref) || !utc(result.timestamp) ||
    result.evidence_mode !== "core_local" || (!generative && result.generative_status !== "disabled") ||
    result.authority !== "none") fail("invalid_response");
  if (generative) {
    const count = result.generative_analysis_characters;
    if (!Number.isInteger(count) || !["accepted", "withheld", "rejected"].includes(result.generative_status)) fail("invalid_response");
    if (result.generative_status === "accepted") {
      if (result.governance_decision !== "allow" || count < 1 || count > 4000 || result.generative_error_code !== null ||
        !["live", "injected_transport"].includes(result.generative_evidence_mode)) fail("invalid_response");
    } else if (count !== 0 || result.generative_evidence_mode !== null || !generativeErrors.has(result.generative_error_code) ||
      (result.generative_status === "withheld" && !["scope_denied", "reviewed_source_invalid"].includes(result.generative_error_code))) fail("invalid_response");
  }
  return value;
}

// Reject duplicate keys, including escaped duplicates, before native JSON decoding.
function decodeJson(source) {
  let offset = 0;
  const space = () => { while (/[ \t\r\n]/.test(source[offset] ?? "!")) offset++; };
  const string = () => {
    const start = offset++;
    let escaped = false;
    while (offset < source.length) {
      const char = source[offset++];
      if (!escaped && char === '"') return JSON.parse(source.slice(start, offset));
      escaped = !escaped && char === "\\";
    }
    fail("invalid_response");
  };
  const value = (depth = 0) => {
    if (depth > 3) fail("invalid_response");
    space();
    if (source[offset] === '"') { string(); return; }
    if (source[offset] === "{") {
      offset++; space(); const seen = new Set();
      if (source[offset] === "}") { offset++; return; }
      while (true) {
        if (source[offset] !== '"') fail("invalid_response");
        const key = string(); if (seen.has(key)) fail("invalid_response"); seen.add(key);
        if (seen.size > 12) fail("invalid_response");
        space(); if (source[offset++] !== ":") fail("invalid_response"); value(depth + 1); space();
        if (source[offset] === "}") { offset++; return; }
        if (source[offset++] !== ",") fail("invalid_response"); space();
      }
    }
    const match = /^(?:true|false|null|-?(?:0|[1-9]\d*))/.exec(source.slice(offset));
    if (!match) fail("invalid_response"); offset += match[0].length;
  };
  try { value(); space(); if (offset !== source.length) fail("invalid_response"); return JSON.parse(source); }
  catch { fail("invalid_response"); }
}
async function responseJson(response) {
  if (response.redirected || response.type === "opaque" || response.type === "opaqueredirect") fail("invalid_response");
  if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(response.headers?.get("content-type") ?? "")) fail("invalid_response");
  const maxBytes = 2097152; // Includes escaped surrogate pairs for the bounded canonical final.
  const length = response.headers?.get("content-length");
  if (length !== null && length !== undefined && (!/^\d+$/.test(length) || Number(length) > maxBytes)) fail("invalid_response");
  let source;
  if (response.body?.getReader) {
    const reader = response.body.getReader(), chunks = []; let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        size += value.byteLength;
        if (size > maxBytes) fail("invalid_response"); chunks.push(value);
      }
      const bytes = new Uint8Array(size); let start = 0;
      for (const chunk of chunks) { bytes.set(chunk, start); start += chunk.byteLength; }
      if (length !== null && length !== undefined && Number(length) !== size) fail("invalid_response");
      try { source = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes); }
      catch { fail("invalid_response"); }
    } finally { await reader.cancel().catch(() => {}); }
  } else {
    source = await response.text(); // Injected transport seam; native fetch uses bounded reader above.
    if (new TextEncoder().encode(source).byteLength > maxBytes) fail("invalid_response");
  }
  return decodeJson(source);
}

export const LIVE_SESSION_LABEL = "Sessão local pareada — não identidade humana";
export function createLiveController({ transport = globalThis.fetch, onState = () => {}, now = () => Date.now(),
  pollIntervalMs = 500, waitTimeoutMs = 30000 } = {}) {
  if (typeof transport !== "function" || typeof onState !== "function" || typeof now !== "function" ||
    !Number.isFinite(pollIntervalMs) || pollIntervalMs < 0 || !Number.isFinite(waitTimeoutMs) ||
    waitTimeoutMs <= 0 || waitTimeoutMs > 30000) throw new TypeError("invalid_live_options");
  let generation = 0, auth = null, expires = 0, abort = null, expectedQuery = null, expectedSchema = null, expiryTimer = null;
  let state = { status: "disconnected", sessionRef: null, ticket: null, result: null, errorCode: null };
  const getState = () => Object.freeze({ ...state,
    result: state.result ? Object.freeze({ ...state.result }) : null });
  const publish = () => { try { onState(getState()); } catch { /* No authority in rendering. */ } };
  const invalidate = (status = "disconnected", errorCode = null) => {
    generation++; abort?.abort(); abort = null; clearTimeout(expiryTimer); expiryTimer = null;
    auth = null; expires = 0; expectedQuery = null; expectedSchema = null;
    state = { status, sessionRef: null, ticket: null, result: null, errorCode }; publish();
  };
  const paired = () => {
    if (!auth) fail("not_paired");
    if (now() >= expires) { invalidate("disconnected", "session_expired"); fail("session_expired"); }
  };
  const request = async (path, method, body, signal, csrf = auth?.csrf_token) => {
    const headers = { "X-Jarvis-Client": "local-web-v1" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (csrf && path !== "/api/pair" && path !== "/api/session") headers["X-Jarvis-CSRF"] = csrf;
    const response = await transport(path, { method, headers, mode: "same-origin", credentials: "same-origin",
      cache: "no-store", redirect: "error", signal, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    const value = await responseJson(response);
    if (!response.ok) {
      if (!exact(value, ["error_code"]) || !httpErrors.has(value.error_code)) fail("invalid_response");
      fail(value.error_code);
    }
    return { value, status: response.status };
  };
  const operation = async (status, action) => {
    const version = ++generation; abort?.abort(); abort = new AbortController();
    const signal = abort.signal;
    state = { ...state, status, result: null, errorCode: null }; publish();
    const timer = setTimeout(() => {
      if (version === generation) { abort?.abort(); generation++;
        state = { ...state, status: state.ticket ? "stopped" : "error", result: null, errorCode: "wait_timeout" }; publish(); }
    }, waitTimeoutMs);
    const current = () => { if (version !== generation || signal.aborted) fail("wait_stopped"); };
    let rejectCancelled;
    const cancelled = new Promise((_resolve, reject) => { rejectCancelled = () => reject(new Error("wait_stopped")); });
    signal.addEventListener("abort", rejectCancelled, { once: true });
    try { current(); await Promise.race([action(signal, current), cancelled]); current(); publish(); }
    catch (error) {
      if (version !== generation) return getState();
      const code = serviceErrors.has(error?.message) || httpErrors.has(error?.message) ||
        clientErrors.has(error?.message) ? error.message : "network_error";
      if (["session_refused", "csrf_refused"].includes(code)) {
        invalidate("disconnected", code); return getState();
      }
      state = { ...state, status: state.ticket ? "stopped" : "error", result: null, errorCode: code }; publish();
    } finally { clearTimeout(timer); signal.removeEventListener("abort", rejectCancelled); }
    return getState();
  };
  const adopt = (value) => {
    let next;
    try { next = session(value); }
    catch { invalidate("disconnected", "invalid_response"); fail("invalid_response"); }
    if (auth && next.session_ref !== auth.session_ref) { invalidate("disconnected", "foreign_session"); fail("foreign_session"); }
    auth = { ...next }; expires = now() + next.expires_in_seconds * 1000;
    clearTimeout(expiryTimer);
    expiryTimer = setTimeout(() => invalidate("disconnected", "session_expired"), next.expires_in_seconds * 1000);
    state = { ...state, sessionRef: next.session_ref };
  };
  const initialize = () => operation("connecting", async (signal, current) => {
    const { value, status } = await request("/api/session", "GET", undefined, signal); current();
    if (status !== 200) fail("invalid_response"); adopt(value);
    if (state.ticket !== auth.last_ticket) { expectedQuery = null; expectedSchema = null; }
    state = { ...state, status: "ready", ticket: auth.last_ticket };
  });
  const pair = (secret) => {
    if (auth || busy()) return getState();
    if (typeof secret !== "string" || !hex.test(secret)) {
      state = { ...state, status: "error", result: null, errorCode: "invalid_secret" }; publish(); return getState();
    }
    return operation("connecting", async (signal, current) => {
      const { value, status } = await request("/api/pair", "POST", { secret }, signal); current();
      if (status !== 200) fail("invalid_response"); adopt(value);
      state = { ...state, status: "ready", ticket: auth.last_ticket };
    });
  };
  const poll = async (signal, current) => {
    while (true) {
      paired(); current();
      const { value, status } = await request("/api/results/" + state.ticket, "GET", undefined, signal); current(); paired();
      if (status !== 200) fail("invalid_response");
      const next = envelope(value, state.ticket, expectedQuery, expectedSchema);
      expectedSchema = next.schema_version; // Reload adopts once; the same ticket may not switch versions later.
      if (next.status === "completed" || next.status === "failed") {
        state = { ...state, status: next.status, result: next.result, errorCode: next.error_code }; return;
      }
      if (next.status === "issued") {
        state = { ...state, status: "stopped", result: null, errorCode: "analysis_outcome_unknown" }; return;
      }
      await new Promise((resolve) => {
        const timer = setTimeout(done, pollIntervalMs);
        function done() { clearTimeout(timer); signal.removeEventListener("abort", done); resolve(); }
        signal.addEventListener("abort", done, { once: true });
      }); current();
    }
  };
  const busy = () => ["connecting", "submitting", "waiting"].includes(state.status);
  const submitRequest = (query, generative = false) => {
    if (busy()) return getState();
    try { paired(); if (!text(query, 4000)) fail("invalid_query"); }
    catch (error) { state = { ...state, result: null, errorCode: error.message }; publish(); return getState(); }
    expectedQuery = query; expectedSchema = generative ? generativeSchema : nativeSchema;
    state = { ...state, ticket: null };
    return operation("submitting", async (signal, current) => {
      const issued = await request(generative ? "/api/generative-tickets" : "/api/tickets", "POST", generative ? { consent: true } : {}, signal); current(); paired();
      const ticket = envelope(issued.value, null, null, expectedSchema);
      if (issued.status !== 201 || ticket.status !== "issued") fail("invalid_response");
      state = { ...state, ticket: ticket.ticket }; publish(); current();
      const started = await request(generative ? "/api/generative-analysis" : "/api/analysis", "POST",
        { ticket: ticket.ticket, query, ...(generative ? { consent: true } : {}) }, signal); current(); paired();
      const accepted = envelope(started.value, ticket.ticket, null, expectedSchema);
      if (started.status !== 202 || !["running", "failed"].includes(accepted.status)) fail("invalid_response");
      if (accepted.status === "failed") {
        state = { ...state, status: "failed", errorCode: accepted.error_code, result: null }; return;
      }
      state = { ...state, status: "waiting" }; publish(); current(); await poll(signal, current);
    });
  };
  const submit = (query) => submitRequest(query);
  const submitGenerative = (query, options = { consent: false }) => {
    if (busy()) return getState();
    if (!exact(options, ["consent"]) || options.consent !== true) {
      state = { ...state, result: null, errorCode: "consent_required" }; publish(); return getState();
    }
    return submitRequest(query, true);
  };
  const recover = () => {
    if (busy()) return getState();
    try { paired(); if (!state.ticket) fail("analysis_ticket_refused"); }
    catch (error) { state = { ...state, result: null, errorCode: error.message }; publish(); return getState(); }
    return operation("waiting", async (signal, current) => {
      const fresh = await request("/api/session", "GET", undefined, signal); current();
      if (fresh.status !== 200) fail("invalid_response"); adopt(fresh.value); await poll(signal, current);
    });
  };
  const stopWaiting = () => {
    generation++; abort?.abort(); abort = null;
    state = { ...state, status: auth ? (state.ticket ? "stopped" : "ready") : "disconnected",
      result: null, errorCode: "wait_stopped" }; publish(); return getState();
  };
  const disconnect = async () => {
    const csrf = auth?.csrf_token; invalidate();
    if (!csrf) return getState();
    const version = generation, signal = new AbortController(); abort = signal;
    const timer = setTimeout(() => signal.abort(), waitTimeoutMs);
    try {
      const { value, status } = await request("/api/disconnect", "POST", {}, signal.signal, csrf);
      if (status !== 200 || !exact(value, ["status"]) || value.status !== "disconnected") fail("invalid_response");
    } catch {
      if (version === generation) { state = { ...state, errorCode: "network_error" }; publish(); }
    } finally { clearTimeout(timer); }
    return getState();
  };
  const pageHide = () => { invalidate(); return getState(); };
  return Object.freeze({ initialize, pair, submit, submitGenerative, recover, stopWaiting, disconnect, pageHide, getState });
}
