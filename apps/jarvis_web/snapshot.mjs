export const SNAPSHOT_VERSION = "jarvis-surface-snapshot-v1";
export const MAX_SNAPSHOT_BYTES = 65536;

function reject() { throw new Error("Snapshot inválido ou fora dos limites permitidos."); }
function exactObject(value, keys) {
  if (!value || typeof value !== "object" || Array.isArray(value)) reject();
  const actual = Object.keys(value);
  if (actual.length !== keys.length || keys.some((key) => !Object.hasOwn(value, key))) reject();
}
function text(value, max = 200) {
  if (typeof value !== "string" || !value.trim() || Array.from(value).length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(value)) reject();
}
function ref(value) { text(value, 200); }
function nullableRef(value) { if (value !== null) ref(value); }
function list(value, validate) {
  if (!Array.isArray(value) || value.length > 100) reject();
  value.forEach(validate);
}
function timestamp(value) {
  text(value, 64);
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(Z|[+-]\d{2}:\d{2})$/u.exec(value);
  if (!match || !Number.isFinite(Date.parse(value))) reject();
  const [, year, month, day, hour, minute, second, offset] = match;
  const maxDay = new Date(Date.UTC(Number(year), Number(month), 0)).getUTCDate();
  if (Number(month) < 1 || Number(month) > 12 || Number(day) < 1 || Number(day) > maxDay ||
      Number(hour) > 23 || Number(minute) > 59 || Number(second) > 59) reject();
  if (offset !== "Z" && (Number(offset.slice(1, 3)) > 23 || Number(offset.slice(4)) > 59)) reject();
}

// A structurally valid snapshot is still an unverified, offline file. Its
// principal and authority fields never replace the current client identity.
export function validateSnapshot(value) {
  exactObject(value, ["schema_version", "mode", "read_only", "authority", "generated_at",
    "principal_ref", "mission", "work_items", "artifacts", "activity"]);
  if (value.schema_version !== SNAPSHOT_VERSION || value.mode !== "core_snapshot" ||
      value.read_only !== true || value.authority !== "none") reject();
  timestamp(value.generated_at); ref(value.principal_ref);
  exactObject(value.mission, ["mission_id", "goal", "status", "objective_ref", "objective_status", "next_action_ref"]);
  ref(value.mission.mission_id); text(value.mission.goal, 1000); text(value.mission.status);
  nullableRef(value.mission.objective_ref); nullableRef(value.mission.next_action_ref);
  if (value.mission.objective_status !== null) text(value.mission.objective_status);
  list(value.work_items, (item) => {
    exactObject(item, ["ref", "status"]); ref(item.ref); text(item.status);
  });
  list(value.artifacts, (item) => {
    exactObject(item, ["ref", "status", "version", "physical_status"]);
    ref(item.ref); text(item.status); text(item.physical_status);
    if (!Number.isSafeInteger(item.version) || item.version < 1) reject();
  });
  list(value.activity, (item) => {
    exactObject(item, ["name", "status"]); ref(item.name); text(item.status);
  });
  return structuredClone(value);
}

export function parseSnapshot(source) {
  if (typeof source !== "string" || new TextEncoder().encode(source).byteLength > MAX_SNAPSHOT_BYTES) reject();
  let value;
  try { value = JSON.parse(source); } catch { reject(); }
  // JSON.parse otherwise silently keeps the last duplicate property. Reject
  // ambiguous files before treating the schema as structurally valid.
  const scopes = [];
  for (const token of source.matchAll(/"(?:\\[\s\S]|[^"\\])*"|[{}\[\]]/gu)) {
    if (token[0] === "{") scopes.push(new Set());
    else if (token[0] === "[") scopes.push(null);
    else if (token[0] === "}" || token[0] === "]") scopes.pop();
    else if (/^\s*:/u.test(source.slice(token.index + token[0].length))) {
      const key = JSON.parse(token[0]);
      const scope = scopes.at(-1);
      if (!scope || scope.has(key)) reject();
      scope.add(key);
    }
  }
  return validateSnapshot(value);
}

export async function readSnapshotFile(file) {
  if (!file || !Number.isSafeInteger(file.size) || file.size < 1 || file.size > MAX_SNAPSHOT_BYTES ||
      typeof file.text !== "function") reject();
  // Recheck decoded bytes so a test adapter cannot bypass the advertised size.
  return parseSnapshot(await file.text());
}
