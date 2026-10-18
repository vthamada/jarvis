"""Real stdin/HTTP/CLI/Core/SQLite; the HTTP peer is a scripted model, not weights."""

import json
import os
import socketserver
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

ROOT = Path(__file__).resolve().parents[2]
MODEL = "scripted-local-cli-model"
SESSION = "local-http-cli-session"
QUERY = "Compare documentation and observability pilot reports."
REPORT = "HTTP_CLI_REPORT_SENTINEL: Documentation records every pilot outcome."
ANALYSIS = "HTTP_CLI_ANALYSIS_SENTINEL: The selected report records the pilot outcome."
_PROCESS_ENTRY = """
import sys
from pathlib import Path
from apps.jarvis_console import local_model_tool_loop_cli as cli
from apps.jarvis_console import source_review_cli
from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
ensure_src_paths()
from governance_service.service import GovernanceService
from knowledge_service.service import KnowledgeService
from memory_service.service import MemoryService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService
from apps.jarvis_console.voice_pilot import _LocalOnlyObservability
runtime = Path(sys.argv[1])
# Keep cwd/stores disposable. Read public repository knowledge through explicit
# source paths, not _isolated_core's cwd-relative KnowledgeService defaults.
def selected_core():
    governance = GovernanceService()
    return OrchestratorService(
        governance_service=governance,
        memory_service=MemoryService(
            database_url=f"sqlite:///{(runtime / 'memory.db').as_posix()}",
        ),
        observability_service=_LocalOnlyObservability(database_path=str(runtime / "events.db")),
        operational_service=OperationalService(
            artifact_dir=str(runtime / "artifacts"),
            action_confirmation_verifier=governance.verify_action_confirmation_claim,
        ),
        knowledge_service=KnowledgeService(
            corpus_path=str(ROOT / "knowledge" / "curated" / "v1_corpus.json"),
            domain_registry_path=str(ROOT / "knowledge" / "curated" / "domain_registry.json"),
        ),
    )
source_review_cli._default_core_factory = selected_core
raise SystemExit(cli.main(sys.argv[2:]))
"""


def _tool():
    return {"kind": "tool_call", "call_id": "read-http-1", "tool": "read_local_report",
            "arguments": {"resource_id": "documentation"}}


def _final():
    return {"kind": "final", "analysis": ANALYSIS,
            "citations": [{"call_id": "read-http-1", "quote": REPORT}]}


@contextmanager
def _server(proposals, *, model=MODEL, stall=False):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                self.request.settimeout(3)
                raw = b""
                while b"\r\n\r\n" not in raw:
                    chunk = self.request.recv(8192)
                    if not chunk:
                        return
                    raw += chunk
                    if len(raw) > 524288:
                        raise ValueError("fixture_request_too_large")
                headers, body = raw.split(b"\r\n\r\n", 1)
                lines = headers.decode("ascii").split("\r\n")
                fields = dict(line.split(": ", 1) for line in lines[1:])
                expected = int(fields["Content-Length"])
                while len(body) < expected:
                    chunk = self.request.recv(min(8192, expected - len(body)))
                    if not chunk:
                        return
                    body += chunk
                self.server.requests.append((lines[0], fields, json.loads(body)))
                index = len(self.server.requests) - 1
                if stall:
                    self.server.release.wait(2)
                if index >= len(proposals):
                    raise ValueError("unexpected_inference")
                proposal = proposals[index]
                response = json.dumps({
                    "id": "chat-cli-fixture-" + str(index), "object": "chat.completion",
                    "model": model, "choices": [{"index": 0, "finish_reason": "stop",
                                                "message": {"role": "assistant", "content":
                                                            json.dumps(proposal)}}],
                }).encode("utf-8")
                self.request.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                    + str(len(response)).encode("ascii") + b"\r\nConnection: close\r\n\r\n"
                    + response,
                )
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # Expected when the bounded CLI rejects/cancels a response.
            except Exception as exc:
                self.server.errors.append(type(exc).__name__)

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
    server.requests, server.errors = [], []
    server.release = threading.Event()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01},
                              daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"
    finally:
        server.release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive() and server.errors == []


