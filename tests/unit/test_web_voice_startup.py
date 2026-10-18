"""Optional voice host wiring and shutdown, without models, profiles or sockets."""

from types import SimpleNamespace

import pytest

from apps.jarvis_api import __main__ as startup


@pytest.mark.parametrize("options", [
    ["--enable-voice"],
    ["--voice-profile", "private-never-opened.json"],
])
def test_voice_flags_require_explicit_pair_before_runtime(options, monkeypatch, capsys):
    from apps.jarvis_api import voice_profile

    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("runtime IO"))
    monkeypatch.setattr(voice_profile, "load_voice_profile", lambda *_: pytest.fail("profile IO"))
    assert startup.main(["--authorized", *options]) == 2
    assert capsys.readouterr().err == "invalid_local_web_options\n"


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("has_voice", [False, True])
@pytest.mark.parametrize("interrupt", [False, True])
def test_optional_voice_shutdown_precedes_auth_core_and_socket(
    enabled, has_voice, interrupt, tmp_path, monkeypatch, capsys,
):
    from apps.jarvis_api import analysis_service, local_server, voice_profile

    events, seen = [], []
    profile = object()
    private_path = tmp_path / "private-never-opened.json"

    def load(selected, root):
        assert selected == private_path and root == startup.ROOT
        seen.append("profile")
        return profile

    class Service:
        def __init__(self, runtime):
            assert runtime == tmp_path

        def close(self):
            events.append("core")

    def serve():
        if interrupt:
            raise KeyboardInterrupt

    server = SimpleNamespace(
        server_port=0,
        auth=SimpleNamespace(
            pairing_secret="synthetic-one-use", close=lambda: events.append("auth"),
        ),
        serve_forever=serve,
        server_close=lambda: events.append("socket"),
    )
    if has_voice:
        server.voice_service = SimpleNamespace(close=lambda: events.append("voice"))

    def create(service, port, **options):
        assert type(service) is Service and port == 0
        assert options == ({"voice_profile": profile} if enabled else {})
        return server

    monkeypatch.setattr(startup, "create_owned_runtime", lambda: tmp_path)
    monkeypatch.setattr(analysis_service, "AnalysisService", Service)
    monkeypatch.setattr(local_server, "create_server", create)
    monkeypatch.setattr(voice_profile, "load_voice_profile", load)
    args = ["--authorized"] + (
        ["--enable-voice", "--voice-profile", str(private_path)] if enabled else []
    )
    assert startup.main(args) == 0
    assert seen == (["profile"] if enabled else [])
    assert events == (["voice"] if has_voice else []) + ["auth", "core", "socket"]
    output = capsys.readouterr()
    assert output.err == "" and "private-never-opened" not in output.out
    assert ("Local voice: configured" if enabled else "Local voice: disabled") in output.out
    assert not private_path.exists()
