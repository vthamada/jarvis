"""Bounded public entrypoint checks; no server, model or credential access."""

import json
from pathlib import Path

import pytest

from evals.operator_tasks import hermes_local_experiment as lab


def _forbidden(*args, **kwargs):
    pytest.fail("inert or refused invocation attempted runtime work")


def _prevent_execution(monkeypatch):
    monkeypatch.setattr(lab, "ChatCompletionsInferenceProvider", _forbidden)
    monkeypatch.setattr(lab, "CampaignInferenceGuard", _forbidden)
    monkeypatch.setattr(lab, "_isolated_core", _forbidden)
    monkeypatch.setattr(lab, "_save", _forbidden)


def test_default_preflight_is_inert_and_does_not_create_runtime(tmp_path, monkeypatch):
    _prevent_execution(monkeypatch)
    directory = tmp_path / "not-created"
    manifest = lab.preflight(directory=directory)
    assert manifest["status"] == "preflight"
    assert manifest["attempted_inferences"] == manifest["warmup_calls"] == 0
    assert manifest["max_inference_attempts"] == 24
    assert manifest["account_used"] is manifest["paid_fallback"] is False
    assert manifest["runtime_capability_promoted"] is manifest["real_model_verified"] is False
    assert manifest["upstream_egress_possible"] is True
    assert not directory.exists() and list(tmp_path.iterdir()) == []


def test_main_without_execute_only_emits_preflight(tmp_path, monkeypatch, capsys):
    _prevent_execution(monkeypatch)
    directory = tmp_path / "not-created"
    assert lab.main(["--runtime-dir", str(directory)]) == 0
    captured = capsys.readouterr()
    manifest = json.loads(captured.out)
    assert captured.err == ""
    assert manifest["status"] == "preflight" and manifest["attempted_inferences"] == 0
    assert not directory.exists()


@pytest.mark.parametrize("authorized,egress", [
    (False, False), (False, True), (True, False), (1, True), (True, 1),
    ("yes", True), (True, "yes"), (None, True),
])
def test_execution_requires_both_literal_permissions_before_runtime_or_artifacts(
    tmp_path, monkeypatch, authorized, egress,
):
    _prevent_execution(monkeypatch)
    directory = tmp_path / "not-created"
    with pytest.raises(ValueError, match="^local_experiment_not_authorized$"):
        lab.run_local_experiment(directory=directory, authorized=authorized,
                                 upstream_egress_acknowledged=egress)
    assert not directory.exists() and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("model", ["", "two models", "http://PRIVATE_SENTINEL", "model\nline", 3])
def test_invalid_model_is_rejected_without_io_or_echo(tmp_path, monkeypatch, model):
    _prevent_execution(monkeypatch)
    directory = tmp_path / "not-created"
    with pytest.raises(ValueError) as error:
        lab.run_local_experiment(directory=directory, model=model, authorized=True,
                                 upstream_egress_acknowledged=True)
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert not directory.exists() and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("endpoint", [
    "https://127.0.0.1:11434/v1/chat/completions",
    "http://example.invalid/v1/chat/completions",
    "http://127.0.0.1:11434/other",
    "http://127.0.0.1:11434/v1/chat/completions?PRIVATE_SENTINEL",
    "http://PRIVATE_SENTINEL:password@127.0.0.1:11434/v1/chat/completions",
    "http://127.0.0.1:0/v1/chat/completions",
])
def test_invalid_endpoint_is_rejected_before_runtime_or_artifacts(
    tmp_path, monkeypatch, endpoint,
):
    _prevent_execution(monkeypatch)
    directory = tmp_path / "not-created"
    with pytest.raises(ValueError) as error:
        lab.run_local_experiment(directory=directory, endpoint=endpoint, authorized=True,
                                 upstream_egress_acknowledged=True)
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert not directory.exists() and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("directory", [Path("relative"), Path("."), "not-a-path", None])
def test_directory_must_be_an_explicit_absolute_path(directory, monkeypatch):
    _prevent_execution(monkeypatch)
    with pytest.raises(ValueError, match="^invalid_experiment_directory$"):
        lab.preflight(directory=directory)


def test_existing_experiment_directory_and_user_contents_are_preserved(tmp_path, monkeypatch):
    _prevent_execution(monkeypatch)
    directory = tmp_path / "existing"
    directory.mkdir()
    sentinel = directory / "existing-user-artifact.txt"
    sentinel.write_bytes(b"user-owned-existing-artifact")
    with pytest.raises(FileExistsError):
        lab.run_local_experiment(directory=directory, authorized=True,
                                 upstream_egress_acknowledged=True)
    assert sentinel.read_bytes() == b"user-owned-existing-artifact"
    assert list(directory.iterdir()) == [sentinel]


@pytest.mark.parametrize("tail", [
    ["--unknown-private-option", "PRIVATE_SENTINEL"],
    ["--endpoint", "http://PRIVATE_SENTINEL/v1/chat/completions"],
    ["--model", "PRIVATE_SENTINEL model"],
    ["--execute", "--authorized-local"],
    ["--execute", "--acknowledge-upstream-egress"],
    ["--execute", "PRIVATE_SENTINEL"],
])
def test_safe_parser_never_echoes_invalid_private_arguments(
    tmp_path, monkeypatch, capsys, tail,
):
    _prevent_execution(monkeypatch)
    directory = tmp_path / "not-created"
    assert lab.main(["--runtime-dir", str(directory), *tail]) == 2
    captured = capsys.readouterr()
    assert captured.err == "" and "PRIVATE_SENTINEL" not in captured.out
    assert json.loads(captured.out) == {
        "status": "refused", "error_code": "local_experiment_refused",
    }
    assert not directory.exists()


def test_parser_disallows_abbreviated_runtime_flag_without_echo(capsys, monkeypatch):
    _prevent_execution(monkeypatch)
    assert lab.main(["--runtime", "PRIVATE_SENTINEL"]) == 2
    captured = capsys.readouterr()
    assert captured.err == "" and "PRIVATE_SENTINEL" not in captured.out


def test_keyboard_interrupt_reports_fixed_cancellation_without_private_details(
    tmp_path, monkeypatch, capsys,
):
    def cancelled(**kwargs):
        raise KeyboardInterrupt("PRIVATE_SENTINEL")

    monkeypatch.setattr(lab, "preflight", cancelled)
    assert lab.main(["--runtime-dir", str(tmp_path / "not-created")]) == 3
    captured = capsys.readouterr()
    assert captured.err == "" and "PRIVATE_SENTINEL" not in captured.out
    assert json.loads(captured.out) == {"status": "cancelled", "error_code": "cancelled"}
