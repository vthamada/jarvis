"""Real local HTTP and SQLite: no accounts, executors or model requests."""

import hashlib
import http.client
import json
import shutil
import subprocess
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from job_service.store import JobSpec, SqliteJobStore

from apps.jarvis_api.local_auth import LocalAuth
from apps.jarvis_api.local_server import create_server

NOW = datetime(2026, 10, 13, tzinfo=UTC)


class NoAnalysis:
    def current_ticket(self, _identity):
        return None

    def __getattr__(self, _name):
        pytest.fail("activity must not invoke analysis, Core or inference")


@contextmanager
def running(profile=None, auth=None):
    options = {} if profile is None else {"job_activity_profile": profile}
    server = create_server(NoAnalysis(), auth=auth, **options)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    context = {"server": server}
    try:
        yield context
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def request(ctx, path="/api/job-activity", *, method="GET", body=None, headers=None):
    origin = f"http://127.0.0.1:{ctx['server'].server_port}"
    fields = {"X-Jarvis-Client": "local-web-v1"}
    if "cookie" in ctx:
        fields.update(Cookie=ctx["cookie"], **{"X-Jarvis-CSRF": ctx["csrf"]})
    if method == "POST":
        fields["Origin"] = origin
    if body is not None:
        body = json.dumps(body).encode("ascii")
        fields["Content-Type"] = "application/json"
    fields.update(headers or {})
    connection = http.client.HTTPConnection("127.0.0.1", ctx["server"].server_port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=fields)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), json.loads(response.read())
    finally:
        connection.close()


def pair(ctx):
    code, headers, value = request(ctx, "/api/pair", method="POST",
                                   body={"secret": ctx["server"].auth.pairing_secret})
    assert code == 200
    ctx.update(cookie=headers["Set-Cookie"].split(";", 1)[0], csrf=value["csrf_token"])
    return value["session_ref"]


def profile(path, *, actor="private-actor", session="private-session", ids=("private-job",)):
    from apps.jarvis_api.job_activity_profile import JobActivityProfile

    return JobActivityProfile(authorized=True, database_path=path,
                             actor_ref=actor, session_ref=session, job_ids=ids)


def seed(path):
    store = SqliteJobStore(path, clock=lambda: NOW)
    for job in ("private-job", "private-done"):
        store.register(JobSpec(job, "private-actor", "private-session", "private-responsibility",
                               "private-approval", "fixture:success", NOW + timedelta(hours=1), 3))
    claim = store.claim("private-done", actor_ref="private-actor", session_ref="private-session",
                        worker_id="private-worker", expected_version=0)
    store.finish(claim, "succeeded")


def fingerprints(path):
    return {item.name: (hashlib.sha256(item.read_bytes()).hexdigest(), item.stat().st_mtime_ns)
            for item in path.parent.iterdir() if item.is_file()}


def test_disabled_activity_is_explicit_after_pairing():
    with running() as ctx:
        pair(ctx)
        code, _, result = request(ctx)
        assert (code, result) == (409, {"error_code": "job_activity_disabled"})


def test_real_selected_ledger_reaches_paired_http_and_survives_reader_restart(tmp_path):
    path = tmp_path / "private-ledger.db"
    seed(path)
    before = fingerprints(path)
    for _ in range(2):
        with running(profile(path, ids=("private-job", "private-done"))) as ctx:
            session = pair(ctx)
            code, headers, result = request(ctx)
            assert code == 200
            assert headers["Cache-Control"] == "no-store"
            assert headers["X-Content-Type-Options"] == "nosniff"
            assert result.keys() == {"schema_version", "session_ref", "activity"}
            assert result["schema_version"] == "jarvis-local-job-activity-v1"
            assert result["session_ref"] == session
            activity = result["activity"]
            assert activity["selected_job_count"] == 2
            assert activity["status_counts"]["registered"] == 1
            assert activity["status_counts"]["succeeded"] == 1
            assert activity["progress"]["terminal_count"] == 1
            assert activity["operator_authenticated"] is False
            assert activity["authority"] == "none"
            assert "private" not in json.dumps(result)
            assert fingerprints(path) == before


@pytest.mark.parametrize("case", ["unpaired", "csrf", "expired", "client", "origin",
                                    "query", "head", "post", "revoke"])
def test_denied_boundary_never_reads_ledger(tmp_path, monkeypatch, case):
    configured = profile(tmp_path / "never-opened.db")
    monkeypatch.setattr(type(configured), "read", lambda _self: pytest.fail("denied read"))
    clock = [100.0]
    with running(configured, LocalAuth(clock=lambda: clock[0])) as ctx:
        if case != "unpaired":
            pair(ctx)
        headers, path, method = {}, "/api/job-activity", "GET"
        if case == "csrf":
            headers["X-Jarvis-CSRF"] = "a" * 64
        if case == "expired":
            clock[0] += 1000
        if case == "client":
            headers["X-Jarvis-Client"] = "foreign"
        if case == "origin":
            headers["Origin"] = "https://foreign.invalid"
        if case == "query":
            path += "?job=private"
        if case == "head":
            method = "HEAD"
        if case == "post":
            method = "POST"
        if case == "revoke":
            ctx["server"].auth.revoke(ctx["cookie"].split("=", 1)[1])
        # HEAD deliberately carries no response body.
        if method == "HEAD":
            connection = http.client.HTTPConnection("127.0.0.1", ctx["server"].server_port)
            try:
                connection.request(method, path, headers={"X-Jarvis-Client": "local-web-v1"})
                response = connection.getresponse()
                assert response.status == 400 and response.read() == b""
            finally:
                connection.close()
        else:
            code, _, value = request(ctx, path, method=method, headers=headers)
            assert code in {400, 401, 403}
            assert value.keys() == {"error_code"}
        assert not (tmp_path / "never-opened.db").exists()


