from tools.render_repository_hygiene_tool_decisions import build_payload, render_markdown


def test_render_repository_hygiene_tool_decisions_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-repository-hygiene-and-tools-review-cut"
    assert payload["sprint_id"] == "sprint-3-tools-classification"
    assert payload["summary"]["keep_active"] == 17
    assert payload["summary"]["archive_candidates"] == 15
    assert payload["summary"]["delete_candidates"] == 0


def test_render_repository_hygiene_tool_decisions_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Repository Hygiene Tool Decisions" in rendered
    assert "render_repository_hygiene_tool_decisions.py" in rendered
    assert "close_alignment_cycle.py" in rendered
    assert "nenhuma ferramenta entra em delete candidate nesta sprint" in rendered
