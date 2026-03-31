from tools.close_native_memory_scope_hardening_cut import build_payload, render_markdown


def test_close_native_memory_scope_hardening_cut_builds_payload() -> None:
    payload = build_payload()

    assert payload["decision"] == "complete_v2_native_memory_scope_hardening_cut"
    assert payload["next_cut_recommendation"] == "repository-hygiene-and-tools-review"
    assert payload["decision_summary"]["user_scope_runtime_status"] == "runtime_parcial"
    assert payload["decision_summary"]["organization_scope_guard_status"] == (
        "no_go_without_canonical_consumer"
    )
    assert payload["decision_summary"]["recurrent_context_fields"] == 6


def test_close_native_memory_scope_hardening_cut_renders_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "Fechamento do V2 Native Memory Scope Hardening Cut" in rendered
    assert "repository-hygiene-and-tools-review" in rendered
    assert "revisao estrutural de docs e tools antes do proximo corte" in rendered
