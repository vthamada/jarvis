from tools.render_repository_hygiene_inventory import build_payload, render_markdown


def test_render_repository_hygiene_inventory_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-repository-hygiene-and-tools-review-cut"
    assert payload["sprint_id"] == "sprint-1-regenerable-inventory"
    assert payload["active_cut_doc"] == "v2-repository-hygiene-and-tools-review-cut.md"
    assert payload["summary"]["archived_tool_scripts"] == 15
    assert "engineering_gate.py" in payload["tool_inventory"]["baseline_validation"]
    assert (
        "close_native_memory_scope_hardening_cut.py"
        in payload["tool_inventory"]["active_cut_closures"]
    )
    assert "close_alignment_cycle.py" in payload["tool_inventory"]["archived_history"]


def test_render_repository_hygiene_inventory_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Repository Hygiene Inventory" in rendered
    assert "v2-repository-hygiene-and-tools-review-cut.md" in rendered
    assert "## Tool Inventory" in rendered
    assert "tools/archive e docs/archive preservam historico regeneravel" in rendered
