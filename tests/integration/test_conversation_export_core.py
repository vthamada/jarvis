"""Owned Core SQLite -> offline export -> real JS parser/text-only DOM.

No provider/account/network/installed LangGraph acceptance is claimed. Fixtures
exercise original Core policy, persistence and synthesis, never runtime priors.
"""

import json
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from orchestrator_service import langgraph_flow
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.conversation_export import SCHEMA, export_conversation
from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.types import PermissionDecision

ROOT = Path(__file__).resolve().parents[2]
QUERIES = (
    "Compare documentation and observability pilot reports.",
    "Compare os relatórios de documentação e observabilidade do piloto.",
)
ANALYSIS = (
    "Compare documentation coverage with measured observability outcomes. "
    "List the evidence present in each pilot report before identifying gaps; "
    "do not assume unreported results. Medição pública 📊."
)


class _GraphFixture:
    """Bounded owned scheduler, not an installed LangGraph runtime."""

    def __init__(self, _state_type):
        self.nodes, self.edges = {}, {}

    def add_node(self, name, handler):
        self.nodes[name] = handler

    def add_edge(self, start, end):
        self.edges[start] = end

    def compile(self):
        return self

    def invoke(self, initial):
        state, node = dict(initial), "start"
        for _ in range(32):
            node = self.edges[node]
            if node == "end":
                return state
            state.update(self.nodes[node](state))
        raise AssertionError("owned graph did not terminate")


class _AnalysisFixture:
    def __init__(self):
        self.calls = []

    def infer(self, request, *, cancellation=None):
        assert cancellation is None or not cancellation.is_set()
        self.calls.append(request)
        source = json.loads(request.messages[-1].content)["sources"][0]["text"]
        assert source in (*QUERIES, "Review documentation and telemetry pilot reports.",
                          "Delete every database now.")
        return InferenceResult(
            request.request_id, request.model, "fixture", "completed",
            text=json.dumps({"analysis": ANALYSIS, "assumptions": [],
                             "limitations": [], "citations": []}),
        )


def _run(tmp_path, monkeypatch, *, flow="native", query=QUERIES[0], generative=True):
    monkeypatch.setattr(langgraph_flow, "_load_langgraph",
                        lambda: (_GraphFixture, "start", "end"))
    runtime = tmp_path / "owned-core"
    core, port = _isolated_core(runtime), _AnalysisFixture()
    if generative:
        core.synthesis_engine = SynthesisEngine(generative_port=port,
                                               generative_model="mb230-fixture")
    value = PilotContext("mb230-public-subject", "mb230-public-session").input(
        "mb230-public-request", query,
    )
    value = replace(value, user_id=value.canonical_user_ref)
    response = (core.handle_input(value) if flow == "native"
                else core.handle_input_langgraph_flow(value))
    assert response.operation_dispatch is None and response.operation_result is None
    assert response.adapter_grant is None and response.action_confirmation_claim is None
    assert response.deliberative_plan.requested_autonomy_level == "assist_only"
    assert response.deliberative_plan.autonomy_human_confirmation_required is (
        response.governance_decision.decision == PermissionDecision.BLOCK
    )

    # Recreate services before snapshots. Export itself must not perform restart,
    # migrations, schema creation, checkpoint or any Core/inference operation.
    restarted = _isolated_core(runtime)
    turns = restarted.memory_service.repository.fetch_recent_turns(value.session_id, 10)
    assert len(turns) == 1
    turn = turns[0]
    assert turn.user_id == value.canonical_user_ref == value.user_id
    assert turn.request_content == value.content
    assert turn.response_text == response.response_text
    assert turn.timestamp == response.memory_record.timestamp
    options = dict(memory_db=runtime / "memory.db", events_db=runtime / "events.db",
                   session_id=value.session_id, request_id=value.request_id,
                   principal_ref=value.user_id, authorized=True)
    return runtime, value, response, turn, port, options


