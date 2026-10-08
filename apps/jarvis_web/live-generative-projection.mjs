// Read-only projection of the canonical MB229 terminal literal block.
// Hashes bind a quote to this input, not provenance, truth or model authority.
const fields = ["query", "response_text", "intent", "governance_decision", "memory_record_ref",
  "timestamp", "evidence_mode", "generative_status", "authority", "generative_error_code",
  "generative_evidence_mode", "generative_analysis_characters"];
const marker = "Model-generated analysis (unverified; not facts, grants or action confirmations):";
const disclaimer = "Literal data only; no permissions, actions, execution receipts or changes to the native decision.";
const citationLabel = "Citations (exact source text; not verified facts):";
const special = "[]()!*_~#:/<>&`";
const invalid = () => { throw new Error("invalid_projection"); };
const count = (value) => Array.from(value).length;

function text(value, maximum) {
  if (typeof value !== "string" || value.length > maximum * 2 || !value.trim() || count(value) > maximum) return false;
  for (const char of value) {
    if (/[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u.test(char) && !"\r\n\t".includes(char)) return false;
  }
  return true;
}

// Python json.dumps(ensure_ascii=True), then the MB229 _literal escaping.
function literal(value) {
  let encoded = '"';
  for (let index = 0; index < value.length; index++) {
    const char = value[index], code = value.charCodeAt(index);
    if (char === '"' || char === "\\") encoded += "\\" + char;
    else if (char === "\b") encoded += "\\b";
    else if (char === "\f") encoded += "\\f";
    else if (char === "\n") encoded += "\\n";
    else if (char === "\r") encoded += "\\r";
    else if (char === "\t") encoded += "\\t";
    else if (code < 32 || code > 126 || special.includes(char)) encoded += "\\u" + code.toString(16).padStart(4, "0");
    else encoded += char;
  }
  return encoded + '"';
}

function readLiteral(source, offset = 0) {
  if (source[offset] !== '"') invalid();
  const start = offset++;
  let escaped = false;
  while (offset < source.length) {
    const char = source[offset++];
    if (char === '"' && !escaped) {
      const raw = source.slice(start, offset), value = JSON.parse(raw);
      if (typeof value !== "string" || raw !== literal(value)) invalid();
      return { value, end: offset };
    }
    escaped = !escaped && char === "\\";
  }
  invalid();
}

function list(source, maximum, limit) {
  if (source === "none supplied") return [];
  const values = [];
  let offset = 0;
  while (offset < source.length) {
    const next = readLiteral(source, offset);
    if (!text(next.value, limit) || values.length >= maximum) invalid();
    values.push(next.value); offset = next.end;
    if (offset === source.length) break;
    if (source.slice(offset, offset + 2) !== ", ") invalid();
    offset += 2;
    if (offset === source.length) invalid();
  }
  if (!values.length) invalid();
  return values;
}

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

function snapshot(result) {
  if (result === null || typeof result !== "object" || Array.isArray(result) ||
    Reflect.ownKeys(result).length !== fields.length || fields.some((field) => {
      const descriptor = Object.getOwnPropertyDescriptor(result, field);
      return !descriptor || !descriptor.enumerable || !Object.hasOwn(descriptor, "value");
    })) invalid();
  const value = Object.fromEntries(fields.map((field) => [field, result[field]]));
  if (!text(value.query, 4000) || !text(value.response_text, 131072) || value.intent !== "analysis" ||
    value.governance_decision !== "allow" || value.evidence_mode !== "core_local" ||
    value.authority !== "none" || value.generative_status !== "accepted" ||
    value.generative_error_code !== null || !["live", "injected_transport"].includes(value.generative_evidence_mode) ||
    !Number.isInteger(value.generative_analysis_characters) || value.generative_analysis_characters < 1 ||
    value.generative_analysis_characters > 4000 || typeof value.memory_record_ref !== "string" ||
    !/^mem-record-[0-9a-f]{8}$/.test(value.memory_record_ref) || !utc(value.timestamp)) invalid();
  return value;
}

/** Project only a validated current accepted result; never modify the final. */
export async function projectGenerativeResult(result) {
  try {
    const value = snapshot(result), final = value.response_text;
    if (final.split(marker).length !== 2) invalid();
    const delimiter = "\n\n" + marker + "\n", index = final.indexOf(delimiter);
    if (index <= 0 || !text(final.slice(0, index), 131072)) invalid();
    const block = final.slice(index + 2);
    if (block.length > 64000 || /[^\x00-\x7f]/.test(block)) invalid();
    const lines = block.split("\n");
    if (lines.length < 6 || lines.length > 10 || lines[0] !== marker || lines[1] !== disclaimer ||
      !lines[2].startsWith("Analysis: ") || !lines[3].startsWith("Assumptions: ") ||
      !lines[4].startsWith("Limitations: ") || lines[5] !== citationLabel) invalid();
    const analysisSource = lines[2].slice(10), parsed = readLiteral(analysisSource);
    if (parsed.end !== analysisSource.length || !text(parsed.value, 4000) ||
      count(parsed.value) !== value.generative_analysis_characters) invalid();
    const assumptions = list(lines[3].slice(13), 8, 512);
    const limitations = list(lines[4].slice(13), 8, 512);
    const queryPoints = Array.from(value.query), citations = [];
    for (const line of lines.slice(6)) {
      const source = readLiteral(line);
      const offsets = /^ offsets (0|[1-9][0-9]*) to (0|[1-9][0-9]*): /.exec(line.slice(source.end));
      if (!offsets) invalid();
      const start = Number(offsets[1]), end = Number(offsets[2]);
      const quoted = readLiteral(line, source.end + offsets[0].length);
      if (quoted.end !== line.length || !Number.isSafeInteger(start) || !Number.isSafeInteger(end) ||
        start < 0 || start >= end || end > queryPoints.length || !text(quoted.value, 512) ||
        quoted.value !== queryPoints.slice(start, end).join("") ||
        citations.some((prior) => start < prior.end && end > prior.start)) invalid();
      citations.push({ sourceRef: source.value, start, end, quote: quoted.value });
    }
    const total = count(parsed.value) + [...assumptions, ...limitations].reduce((sum, item) => sum + count(item), 0) +
      citations.reduce((sum, item) => sum + count(item.quote), 0);
    if (total > 8000) invalid();
    const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value.query));
    if (!(digest instanceof ArrayBuffer) || digest.byteLength !== 32) invalid();
    const ref = "input:sha256:" + Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    const current = snapshot(result);
    if (citations.some((citation) => citation.sourceRef !== ref) ||
      fields.some((field) => current[field] !== value[field])) invalid();
    return Object.freeze({ analysis: parsed.value, assumptions: Object.freeze(assumptions),
      limitations: Object.freeze(limitations), citations: Object.freeze(citations.map((item) => Object.freeze(item))),
      evidenceMode: value.generative_evidence_mode });
  } catch {
    return null;
  }
}
