"""History egress is an explicit host choice, never a document instruction."""

from pathlib import Path

import pytest

from apps.jarvis_console import local_model_tool_loop_cli as local
from apps.jarvis_console import model_tool_loop_cli as account


class Port:
    provider_id = "responses_plan"
    evidence_mode = "injected_transport"

    def infer(self, *_args, **_kwargs):
        pytest.fail("option tests must not infer")


def options(tmp_path, module):
    result = dict(
        authorized=True, confirmed=True, reports_confirmed=True,
        session_id="history-option-test", model="synthetic-model",
        reports={"documentation": tmp_path / "unopened.txt"},
    )
    if module is local:
        result.update(endpoint="http://127.0.0.1:11434/v1/chat/completions",
                      upstream_egress_acknowledged=True)
    else:
        result.update(credential_dir=tmp_path / "unopened", profile_ref="profile-" + "a" * 64)
    return result


@pytest.mark.parametrize("module", [account, local])
@pytest.mark.parametrize("enabled", [False, True])
def test_host_history_choice_reaches_shared_canonical_flow(tmp_path, monkeypatch, module, enabled):
    captured = []

    def run(query, **kwargs):
        captured.append(kwargs["include_canonical_history"])
        return {"status": "recorded"}

    monkeypatch.setattr(module, "_run_report_loop", run)
    port = Port()
    if module is local:
        port.provider_id = "chat_completions_local"
    execute = local.analyze_local_reports if module is local else account.analyze_reports
    result = execute(
        {"schema_version": module.INPUT_SCHEMA,
         "query": "Compare documentation and observability pilot reports."},
        **options(tmp_path, module), include_canonical_history=enabled,
        port_factory=lambda *_args: port,
    )
    assert result["status"] == "recorded" and captured == [enabled]
    assert not (tmp_path / "unopened.txt").exists()


@pytest.mark.parametrize("module", [account, local])
@pytest.mark.parametrize("invalid", [None, 1, "true", [], {}])
def test_non_boolean_history_refused_before_factory(tmp_path, module, invalid):
    def forbidden(*_args):
        pytest.fail("invalid egress choice opened a factory")

    execute = local.analyze_local_reports if module is local else account.analyze_reports
    with pytest.raises(ValueError):
        execute({"schema_version": module.INPUT_SCHEMA, "query": "Compare reports."},
                **options(tmp_path, module), include_canonical_history=invalid,
                core_factory=forbidden, port_factory=forbidden)


@pytest.mark.parametrize("module", [account, local])
def test_document_cannot_enable_history(tmp_path, module):
    execute = local.analyze_local_reports if module is local else account.analyze_reports
    with pytest.raises(ValueError):
        execute({"schema_version": module.INPUT_SCHEMA, "query": "Compare reports.",
                 "include_canonical_history": True}, **options(tmp_path, module))


@pytest.mark.parametrize("module", [account, local])
@pytest.mark.parametrize("enabled", [False, True])
def test_main_flag_is_explicit_and_default_off(tmp_path, monkeypatch, module, enabled):
    captured = []
    monkeypatch.setattr(module, "read_review_input", lambda: {})
    entry = "analyze_local_reports" if module is local else "analyze_reports"
    monkeypatch.setattr(module, entry, lambda document, **kwargs: captured.append(kwargs) or {})
    args = ["--authorized", "--confirm-input", "--confirm-reports", "--session-id", "demo",
            "--model", "synthetic-model", "--report", "documentation=" + str(tmp_path / "a")]
    if module is local:
        args.extend(["--endpoint", "http://127.0.0.1:11434/v1/chat/completions",
                     "--acknowledge-upstream-egress"])
    else:
        args.extend(["--credential-dir", str(Path(tmp_path) / "unopened"),
                     "--profile-ref", "profile-" + "a" * 64])
    if enabled:
        args.append("--include-canonical-history")
    assert module.main(args) == 0
    assert captured[0]["include_canonical_history"] is enabled
