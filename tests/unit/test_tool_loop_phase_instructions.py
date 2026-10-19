"""Only currently valid response schemas belong in model instructions."""

import json
from dataclasses import replace

from test_model_tool_loop import Harness, final, proposal


def test_read_phase_does_not_offer_a_premature_final_schema():
    harness = Harness()
    assert harness.run().status == "completed"
    instructions = harness.port.requests[0].instructions
    assert '"kind":"tool_call"' in instructions
    assert '"kind":"final"' not in instructions


def test_final_only_phase_does_not_offer_another_tool_call_schema():
    harness = Harness([proposal(), final()])
    assert harness.run(max_tool_calls=1).status == "completed"
    instructions = harness.port.requests[1].instructions
    assert '"kind":"final"' in instructions
    assert '"kind":"tool_call"' not in instructions
    assert "final_required" in instructions


def test_continuation_with_budget_offers_final_before_another_read_schema():
    harness = Harness([proposal(), final()])
    assert harness.run(max_tool_calls=2).status == "completed"
    instructions = harness.port.requests[1].instructions
    assert instructions.index('"kind":"final"') < instructions.index('"kind":"tool_call"')


def test_finalize_suggestion_does_not_also_suggest_an_unnecessary_new_read_id():
    harness = Harness([proposal(), final()])
    harness.context = replace(harness.context, resource_ids=("documentation",))
    assert harness.run().status == "completed"
    state = json.loads(harness.port.requests[1].messages[0].content)["continuation"]
    assert state["remaining_tool_calls"] == 2
    assert state["allowed_response_kinds"] == ["tool_call", "final"]
    assert state["suggested_next_action"] == "finalize"
    assert state["suggested_call_id"] is None
