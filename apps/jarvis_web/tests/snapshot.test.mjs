import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { validateSnapshot, parseSnapshot, readSnapshotFile } from "../snapshot.mjs";
import { createController, handlePageHide } from "../controller.mjs";

const fixture = () => JSON.parse(readFileSync(new URL("./snapshot-fixture.json", import.meta.url), "utf8"));
const file = (value) => new Blob([JSON.stringify(value)], { type: "application/json" });
const deferred = () => {
  let resolve;
  const promise = new Promise((settle) => { resolve = settle; });
  return { file: { size: 1000, text: () => promise }, resolve };
};

test("valid schema is cloned without claiming verified origin", async () => {
  const value = fixture();
  const result = validateSnapshot(value);
  result.mission.goal = "Changed";
  assert.notEqual(value.mission.goal, result.mission.goal);
  assert.deepEqual(await readSnapshotFile(file(value)), value);
});
test("schema flags, extra/missing fields, identities and arrays fail closed", () => {
  const mutations = [
    (s) => { s.authority = "admin"; }, (s) => { s.mode = "live"; },
    (s) => { s.read_only = "true"; }, (s) => { s.schema_version = "v0"; },
    (s) => { s.access_token = "secret"; }, (s) => { delete s.generated_at; },
    (s) => { s.principal_ref = "x".repeat(201); }, (s) => { s.mission.goal = "x".repeat(1001); },
    (s) => { s.mission.next_action_ref = 2; }, (s) => { s.mission.objective_status = false; },
    (s) => { s.mission.hidden = "extra"; }, (s) => { s.work_items = {}; },
    (s) => { s.work_items = Array(101).fill(s.work_items[0]); },
    (s) => { s.artifacts = Array(101).fill(s.artifacts[0]); },
    (s) => { s.activity = Array(101).fill(s.activity[0]); },
    (s) => { s.work_items[0].extra = "secret"; },
    (s) => { s.artifacts[0].version = 1.5; }, (s) => { s.artifacts[0].version = 0; },
    (s) => { s.artifacts[0].version = true; },
    (s) => { s.activity[0].name = "x".repeat(201); },
    (s) => { s.mission.status = ""; }, (s) => { s.mission.goal = "bad\u0000text"; },
  ];
  for (const mutate of mutations) {
    const value = fixture(); mutate(value); assert.throws(() => validateSnapshot(value));
  }
});
test("invalid JSON, duplicate keys and malformed timestamps are rejected", () => {
  assert.throws(() => parseSnapshot("not json"));
  const source = JSON.stringify(fixture());
  assert.throws(() => parseSnapshot(source.replace('"authority":"none"', '"authority":"admin","authority":"none"')));
  assert.throws(() => parseSnapshot(source.replace('"goal":', '"goal":"first","goal":')));
  for (const generated_at of ["today", "2026-02-30T00:00:00Z", "2026-10-02", "2026-10-02T24:00:00Z"]) {
    assert.throws(() => validateSnapshot({ ...fixture(), generated_at }));
  }
});
test("escaped JSON keys cannot evade duplicate detection; string punctuation stays data", () => {
  const source = JSON.stringify(fixture());
  assert.throws(() => parseSnapshot(source.replace('"authority":"none"', '"author\\u0069ty":"none","authority":"none"')));
  const value = fixture(); value.mission.goal = 'Words "key": { [ punctuation ] }';
  assert.deepEqual(parseSnapshot(JSON.stringify(value)), value);
});
test("byte limits are enforced before and after reading, including UTF-8", async () => {
  let reads = 0;
  await assert.rejects(() => readSnapshotFile({ size: 65537, text() { reads += 1; return ""; } }));
  assert.equal(reads, 0);
  await assert.rejects(() => readSnapshotFile({ size: 20, text: async () => "é".repeat(40000) }));
  assert.throws(() => parseSnapshot("x".repeat(65537)));
  await assert.rejects(() => readSnapshotFile({ size: 0, text: async () => "" }));
});
test("import never replaces identity, conversation, fixture mode or authority", async () => {
  const controller = createController();
  const before = controller.getSnapshot();
  assert.equal(await controller.importSnapshotFile(file(fixture())), true);
  const after = controller.getSnapshot();
  assert.equal(after.mode, "fixture");
  assert.equal(after.principalId, before.principalId);
  assert.equal(after.sessionId, before.sessionId);
  assert.deepEqual(after.messages, before.messages);
  assert.match(after.snapshotNotice, /origem não verificada/);
  assert.equal(after.snapshotStatus, "loaded");
  assert.equal(controller.submit("Not this identity", { principalId: after.importedSnapshot.principal_ref }), false);
});
test("invalid import preserves prior view and does not expose malformed content", async () => {
  const controller = createController();
  await controller.importSnapshotFile(file(fixture()));
  const prior = controller.getSnapshot().importedSnapshot;
  assert.equal(await controller.importSnapshotFile(file({ access_token: "secret" })), false);
  assert.deepEqual(controller.getSnapshot().importedSnapshot, prior);
  assert.equal(controller.getSnapshot().snapshotStatus, "error");
  assert.doesNotMatch(controller.getSnapshot().snapshotNotice, /secret/);
});
test("newer imports win; stale successful or failed reads cannot overwrite them", async () => {
  const controller = createController();
  const old = deferred();
  const pending = controller.importSnapshotFile(old.file);
  const newer = fixture(); newer.mission.goal = "Newest snapshot";
  await controller.importSnapshotFile(file(newer));
  old.resolve(JSON.stringify(fixture()));
  assert.equal(await pending, false);
  assert.equal(controller.getSnapshot().importedSnapshot.mission.goal, "Newest snapshot");
  const staleError = deferred(); const failure = controller.importSnapshotFile(staleError.file);
  await controller.importSnapshotFile(file(newer)); staleError.resolve("broken");
  assert.equal(await failure, false);
  assert.equal(controller.getSnapshot().snapshotStatus, "loaded");
});
test("reset restores fixtures and invalidates pending import", async () => {
  const controller = createController();
  await controller.importSnapshotFile(file(fixture()));
  const delayed = deferred(); const pending = controller.importSnapshotFile(delayed.file);
  controller.reset(); delayed.resolve(JSON.stringify(fixture()));
  assert.equal(await pending, false);
  assert.equal(controller.getSnapshot().importedSnapshot, null);
  assert.equal(controller.getSnapshot().snapshotStatus, "idle");
});
test("dispose/BFCache cancel pending import; no stale callback or new read accepted", async () => {
  for (const persisted of [true, false]) {
    const controller = createController();
    const delayed = deferred(); const pending = controller.importSnapshotFile(delayed.file);
    handlePageHide(controller, { persisted }); delayed.resolve(JSON.stringify(fixture()));
    assert.equal(await pending, false);
    assert.equal(controller.getSnapshot().importedSnapshot, null);
    assert.equal(await controller.importSnapshotFile(file(fixture())), persisted);
  }
});
test("hostile goal remains a text value, never executable code", () => {
  const value = fixture(); value.mission.goal = '<img src=x onerror="alert(1)">';
  assert.equal(parseSnapshot(JSON.stringify(value)).mission.goal, value.mission.goal);
});
test("all metadata strings are bounded at 200 codepoints; goal allows 1000", () => {
  for (const change of [
    (s) => { s.mission.status = "x".repeat(201); },
    (s) => { s.mission.objective_status = "x".repeat(201); },
    (s) => { s.work_items[0].status = "x".repeat(201); },
    (s) => { s.artifacts[0].status = "x".repeat(201); },
    (s) => { s.artifacts[0].physical_status = "x".repeat(201); },
    (s) => { s.activity[0].status = "x".repeat(201); },
    (s) => { s.generated_at = "x".repeat(65); },
  ]) {
    const value = fixture(); change(value); assert.throws(() => validateSnapshot(value));
  }
  const value = fixture(); value.mission.goal = "😀".repeat(1000);
  value.principal_ref = "😀".repeat(200);
  assert.equal(validateSnapshot(value).mission.goal, value.mission.goal);
  value.principal_ref += "😀"; assert.throws(() => validateSnapshot(value));
});
