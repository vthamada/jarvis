"""Host opt-in validation before runtime/profile IO; no account or model is opened."""

from types import SimpleNamespace

import pytest

from apps.jarvis_api import __main__ as startup


@pytest.mark.parametrize(
    "options",
    [
        ["--model", "private-model"],
        ["--profile-ref", "private-profile"],
        ["--credential-dir", "private-path"],
        ["--generative-timeout-seconds", "10"],
        ["--enable-generative"],
        ["--enable-generative", "--model", "private-model"],
        ["--enable-generative", "--generative-timeout-seconds", "0"],
        ["--enable-generative", "--generative-timeout-seconds", "21"],
        ["--enable-generative", "--generative-timeout-seconds", "nan"],
    ],
)
def test_incomplete_or_non_opted_options_refused_without_io(monkeypatch, capsys, options):
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("unexpected IO"))
    assert startup.main(["--authorized", *options]) == 2
    assert capsys.readouterr().err == "invalid_local_web_options\n"


def test_authorization_before_profile_or_runtime(monkeypatch, capsys):
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("unexpected IO"))
    assert startup.main(["--enable-generative", "--model", "private-model"]) == 2
    assert capsys.readouterr().err == "local_web_authorization_required\n"


@pytest.mark.parametrize("change", ["relative", "profile", "model", "budget", "infinity"])
def test_invalid_complete_options_do_not_open_profile(tmp_path, monkeypatch, capsys, change):
    options = {
        "model": "synthetic-model",
        "credential-dir": str(tmp_path / "no-profile-io"),
        "profile-ref": "profile-" + "a" * 64,
        "generative-timeout-seconds": "20",
    }
    key, value = {
        "relative": ("credential-dir", "relative-private"),
        "profile": ("profile-ref", "private-secret"),
        "model": ("model", "private model"),
        "budget": ("generative-timeout-seconds", "21"),
        "infinity": ("generative-timeout-seconds", "inf"),
    }[change]
    options[key] = value
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("unexpected IO"))
    args = ["--authorized", "--enable-generative"]
    for key, value in options.items():
        args.extend(["--" + key, value])
    assert startup.main(args) == 2
    assert capsys.readouterr().err == "invalid_local_web_options\n"
    assert not (tmp_path / "no-profile-io").exists()


@pytest.mark.parametrize("enabled", [False, True])
def test_explicit_startup_composes_inert_profile_and_preserves_default(
    tmp_path, monkeypatch, capsys, enabled
):
    from apps.jarvis_api import analysis_service, local_server

    created, closed = [], []
    runtime = tmp_path / "owned-runtime"

    class Service:
        def __init__(self, directory, **options):
            created.append((directory, options))

        def close(self):
            closed.append("service")

    def stop():
        raise KeyboardInterrupt

    server = SimpleNamespace(
        server_port=12345,
        auth=SimpleNamespace(
            pairing_secret="synthetic-one-use", close=lambda: closed.append("auth")
        ),
        serve_forever=stop,
        server_close=lambda: closed.append("server"),
    )
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: runtime)
    monkeypatch.setattr(analysis_service, "AnalysisService", Service)
    monkeypatch.setattr(local_server, "create_server", lambda service, port: server)
    args = ["--authorized"]
    if enabled:
        args.extend(
            [
                "--enable-generative",
                "--model",
                "synthetic-model",
                "--credential-dir",
                str(tmp_path / "no-profile-io"),
                "--profile-ref",
                "profile-" + "a" * 64,
            ]
        )
    assert startup.main(args) == 0
    assert created[0][0] == runtime
    if enabled:
        profile = created[0][1]["generative_profile"]
        assert profile.model == "synthetic-model" and profile.timeout_seconds == 20
        assert profile.evidence_mode == "live"  # Selection, NOT observed model acceptance.
    else:
        assert created[0][1] == {}
    assert closed == ["auth", "service", "server"]
    output = capsys.readouterr()
    assert not output.err and "synthetic-model" not in output.out
    assert "profile-" not in output.out and "no-profile-io" not in output.out
    assert not (tmp_path / "no-profile-io").exists()
