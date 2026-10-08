"""Opt-in startup and fresh runtime creation, without any actual Core/socket."""

from pathlib import Path

import pytest

from apps.jarvis_api import __main__ as startup


def test_unauthorized_startup_does_not_construct_or_write(monkeypatch, capsys):
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("unexpected IO"))
    assert startup.main([]) == 2
    assert capsys.readouterr().err == "local_web_authorization_required\n"


@pytest.mark.parametrize("port", ["-1", "65536", "private-secret", "1.2"])
def test_invalid_options_do_not_construct_or_write(monkeypatch, capsys, port):
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("unexpected IO"))
    try:
        code = startup.main(["--authorized", "--port", port])
    except SystemExit as error:
        code = error.code
    assert code == 2
    assert capsys.readouterr().err == "invalid_local_web_options\n"


@pytest.mark.parametrize("arguments", [["--secret", "private-secret"], ["--runtime", "private"]])
def test_no_credential_or_human_runtime_options(arguments, capsys):
    with pytest.raises(SystemExit) as error:
        startup.main(arguments)
    assert error.value.code == 2
    assert capsys.readouterr().err == "invalid_local_web_options\n"


def test_two_runs_create_distinct_preserved_directories(tmp_path):
    first = startup.create_owned_runtime(tmp_path)
    evidence = first / "owned-evidence.txt"
    evidence.write_text("synthetic", encoding="utf-8")
    second = startup.create_owned_runtime(tmp_path)
    assert first != second
    assert first.parent == second.parent == tmp_path / ".jarvis_runtime" / "web-live"
    assert evidence.read_text(encoding="utf-8") == "synthetic"
    assert list(second.iterdir()) == []


@pytest.mark.parametrize("level", [".jarvis_runtime", ".jarvis_runtime/web-live"])
def test_existing_file_is_not_overwritten(tmp_path, level):
    target = tmp_path / level
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("synthetic existing content", encoding="utf-8")
    with pytest.raises(ValueError, match="local_web_runtime_refused"):
        startup.create_owned_runtime(tmp_path)
    assert target.read_text(encoding="utf-8") == "synthetic existing content"


@pytest.mark.parametrize("root", [Path("relative"), None, "not-path"])
def test_invalid_root_refused_before_runtime(root):
    with pytest.raises(ValueError, match="local_web_runtime_refused"):
        startup.create_owned_runtime(root)