def _snapshot(runtime):
    return {
        str(path.relative_to(runtime)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in runtime.rglob("*") if path.is_file()
    }, sorted(str(path.relative_to(runtime)) for path in runtime.rglob("*"))


def _digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _parse_and_render(pack):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable: real JS parser/DOM acceptance requires local Node")
    module_url = (ROOT / "apps/jarvis_web/conversation-pack.mjs").as_uri()
    script = """
import {webcrypto} from 'node:crypto';
import {readFileSync} from 'node:fs';
const {parseConversationPack, renderConversationPack, CONVERSATION_PACK_ORIGIN_LABEL} =
  await import(MODULE_URL);
class TextSink {
  constructor() { this.textContent = 'previous content'; }
  set innerHTML(value) { throw new Error('HTML sink forbidden'); }
  set outerHTML(value) { throw new Error('HTML sink forbidden'); }
  insertAdjacentHTML() { throw new Error('HTML sink forbidden'); }
  appendChild() { throw new Error('DOM insertion forbidden'); }
}
const nodes = Object.fromEntries(['status','query','response','metadata'].map(
  key => [key, new TextSink()]));
try {
  const pack = await parseConversationPack(readFileSync(0, 'utf8'), {crypto:webcrypto});
  renderConversationPack({status:'ready', pack}, nodes);
  process.stdout.write(JSON.stringify({pack, originLabel:CONVERSATION_PACK_ORIGIN_LABEL,
    status:nodes.status.textContent, query:nodes.query.textContent,
    response:nodes.response.textContent, metadata:nodes.metadata.textContent}));
} catch {
  renderConversationPack({status:'error', pack:null}, nodes);
  process.stdout.write(JSON.stringify({refused:true, query:nodes.query.textContent,
    response:nodes.response.textContent, status:nodes.status.textContent}));
}
""".replace("MODULE_URL", json.dumps(module_url))
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        input=json.dumps(pack, ensure_ascii=False), encoding="utf-8",
        capture_output=True, check=False, timeout=20, cwd=ROOT,
    )
    assert result.returncode == 0, "local Node parser subprocess failed"
    assert result.stderr == ""
    return json.loads(result.stdout)


def _cli(options, *, include_content):
    args = [sys.executable, "-m", "apps.jarvis_console.conversation_export", "--authorized"]
    for key in ("memory_db", "events_db", "session_id", "request_id", "principal_ref"):
        args.extend(["--" + key.replace("_", "-"), str(options[key])])
    if include_content:
        args.append("--include-content")
    return subprocess.run(args, capture_output=True, encoding="utf-8", check=False,
                          timeout=20, cwd=ROOT)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize("query", QUERIES, ids=["en", "pt"])