def _invoke(tmp_path, endpoint, report, *, query=QUERY, document=None, extra=(),
            remove=(), timeout=120):
    # Process startup and SQLite preparation are outside the inference budget.
    # This is a test watchdog, not a conversational latency/SLO assertion.
    arguments = ["--authorized", "--confirm-input", "--confirm-reports",
                 "--acknowledge-upstream-egress", "--session-id", SESSION,
                 "--model", MODEL, "--endpoint", endpoint,
                 "--report", "documentation=" + str(report), *extra]
    for flag in remove:
        arguments.remove(flag)
    source = document if document is not None else {
        "schema_version": "jarvis-local-model-tool-loop-v1", "query": query,
    }
    return subprocess.run(
        [sys.executable, "-c", _PROCESS_ENTRY, str(tmp_path / "runtime"), *arguments],
        cwd=tmp_path, input=json.dumps(source).encode("utf-8"), capture_output=True,
        timeout=timeout, env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
                                  DATABASE_URL="postgresql://must-not-connect.invalid/synthetic"),
    )


@pytest.mark.parametrize("include_content", [False, True])
def test_real_cli_reads_selected_report_under_core_and_restarts_exact_final(
    tmp_path, include_content,
):
    report = tmp_path / "selected-report.txt"
    report.write_text(REPORT, encoding="utf-8")
    with _server([_tool(), _final()]) as (server, endpoint):
        result = _invoke(tmp_path, endpoint, report,
                         extra=("--include-content",) if include_content else ())
        assert result.returncode == 0 and result.stderr == b""
        payload = json.loads(result.stdout)
        assert payload["schema_version"] == "jarvis-local-model-tool-loop-result-v1"
        assert payload["status"] == "recorded" and payload["canonical_turn_recorded"] is True
        assert payload["model_tool_loop_status"] == "completed"
        assert payload["model_tool_loop_observation_count"] == 1
        assert payload["model_tool_loop_evidence_mode"] == "live"  # Socket evidence only.
        assert payload["real_model_verified"] is False
        assert payload["local_weights_verified"] is False
        assert payload["account_used"] is False and payload["upstream_egress_possible"] is True
        assert payload["operation_dispatched"] is False and payload["authority"] == "none"
        assert payload["operator_authenticated"] is False
        assert payload["runtime_capability_promoted"] is False
        assert len(server.requests) == 2
        for line, headers, value in server.requests:
            assert line == "POST /v1/chat/completions HTTP/1.1"
            assert "Authorization" not in headers and "Cookie" not in headers
            assert value["model"] == MODEL and value["stream"] is False and value["n"] == 1
            assert str(report) not in json.dumps(value) and endpoint not in json.dumps(value)
        first = json.loads(server.requests[0][2]["messages"][-1]["content"])
        second = json.loads(server.requests[1][2]["messages"][-1]["content"])
        assert first["observations"] == []
        assert second["observations"][0]["text"] == REPORT
    restarted = _isolated_core(tmp_path / "runtime")
    turns = restarted.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(turns) == 1 and turns[0].request_content == QUERY
    assert turns[0].user_id == "user://local_operator"
    assert GENERATIVE_ANALYSIS_MARKER in turns[0].response_text
    # Native synthesis intentionally escapes active markup (including `_`).
    # Decode its actual JSON literals rather than copying the escape algorithm
    # or weakening the exact analysis/citation and canonical readback checks.
    annex = turns[0].response_text.split(GENERATIVE_ANALYSIS_MARKER, 1)[1]
    rendered = {}
    for line in annex.splitlines():
        key, separator, literal = line.partition(": ")
        if separator:
            assert key not in rendered
            rendered[key] = json.loads(literal)
    assert rendered == {"Analysis": ANALYSIS, "Selected report": "documentation",
                        "Observed quote": REPORT}
    assert payload["response_character_count"] == len(turns[0].response_text)
    assert payload["content_included"] is include_content
    if include_content:
        assert payload["response_text"] == turns[0].response_text
    else:
        assert "response_text" not in payload
        for text in (QUERY, REPORT, ANALYSIS):
            assert text.encode() not in result.stdout
    assert endpoint.encode() not in result.stdout and str(tmp_path).encode() not in result.stdout
    events = restarted.observability_service.repository.list_events(session_id=SESSION, limit=100)
    synthesis = [event for event in events if event.event_name == "response_synthesized"]
    assert len(synthesis) == 1
    assert synthesis[0].payload["model_tool_loop_status"] == "completed"
    assert any(event.event_name == "model_tool_loop_governance_checked" for event in events)
    metadata = json.dumps([event.payload for event in events], default=str)
    for private in (REPORT, ANALYSIS, endpoint, str(tmp_path)):
        assert private not in metadata
    telemetry = json.dumps([event.payload for event in events if (
        event.event_name.startswith("model_tool_loop_")
        or event.event_name == "response_synthesized"
    )], default=str)
    assert QUERY not in telemetry  # Native input_received/memory intentionally retain it.