@pytest.mark.parametrize("case", ["foreign_actor", "foreign_session", "missing_job", "wal"])
def test_source_denials_are_fixed_and_do_not_write(tmp_path, case):
    path = tmp_path / "private-ledger.db"
    seed(path)
    if case == "wal":
        path.with_name(path.name + "-wal").write_bytes(b"private")
    configured = profile(path, actor="foreign" if case == "foreign_actor" else "private-actor",
                         session="foreign" if case == "foreign_session" else "private-session",
                         ids=("missing",) if case == "missing_job" else ("private-job",))
    before = fingerprints(path)
    with running(configured) as ctx:
        pair(ctx)
        code, _, result = request(ctx)
        assert (code, result) == (503, {"error_code": "job_activity_unavailable"})
    assert fingerprints(path) == before


def test_session_revoked_during_read_withholds_result(tmp_path, monkeypatch):
    path = tmp_path / "ledger.db"
    seed(path)
    configured = profile(path)
    original = type(configured).read
    with running(configured) as ctx:
        pair(ctx)

        def revoked_read(self):
            result = original(self)
            ctx["server"].auth.revoke(ctx["cookie"].split("=", 1)[1])
            return result

        monkeypatch.setattr(type(configured), "read", revoked_read)
        code, _, result = request(ctx)
        assert (code, result) == (401, {"error_code": "session_refused"})


def test_actual_sqlite_http_controller_and_panel_flow(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required to verify the frontend runtime")
    path = tmp_path / "private-ledger.db"
    seed(path)
    before = fingerprints(path)
    web = Path(__file__).resolve().parents[2] / "apps" / "jarvis_web"
    # Native Node fetch exercises the HTTP wire. The small DOM seam executes
    # the real panel; it does not claim browser layout or human acceptance.
    program = """
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const [origin, secret, controllerUri, panelUri, htmlPath] = process.argv.slice(1);
const {createLiveController} = await import(controllerUri);
const {createJobActivityPanel} = await import(panelUri);
const markup = readFileSync(htmlPath, 'utf8');
let cookie = '', calls = [];
const controller = createLiveController({transport: async (path, options) => {
  calls.push(path);
  const headers = {...options.headers, Origin: origin};
  if (cookie) headers.Cookie = cookie;
  const result = await fetch(origin + path, {...options, headers});
  const issued = result.headers.get('set-cookie');
  if (issued) cookie = issued.split(';',1)[0];
  return result;
}});
class Element {
  textContent = ''; disabled = false; listeners = new Map();
  set innerHTML(value) { assert.fail('HTML sink'); }
  addEventListener(name, fn) { this.listeners.set(name, fn); }
  removeEventListener(name, fn) {
    if (this.listeners.get(name) === fn) this.listeners.delete(name);
  }
}
const ids = ['live-job-refresh','live-job-status','live-job-summary'];
for (const id of ids) assert.ok(markup.includes('id="' + id + '"'));
const elements = Object.fromEntries(ids.map(id => [id,new Element()]));
const panel = createJobActivityPanel({document:{getElementById:id => elements[id]},
  read: options => controller.readJobActivity(options)});
try {
  assert.deepEqual(calls, []);
  await controller.pair(secret);
  assert.equal(controller.getState().status, 'ready');
  panel.setSession(controller.getState().sessionRef);
  assert.deepEqual(calls, ['/api/pair']);
  assert.equal(elements['live-job-refresh'].disabled, false);
  const prior = controller.getState();
  await panel.refresh();
  assert.equal(panel.getState().status,'ready');
  assert.match(elements['live-job-summary'].textContent, /2 jobs selecionados/);
  assert.match(elements['live-job-summary'].textContent, /Registrados: 1/);
  assert.match(elements['live-job-summary'].textContent, /Concluídos: 1/);
  assert.doesNotMatch(elements['live-job-summary'].textContent,/private|mem-record/);
  assert.deepEqual(controller.getState(),prior);
  assert.deepEqual(calls,['/api/pair','/api/job-activity']);
  controller.pageHide(); panel.setSession(null);
  assert.equal(elements['live-job-summary'].textContent,'');
  assert.equal(elements['live-job-refresh'].disabled,true);
  await panel.refresh();
  assert.deepEqual(calls,['/api/pair','/api/job-activity']);
  console.log(JSON.stringify({flow:'sqlite_http_controller_panel',selected:2,requests:2,
    core_invoked:false,ledger_scope:'host_selected',cleared_on_disconnect:true}));
} finally { controller.pageHide(); panel.dispose(); }
"""
    with running(profile(path, ids=("private-job", "private-done"))) as ctx:
        server = ctx["server"]
        command = [node, "--input-type=module", "-e", program,
                   f"http://127.0.0.1:{server.server_port}", server.auth.pairing_secret,
                   (web / "live-controller.mjs").as_uri(),
                   (web / "live-job-activity.mjs").as_uri(), str(web / "live-index.html")]
        result = subprocess.run(command, capture_output=True, timeout=20, check=False)
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        assert not result.stderr
        assert json.loads(result.stdout) == {
            "flow": "sqlite_http_controller_panel", "selected": 2, "requests": 2,
            "core_invoked": False, "ledger_scope": "host_selected", "cleared_on_disconnect": True,
        }
    assert fingerprints(path) == before