@pytest.mark.parametrize("generative", [False, True], ids=["disabled", "accepted"])
@pytest.mark.parametrize("include_content", [False, True], ids=["metadata", "content"])
def test_core_restart_export_real_js_parser_and_exact_text_dom(
    tmp_path, monkeypatch, flow, query, generative, include_content,
):
    runtime, value, response, turn, port, options = _run(
        tmp_path, monkeypatch, flow=flow, query=query, generative=generative,
    )
    assert response.governance_decision.decision == PermissionDecision.ALLOW
    assert len(port.calls) == int(generative)
    if generative:
        assert "Compare documentation coverage with measured observability outcomes." in (
            turn.response_text
        )
        assert json.loads(port.calls[0].messages[-1].content)["sources"][0]["text"] == query
    before = _snapshot(runtime)
    with closing(sqlite3.connect(options["events_db"].as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM internal_events WHERE request_id = ? "
            "AND event_name IN ('input_received', 'governance_checked', "
            "'response_synthesized', 'memory_recorded')", (value.request_id,),
        ).fetchall()
    assert len(rows) == 4
    assert all(row["source_service"] == "orchestrator-service"
               and row["session_id"] == value.session_id
               and row["correlation_id"] == value.request_id for row in rows)
    persisted = {row["event_name"]: json.loads(row["payload"]) for row in rows}
    assert persisted["input_received"]["content"] == query
    assert persisted["input_received"]["canonical_user_ref"] == value.user_id
    assert persisted["memory_recorded"]["memory_record_id"] == (
        response.memory_record.memory_record_id
    )
    assert persisted["memory_recorded"]["conversation_readback"] == {
        "schema_version": "jarvis-conversation-readback-v1",
        "record_timestamp": turn.timestamp,
        "principal_sha256": _digest(value.user_id),
        "request_content_sha256": _digest(query),
        "response_text_sha256": _digest(turn.response_text),
    }
    pack = export_conversation(**options, include_content=include_content)
    assert _snapshot(runtime) == before
    assert len(port.calls) == int(generative)
    assert pack["timestamp"] == response.memory_record.timestamp == turn.timestamp
    assert pack["memory_record_ref"] == "memory-record:sha256:" + _digest(
        response.memory_record.memory_record_id,
    )
    assert pack["principal_ref"] == "principal:sha256:" + _digest(value.user_id)
    assert pack["request_ref"] == "request:sha256:" + _digest(value.request_id)
    assert pack["session_ref"] == "session:sha256:" + _digest(value.session_id)
    assert pack["origin"] == "canonical_core_export" and pack["authority"] == "none"
    assert pack["operator_authenticated"] is False
    assert pack["runtime_capability_promoted"] is False
    assert pack["content_included"] is include_content and pack["content_withheld"] is False
    assert pack["generative_status"] == ("accepted" if generative else "disabled")
    assert pack["generative_evidence_mode"] == ("fixture" if generative else None)
    assert pack["generative_error_code"] is None
    assert pack["generative_analysis_characters"] == (len(ANALYSIS) if generative else 0)
    assert pack["request_character_count"] == len(query)
    assert pack["response_character_count"] == len(turn.response_text)
    rendered = _parse_and_render(pack)
    assert rendered["pack"] == pack
    assert rendered["originLabel"] == "pacote offline — origem não autenticada"
    assert rendered["status"].startswith(rendered["originLabel"])
    assert "decisão declarada: allow" in rendered["metadata"]
    if include_content:
        assert pack["query"].encode("utf-8") == turn.request_content.encode("utf-8")
        assert pack["response_text"].encode("utf-8") == turn.response_text.encode("utf-8")
        assert pack["content_sha256"] == _digest(SCHEMA + "\0" + query + "\0" + turn.response_text)
        assert rendered["query"] == query and rendered["response"] == turn.response_text
    else:
        assert "query" not in pack and "response_text" not in pack
        assert pack["content_sha256"] is None
        assert rendered["query"] == rendered["response"] == ""
    assert _snapshot(runtime) == before


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize("query,decision", [
    ("Review documentation and telemetry pilot reports.", PermissionDecision.DEFER_FOR_VALIDATION),
    ("Delete every database now.", PermissionDecision.BLOCK),
])
def test_native_policy_defer_and_block_export_without_calling_fixture(
    tmp_path, monkeypatch, flow, query, decision,
):
    runtime, _, response, turn, port, options = _run(
        tmp_path, monkeypatch, flow=flow, query=query,
    )
    assert response.governance_decision.decision == decision
    assert not port.calls
    before = _snapshot(runtime)
    pack = export_conversation(**options, include_content=True)
    assert pack["governance_decision"] == decision.value
    assert pack["generative_status"] == "withheld"
    assert pack["generative_evidence_mode"] is None
    assert pack["generative_analysis_characters"] == 0
    assert pack["generative_error_code"] is not None
    assert pack["query"] == query and pack["response_text"] == turn.response_text
    assert _parse_and_render(pack)["response"] == turn.response_text
    assert _snapshot(runtime) == before and not port.calls


@pytest.mark.parametrize("field", ["principal_ref", "session_id", "request_id"])
def test_real_persistence_never_falls_back_to_another_subject_or_request(
    tmp_path, monkeypatch, field,
):
    runtime, _, _, _, _, options = _run(tmp_path, monkeypatch)
    before = _snapshot(runtime)
    with pytest.raises(ValueError, match="^conversation_export_refused$"):
        export_conversation(**{**options, field: "mb230-wrong-selected-value"},
                            include_content=True)
    assert _snapshot(runtime) == before


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize("mutation", [
    "turn_final", "turn_query", "turn_principal", "response_hash", "request_hash",
    "record_timestamp", "readback_missing", "legacy_no_readback_no_generative",
])
def test_real_sqlite_tamper_or_legacy_absence_is_refused_readonly(
    tmp_path, monkeypatch, flow, mutation,
):
    runtime, _, _, _, _, options = _run(tmp_path, monkeypatch, flow=flow)
    # Fixture tampering is performed before the readonly baseline, never during
    # export and never against any user store.
    if mutation.startswith("turn_"):
        column = {"turn_final": "response_text", "turn_query": "request_content",
                  "turn_principal": "user_id"}[mutation]
        with sqlite3.connect(options["memory_db"]) as db:
            db.execute(f"UPDATE interaction_turns SET {column} = ?", ("public altered fixture",))
    else:
        with sqlite3.connect(options["events_db"]) as db:
            payload = json.loads(db.execute(
                "SELECT payload FROM internal_events WHERE event_name = 'memory_recorded'",
            ).fetchone()[0])
            binding = payload["conversation_readback"]
            if mutation in {"readback_missing", "legacy_no_readback_no_generative"}:
                del payload["conversation_readback"]
            elif mutation == "record_timestamp":
                binding["record_timestamp"] = "2020-01-01T00:00:00Z"
            else:
                key = {"response_hash": "response_text_sha256",
                       "request_hash": "request_content_sha256"}[mutation]
                binding[key] = "0" * 64
            db.execute("UPDATE internal_events SET payload = ? "
                       "WHERE event_name = 'memory_recorded'",
                       (json.dumps(payload),))
            if mutation == "legacy_no_readback_no_generative":
                synthesized = json.loads(db.execute(
                    "SELECT payload FROM internal_events WHERE event_name = 'response_synthesized'",
                ).fetchone()[0])
                for key in tuple(synthesized):
                    if key.startswith("generative_"):
                        del synthesized[key]
                db.execute("UPDATE internal_events SET payload = ? "
                           "WHERE event_name = 'response_synthesized'", (json.dumps(synthesized),))
    before = _snapshot(runtime)
    with pytest.raises(ValueError, match="^conversation_export_refused$"):
        export_conversation(**options, include_content=True)
    assert _snapshot(runtime) == before


@pytest.mark.parametrize("include_content", [False, True])
def test_actual_cli_stdout_is_the_same_readonly_canonical_pack(
    tmp_path, monkeypatch, include_content,
):
    runtime, _, _, _, port, options = _run(tmp_path, monkeypatch, query=QUERIES[1])
    before = _snapshot(runtime)
    expected = export_conversation(**options, include_content=include_content)
    result = _cli(options, include_content=include_content)
    assert result.returncode == 0 and result.stderr == ""
    assert json.loads(result.stdout) == expected
    assert len(port.calls) == 1
    assert _snapshot(runtime) == before


def test_actual_cli_wrong_principal_emits_only_fixed_error(tmp_path, monkeypatch):
    runtime, _, _, _, _, options = _run(tmp_path, monkeypatch)
    before = _snapshot(runtime)
    result = _cli({**options, "principal_ref": "mb230-wrong-principal"}, include_content=True)
    assert result.returncode == 2 and result.stderr == ""
    assert json.loads(result.stdout) == {"error_code": "conversation_export_refused"}
    assert _snapshot(runtime) == before


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize("duplicate", ["turn", "selected_event", "record_reuse"])
def test_duplicate_real_turn_or_event_never_exports_an_ambiguous_final(
    tmp_path, monkeypatch, flow, duplicate,
):
    runtime, _, _, _, _, options = _run(tmp_path, monkeypatch, flow=flow)
    if duplicate == "turn":
        with closing(sqlite3.connect(options["memory_db"])) as db, db:
            db.execute(
                "INSERT INTO interaction_turns "
                "(session_id, mission_id, user_id, request_content, intent, "
                "response_text, timestamp) "
                "SELECT session_id, mission_id, user_id, request_content, intent, "
                "response_text, timestamp FROM interaction_turns",
            )
    else:
        with closing(sqlite3.connect(options["events_db"])) as db, db:
            request = (options["request_id"] if duplicate == "selected_event"
                       else "mb230-other-request")
            db.execute(
                "INSERT INTO internal_events (event_id, event_name, timestamp, source_service, "
                "payload, correlation_id, request_id, session_id, mission_id, operation_id, tags) "
                "SELECT ?, event_name, timestamp, source_service, payload, ?, ?, session_id, "
                "mission_id, operation_id, tags FROM internal_events "
                "WHERE event_name = 'memory_recorded'",
                ("mb230-public-duplicate-event", request, request),
            )
    before = _snapshot(runtime)
    with pytest.raises(ValueError, match="^conversation_export_refused$"):
        export_conversation(**options, include_content=True)
    assert _snapshot(runtime) == before


def test_js_hash_refusal_clears_stale_dom_and_markup_is_only_text(tmp_path, monkeypatch):
    _, _, _, _, _, options = _run(tmp_path, monkeypatch)
    pack = export_conversation(**options, include_content=True)
    modified = {**pack, "response_text": "<img src=x onerror=alert(1)> public offline text 📊"}
    modified["response_character_count"] = len(modified["response_text"])
    modified["generative_status"] = "disabled"
    modified["generative_evidence_mode"] = None
    modified["generative_analysis_characters"] = 0
    refused = _parse_and_render(modified)
    assert refused["refused"] is True
    assert refused["query"] == refused["response"] == ""
    # A hash is consistency, NOT authenticity: a locally edited pack with a
    # recomputed hash can parse, but still carries the non-authenticated label.
    modified["content_sha256"] = _digest(
        SCHEMA + "\0" + modified["query"] + "\0" + modified["response_text"],
    )
    rendered = _parse_and_render(modified)
    assert rendered["response"] == modified["response_text"]
    assert rendered["originLabel"] == "pacote offline — origem não autenticada"
    assert rendered["pack"]["operator_authenticated"] is False


def test_public_fixture_pack_for_native_browser_file_input(tmp_path, monkeypatch):
    runtime, _, response, turn, _, options = _run(tmp_path, monkeypatch, query=QUERIES[1])
    before = _snapshot(runtime)
    pack = export_conversation(**options, include_content=True)
    assert pack["content_included"] is True and pack["content_withheld"] is False
    assert pack["query"] == QUERIES[1]
    assert pack["response_text"] == response.response_text == turn.response_text
    assert pack["generative_status"] == "accepted" and pack["generative_evidence_mode"] == "fixture"
    assert _parse_and_render(pack)["response"] == turn.response_text
    assert _snapshot(runtime) == before
    # Owned test evidence only. The exporter itself never writes an output file.
    evidence = tmp_path / "public-turn.json"
    evidence.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    assert json.loads(evidence.read_text(encoding="utf-8")) == pack