@pytest.mark.parametrize("case", ["egress", "sensitive", "extra_endpoint", "extra_tools"])
def test_real_cli_input_and_consent_refusals_never_contact_http_or_open_runtime(tmp_path, case):
    report = tmp_path / "not-read.txt"
    with _server([]) as (server, endpoint):
        options = {}
        if case == "egress":
            options["remove"] = ("--acknowledge-upstream-egress",)
        elif case == "sensitive":
            options["query"] = QUERY + " password=synthetic-secret"
        else:
            document = {"schema_version": "jarvis-local-model-tool-loop-v1", "query": QUERY}
            document["endpoint" if case == "extra_endpoint" else "tools"] = (
                "http://192.0.2.1/private" if case == "extra_endpoint" else ["execute_shell"]
            )
            options["document"] = document
        result = _invoke(tmp_path, endpoint, report, **options)
        assert result.returncode == 2 and result.stderr == b""
        assert json.loads(result.stdout) == {
            "status": "refused", "error_code": "invalid_local_model_tool_loop_input",
        }
        assert server.requests == []
    assert not report.exists() and not (tmp_path / "runtime").exists()


@pytest.mark.parametrize("query,decision", [
    ("Delete every database now.", "block"),
    ("Analyze policy evidence in read-only mode.", "defer_for_validation"),
])
def test_real_cli_native_refusal_is_canonical_without_http_or_report_read(
    tmp_path, query, decision,
):
    report = tmp_path / "not-read.txt"
    with _server([]) as (server, endpoint):
        result = _invoke(tmp_path, endpoint, report, query=query)
        assert result.returncode == 0 and result.stderr == b""
        payload = json.loads(result.stdout)
        assert payload["governance_decision"] == decision
        assert payload["model_tool_loop_status"] == "withheld"
        assert payload["model_tool_loop_observation_count"] == 0
        assert server.requests == []
    turns = _isolated_core(tmp_path / "runtime").memory_service.repository.fetch_recent_turns(
        SESSION, 10,
    )
    assert len(turns) == 1 and turns[0].request_content == query
    assert GENERATIVE_ANALYSIS_MARKER not in turns[0].response_text and not report.exists()


@pytest.mark.parametrize("proposal", [
    {"kind": "tool_call", "call_id": "attack-1", "tool": "execute_shell",
     "arguments": {"command": "delete everything"}},
    {"kind": "tool_call", "call_id": "attack-1", "tool": "read_local_report",
     "arguments": {"resource_id": "documentation", "endpoint": "http://192.0.2.1/private"}},
    {"kind": "tool_call", "call_id": "attack-1", "tool": "read_local_report",
     "arguments": {"resource_id": "unselected-private-report"}},
])
def test_model_cannot_open_remote_endpoint_or_expand_tool_authority(tmp_path, proposal):
    report = tmp_path / "not-read.txt"
    with _server([proposal]) as (server, endpoint):
        result = _invoke(tmp_path, endpoint, report, extra=("--include-content",))
        assert result.returncode == 0 and result.stderr == b""
        payload = json.loads(result.stdout)
        assert payload["model_tool_loop_status"] == "refused"
        assert payload["model_tool_loop_observation_count"] == 0
        assert payload["operation_dispatched"] is False and len(server.requests) == 1
        assert GENERATIVE_ANALYSIS_MARKER not in payload["response_text"]
        assert "192.0.2.1" not in payload["response_text"]
    assert not report.exists()


def test_real_cli_model_echo_mismatch_keeps_native_final_and_makes_no_retry(tmp_path):
    report = tmp_path / "not-read.txt"
    with _server([_tool()], model="unselected-model") as (server, endpoint):
        result = _invoke(tmp_path, endpoint, report)
        assert result.returncode == 0 and result.stderr == b""
        payload = json.loads(result.stdout)
        assert payload["model_tool_loop_status"] in {"failed", "refused"}
        assert payload["model_tool_loop_observation_count"] == 0
        assert payload["canonical_turn_recorded"] is True and len(server.requests) == 1
    assert not report.exists()


def test_real_cli_total_deadline_stops_http_without_retry_or_report_read(tmp_path):
    report = tmp_path / "not-read.txt"
    with _server([_tool()], stall=True) as (server, endpoint):
        result = _invoke(tmp_path, endpoint, report, extra=("--timeout-seconds", "0.3"))
        assert result.returncode == 0 and result.stderr == b""
        payload = json.loads(result.stdout)
        assert payload["model_tool_loop_status"] == "timed_out"
        assert payload["model_tool_loop_observation_count"] == 0
        assert payload["canonical_turn_recorded"] is True and len(server.requests) <= 1
    assert not report.exists()
