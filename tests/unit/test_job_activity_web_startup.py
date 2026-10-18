"""New host options stay inert and never reflect private option values."""

import pytest

from apps.jarvis_api import __main__ as startup


@pytest.mark.parametrize("arguments", [
    ["--job-db", "private-path"],
    ["--job-actor-ref", "private-actor"],
    ["--job-session-ref", "private-session"],
    ["--job-id", "private-job"],
    ["--enable-job-activity"],
    ["--enable-job-activity", "--job-db", "relative", "--job-actor-ref", "actor",
     "--job-session-ref", "session", "--job-id", "job"],
])
def test_incomplete_or_unenabled_activity_config_denied_before_runtime(arguments, monkeypatch,
                                                                     capsys):
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("runtime IO"))
    assert startup.main(["--authorized", *arguments]) == 2
    assert capsys.readouterr().err == "invalid_local_web_options\n"


def test_enabled_profile_reaches_server_without_opening_ledger(tmp_path, monkeypatch, capsys):
    from apps.jarvis_api import analysis_service, local_server
    from apps.jarvis_api.job_activity_profile import JobActivityProfile

    monkeypatch.setattr(startup, "create_owned_runtime", lambda: tmp_path)
    monkeypatch.setattr(JobActivityProfile, "read", lambda _self: pytest.fail("startup read"))
    seen = []

    class Service:
        def __init__(self, runtime):
            assert runtime == tmp_path

        def close(self):
            seen.append("closed")

    class Server:
        server_port = 0

        class auth:
            pairing_secret = "synthetic"

            @staticmethod
            def close():
                pass

        def serve_forever(self):
            pass

        def server_close(self):
            pass

    def create(service, port, **options):
        assert type(options["job_activity_profile"]) is JobActivityProfile
        seen.append("profile")
        return Server()

    monkeypatch.setattr(analysis_service, "AnalysisService", Service)
    monkeypatch.setattr(local_server, "create_server", create)
    database = tmp_path / "private-missing.db"
    assert startup.main(["--authorized", "--enable-job-activity", "--job-db", str(database),
                         "--job-actor-ref", "private-actor", "--job-session-ref", "private-session",
                         "--job-id", "private-job"]) == 0
    assert seen == ["profile", "closed"]
    output = capsys.readouterr()
    assert "Job activity: manual readonly" in output.out
    assert "private" not in output.out and not output.err
    assert not database.exists()
