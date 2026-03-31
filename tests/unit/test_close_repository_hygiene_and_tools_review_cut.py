from tools.close_repository_hygiene_and_tools_review_cut import build_payload, render_markdown


def test_close_repository_hygiene_and_tools_review_cut_builds_payload() -> None:
    payload = build_payload()

    assert payload["decision"] == "complete_v2_repository_hygiene_and_tools_review_cut"
    assert (
        payload["next_cut_recommendation"]
        == "select-next-functional-cut-from-adherence-snapshot"
    )
    assert payload["decision_summary"]["docs_moved_to_archive"] == 15
    assert payload["decision_summary"]["tools_moved_to_archive"] == 15
    assert payload["decision_summary"]["delete_candidates_executed"] == 0


def test_close_repository_hygiene_and_tools_review_cut_renders_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "Fechamento do V2 Repository Hygiene And Tools Review Cut" in rendered
    assert "select-next-functional-cut-from-adherence-snapshot" in rendered
    assert "tools/archive" in rendered
    assert "docs_moved_to_archive" in rendered
