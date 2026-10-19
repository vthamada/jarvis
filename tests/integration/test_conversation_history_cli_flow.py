"""Explicit CLI history survives a Core restart and affects a fixture answer.

This proves contextual plumbing, not real-model usefulness or voice acceptance.
"""

import json

import pytest
from test_local_model_tool_loop_cli_flow import (
    MODEL as HTTP_MODEL,
)
from test_local_model_tool_loop_cli_flow import (
    REPORT as HTTP_REPORT,
)
from test_local_model_tool_loop_cli_flow import (
    _final,
    _invoke,
    _server,
    _tool,
)

from apps.jarvis_console import local_model_tool_loop_cli as local
from apps.jarvis_console import model_tool_loop_cli as account
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

QUERY = "Compare documentation and observability pilot reports."
REPORT = "Documentation requires recording every pilot outcome."


class ContextualPort:
    evidence_mode = "injected_transport"

    def __init__(self, provider_id):
        self.provider_id = provider_id
        self.requests = []
        self.analysis = None

    def infer(self, request, *, cancellation=None):
        self.requests.append(request)
        payload = json.loads(request.messages[0].content)
        if not payload["observations"]:
            value = {"kind": "tool_call", "call_id": "read-context-report",
                     "tool": "read_local_report", "arguments": {"resource_id": "documentation"}}
        else:
            remembered = any(item["query"] == QUERY for item in payload.get("history", []))
            self.analysis = ("The previous comparison request is available; the report requires "
                             "recording outcomes." if remembered else
                             "No previous comparison request was supplied; the report requires "
                             "recording outcomes.")
            value = {"kind": "final", "analysis": self.analysis,
                     "citations": [{"call_id": "read-context-report", "quote": REPORT}]}
        return InferenceResult(request.request_id, request.model, self.provider_id, "completed",
                               text=json.dumps(value), evidence_mode=self.evidence_mode)


@pytest.mark.parametrize("module", [account, local])
@pytest.mark.parametrize("enabled", [False, True])
def test_two_cli_turns_use_only_explicit_history_after_restart(tmp_path, module, enabled):
    path = tmp_path / "report.txt"
    path.write_text(REPORT, encoding="utf-8")
    runtime = tmp_path / "runtime"
    ports, cores = [], []
    provider_id = "chat_completions_local" if module is local else "responses_plan"

    def core_factory():
        core = _isolated_core(runtime)
        cores.append(core)
        return core

    def port_factory(*_args):
        port = ContextualPort(provider_id)
        ports.append(port)
        return port

    options = dict(reports={"documentation": path}, authorized=True, confirmed=True,
                   reports_confirmed=True, session_id="context-cli-session", model="test-model",
                   core_factory=core_factory, port_factory=port_factory, include_content=True)
    if module is local:
        options.update(endpoint="http://127.0.0.1:11434/v1/chat/completions",
                       upstream_egress_acknowledged=True)
    else:
        options.update(credential_dir=tmp_path / "unopened", profile_ref="profile-" + "a" * 64)
    analyze = local.analyze_local_reports if module is local else account.analyze_reports
    document = {"schema_version": module.INPUT_SCHEMA, "query": QUERY}
    first = analyze(document, **options)
    second = analyze(document, **options, include_canonical_history=enabled)
    assert first["model_tool_loop_status"] == second["model_tool_loop_status"] == "completed"
    assert second["operation_dispatched"] is False
    assert len(cores) == 2 and cores[0] is not cores[1]
    assert len(ports) == 2 and all(len(port.requests) == 2 for port in ports)
    assert ports[1].analysis.startswith("The previous" if enabled else "No previous")
    annex = second["response_text"].split(GENERATIVE_ANALYSIS_MARKER, 1)[1]
    delivered_analysis = [json.loads(line[10:]) for line in annex.splitlines()
                          if line.startswith("Analysis: ")]
    assert delivered_analysis == [ports[1].analysis]
    history = json.loads(ports[1].requests[0].messages[0].content).get("history", [])
    assert len(history) == int(enabled)
    rows = cores[1].memory_service.repository.fetch_recent_turns("context-cli-session", 10)
    assert len(rows) == 2 and rows[-1].response_text == second["response_text"]
    assert rows[0].response_text == first["response_text"]
    assert cores[1].model_tool_loop is None
    assert not (tmp_path / "unopened").exists()


def test_local_http_transports_history_after_canonical_restart(tmp_path):
    report = tmp_path / "http-report.txt"
    report.write_text(HTTP_REPORT, encoding="utf-8")
    with _server([_tool(), _final(), _tool(), _final()]) as (server, endpoint):
        initial = _invoke(tmp_path, endpoint, report, extra=("--include-content",))
        resumed = _invoke(
            tmp_path, endpoint, report,
            extra=("--include-content", "--include-canonical-history"),
        )
        assert initial.returncode == resumed.returncode == 0
        assert initial.stderr == resumed.stderr == b""
        first, second = json.loads(initial.stdout), json.loads(resumed.stdout)
        assert first["model_tool_loop_status"] == second["model_tool_loop_status"] == "completed"
        assert second["model_tool_loop_evidence_mode"] == "live"
        # Physical socket I/O is not acceptance of a real model or local weights.
        assert second["real_model_verified"] is second["local_weights_verified"] is False
        assert all(item[2]["model"] == HTTP_MODEL for item in server.requests)
        bodies = [json.loads(item[2]["messages"][-1]["content"]) for item in server.requests]
        assert len(bodies) == 4 and "history" not in bodies[0]
        assert bodies[2]["history"][0]["query"] == QUERY
        assert bodies[3]["history"] == bodies[2]["history"]
        assert bodies[3]["observations"][0]["text"] == HTTP_REPORT
