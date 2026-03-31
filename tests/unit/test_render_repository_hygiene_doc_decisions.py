from tools.render_repository_hygiene_doc_decisions import build_payload, render_markdown


def test_render_repository_hygiene_doc_decisions_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-repository-hygiene-and-tools-review-cut"
    assert payload["sprint_id"] == "sprint-2-docs-classification"
    assert payload["summary"]["keep_active"] == 6
    assert payload["summary"]["archive_candidates"] == 15
    assert payload["summary"]["delete_candidates"] == 0


def test_render_repository_hygiene_doc_decisions_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Repository Hygiene Doc Decisions" in rendered
    assert "v2-native-memory-scope-hardening-cut-closure.md" in rendered
    assert "v2-domain-consumers-and-workflows-cut.md" in rendered
    assert "nenhum documento entra em delete candidate nesta sprint" in rendered
