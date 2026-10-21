"""Host guidance drives completion through real Core, reports and SQLite.

The contextual model double selects its next action from the received state;
it does not supply policy, read files or synthesize the canonical final itself.
"""

import json

from orchestrator_service.model_tool_loop import ModelToolLoopConfig
from test_model_tool_loop_core import (
    DOCUMENTATION,
    MODEL,
    OBSERVABILITY,
    _annex_values,
    _assert_no_authority,
    _assert_persisted,
    _configured_core,
    _contract,
    _payload,
    _reports,
)

from shared.model_inference import InferenceResult


class GuidedPort:
    def __init__(self):
        self.calls = []

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        data = json.loads(request.messages[0].content)
        progress = data.get("continuation", {})
        if progress.get("suggested_next_action") == "finalize":
            observations = data["observations"]
            value = {
                "kind": "final",
                "analysis": "Both reports were considered; one trace is missing.",
                "citations": [{"call_id": item["call_id"], "quote": item["text"]}
                              for item in observations],
            }
        else:
            # Without host progress this double repeats a valid-looking ID,
            # exposing the old affordance gap instead of silently faking success.
            unread = progress.get("unread_resource_ids", ["documentation"])
            value = {
                "kind": "tool_call",
                "call_id": progress.get("suggested_call_id", "read-report-1"),
                "tool": "read_local_report", "arguments": {"resource_id": unread[0]},
            }
        return InferenceResult(request.request_id, request.model, "fixture", "completed",
                               text=json.dumps(value), evidence_mode="fixture")


def test_guidance_finishes_after_two_reads_with_budget_left_and_exact_canonical_final(
    tmp_path, monkeypatch,
):
    reader, reads, _ = _reports(tmp_path, monkeypatch)
    port = GuidedPort()
    runtime = tmp_path / "runtime"
    core, _ = _configured_core(
        runtime, ModelToolLoopConfig(port=port, model=MODEL, reader=reader), monkeypatch,
    )
    response = core.handle_input(_contract("guided-completion"))
    assert _payload(response)["model_tool_loop_status"] == "completed"
    assert len(port.calls) == 3 and reads == ["documentation", "observability"]
    last = json.loads(port.calls[-1].messages[0].content)["continuation"]
    assert last["remaining_tool_calls"] == 1
    assert last["allowed_response_kinds"] == ["tool_call", "final"]
    assert last["suggested_next_action"] == "finalize" and not last["final_required"]
    assert _annex_values(response, "Analysis: ") == [
        "Both reports were considered; one trace is missing."
    ]
    assert _annex_values(response, "Observed quote: ") == [DOCUMENTATION, OBSERVABILITY]
    _assert_no_authority(response)
    _assert_persisted(runtime, response)
